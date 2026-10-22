import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend_flutter/services/api_service.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

http.StreamedResponse streamedJson(Object body, int statusCode) {
  return http.StreamedResponse(
    Stream<List<int>>.value(utf8.encode(jsonEncode(body))),
    statusCode,
    headers: {'content-type': 'application/json'},
  );
}

void main() {
  late Directory temporaryDirectory;
  late File image;
  late Map<String, dynamic> fullResponse;

  setUp(() {
    temporaryDirectory = Directory.systemTemp.createTempSync('rice_flutter_test');
    image = File('${temporaryDirectory.path}${Platform.pathSeparator}leaf.png')
      ..writeAsBytesSync(<int>[137, 80, 78, 71]);
    fullResponse = Map<String, dynamic>.from(
      jsonDecode(
        File('test/fixtures/api_v2_full_response.json').readAsStringSync(),
      ) as Map,
    );
  });

  tearDown(() {
    temporaryDirectory.deleteSync(recursive: true);
  });

  test('image-only multipart sends file and no observations_json', () async {
    http.MultipartRequest? captured;
    final api = ApiService(
      multipartSender: (request) async {
        captured = request;
        return streamedJson(fullResponse, 200);
      },
    );

    final result = await api.predictDisease(image.path);

    expect(result.finalPrediction, 'leaf_blast');
    expect(captured!.files.single.field, 'file');
    expect(captured!.fields.containsKey('observations_json'), isFalse);
    expect(captured!.fields.containsKey('runtime_mode'), isFalse);
  });

  test('guided multipart sends cleaned canonical observations JSON', () async {
    http.MultipartRequest? captured;
    final api = ApiService(
      multipartSender: (request) async {
        captured = request;
        return streamedJson(fullResponse, 200);
      },
    );

    await api.predictDisease(
      image.path,
      observations: {
        'lesion_shape': 'spindle_shaped',
        'unused': '',
        'empty_list': <String>[],
        'not_set': null,
      },
    );

    final sent = jsonDecode(captured!.fields['observations_json']!) as Map;
    expect(sent, {'lesion_shape': 'spindle_shaped'});
    expect(captured!.fields.containsKey('runtime_mode'), isFalse);
  });

  test('safe 422 observation error exposes field and allowed values', () async {
    final api = ApiService(
      multipartSender: (_) async => streamedJson(
        {
          'detail': {
            'field': 'lesion_shape',
            'message': "Unsupported categorical value for 'lesion_shape'.",
            'allowed_values': ['oval', 'spindle_shaped'],
          },
        },
        422,
      ),
    );

    await expectLater(
      api.predictDisease(image.path),
      throwsA(
        isA<ApiException>()
            .having((error) => error.statusCode, 'status', 422)
            .having((error) => error.field, 'field', 'lesion_shape')
            .having(
              (error) => error.userMessage,
              'message',
              contains('Allowed values: oval, spindle_shaped'),
            ),
      ),
    );
  });

  test('health and system information endpoints parse typed responses', () async {
    final client = MockClient((request) async {
      if (request.url.path.endsWith('/health')) {
        return http.Response(
          jsonEncode({
            'status': 'ok',
            'api_version': '2.0.0',
            'runtime_mode': 'research',
          }),
          200,
        );
      }
      return http.Response(
        jsonEncode({
          'api_version': '2.0.0',
          'runtime_mode': 'research',
          'reasoning_engine_version': '1.0.0',
          'fusion_engine_version': '1.0.0',
          'artifacts': {},
        }),
        200,
      );
    });
    final api = ApiService(client: client);

    expect((await api.healthCheck()).status, 'ok');
    expect((await api.getSystemInfo()).fusionEngineVersion, '1.0.0');
  });

  test('backend unavailable becomes a stable user-facing API error', () async {
    final api = ApiService(
      client: MockClient((_) => throw http.ClientException('offline')),
      timeout: const Duration(milliseconds: 100),
    );

    await expectLater(
      api.getObservationSchema(),
      throwsA(
        isA<ApiException>().having(
          (error) => error.userMessage,
          'message',
          contains('Could not reach'),
        ),
      ),
    );
  });
}
