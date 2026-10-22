import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config/app_config.dart';
import '../models/json_parsing.dart';
import '../models/observation_schema.dart';
import '../models/prediction_result.dart';
import '../models/system_info.dart';

typedef MultipartSender = Future<http.StreamedResponse> Function(
  http.MultipartRequest request,
);

class BackendHealth {
  const BackendHealth({
    required this.status,
    required this.apiVersion,
    required this.runtimeMode,
  });

  final String status;
  final String apiVersion;
  final String runtimeMode;

  factory BackendHealth.fromJson(JsonMap json) {
    return BackendHealth(
      status: asString(json['status']),
      apiVersion: asString(json['api_version']),
      runtimeMode: asString(json['runtime_mode']),
    );
  }
}

class ApiException implements Exception {
  const ApiException({
    required this.message,
    this.statusCode,
    this.field,
    this.allowedValues = const <String>[],
  });

  final String message;
  final int? statusCode;
  final String? field;
  final List<String> allowedValues;

  String get userMessage {
    if (statusCode == 422 && field != null) {
      final fieldName = humanizeIdentifier(field!);
      final allowed = allowedValues.isEmpty
          ? ''
          : ' Allowed values: ${allowedValues.join(', ')}.';
      return '$fieldName: $message$allowed';
    }
    return message;
  }

  @override
  String toString() => userMessage;
}

abstract class RiceLeafApi {
  Future<BackendHealth> healthCheck();

  Future<SystemInfo> getSystemInfo();

  Future<ObservationSchema> getObservationSchema();

  Future<PredictionResult> predictDisease(
    String imagePath, {
    Map<String, dynamic>? observations,
    void Function(double progress)? onProgress,
  });
}

class ApiService implements RiceLeafApi {
  ApiService({
    http.Client? client,
    MultipartSender? multipartSender,
    this.timeout = const Duration(seconds: 45),
  })  : _client = client ?? http.Client(),
        _multipartSender = multipartSender;

  final http.Client _client;
  final MultipartSender? _multipartSender;
  final Duration timeout;

  @override
  Future<BackendHealth> healthCheck() async {
    final json = await _getJson(AppConfig.healthEndpoint);
    return BackendHealth.fromJson(json);
  }

  @override
  Future<SystemInfo> getSystemInfo() async {
    final json = await _getJson(AppConfig.systemInfoEndpoint);
    return SystemInfo.fromJson(json);
  }

  @override
  Future<ObservationSchema> getObservationSchema() async {
    final json = await _getJson(AppConfig.observationSchemaEndpoint);
    return ObservationSchema.fromJson(json);
  }

  @override
  Future<PredictionResult> predictDisease(
    String imagePath, {
    Map<String, dynamic>? observations,
    void Function(double progress)? onProgress,
  }) async {
    final imageFile = File(imagePath);
    if (!await imageFile.exists()) {
      throw const ApiException(
        message: 'Selected image file was not found on the device.',
      );
    }

    final request = http.MultipartRequest('POST', AppConfig.predictEndpoint);
    request.files.add(await http.MultipartFile.fromPath('file', imagePath));
    final cleaned = _cleanObservations(observations);
    if (cleaned.isNotEmpty) {
      request.fields['observations_json'] = jsonEncode(cleaned);
    }

    onProgress?.call(0.05);
    try {
      final response = await (_multipartSender?.call(request) ?? request.send())
          .timeout(timeout);
      onProgress?.call(0.85);
      final body = await response.stream.bytesToString().timeout(timeout);
      final json = _decodeResponse(body, response.statusCode);
      if (response.statusCode != 200) {
        throw _apiError(response.statusCode, json);
      }
      onProgress?.call(1.0);
      return PredictionResult.fromJson(json);
    } on ApiException {
      rethrow;
    } on TimeoutException {
      throw const ApiException(
        message: 'The request timed out. Check the backend and try again.',
      );
    } on SocketException {
      throw const ApiException(
        message: 'Backend unavailable. Confirm the server address, Wi-Fi, and firewall.',
      );
    } on http.ClientException {
      throw const ApiException(
        message: 'Backend unavailable. Confirm the server address and network.',
      );
    } on FormatException {
      throw const ApiException(
        message: 'The backend returned an invalid response.',
      );
    }
  }

  Future<JsonMap> _getJson(Uri uri) async {
    try {
      final response = await _client.get(uri).timeout(timeout);
      final json = _decodeResponse(response.body, response.statusCode);
      if (response.statusCode != 200) {
        throw _apiError(response.statusCode, json);
      }
      return json;
    } on ApiException {
      rethrow;
    } on TimeoutException {
      throw const ApiException(
        message: 'The backend request timed out.',
      );
    } on SocketException {
      throw const ApiException(message: 'Could not reach the FastAPI backend.');
    } on http.ClientException {
      throw const ApiException(message: 'Could not reach the FastAPI backend.');
    } on FormatException {
      throw const ApiException(
        message: 'The backend returned invalid JSON.',
      );
    }
  }

  static JsonMap _decodeResponse(String body, int statusCode) {
    if (body.trim().isEmpty) {
      return <String, dynamic>{};
    }
    final decoded = jsonDecode(body);
    if (decoded is! Map) {
      if (statusCode == 200) {
        throw const FormatException('Expected a JSON object.');
      }
      return <String, dynamic>{};
    }
    return asJsonMap(decoded);
  }

  static ApiException _apiError(int statusCode, JsonMap response) {
    final rawDetail = response['detail'];
    final detail = asJsonMap(rawDetail);
    final serverMessage = detail.isNotEmpty
        ? asString(detail['message'])
        : rawDetail is String
            ? rawDetail
            : '';
    switch (statusCode) {
      case 400:
        return ApiException(
          statusCode: statusCode,
          message: serverMessage.isEmpty
              ? 'The backend rejected the image. Select a valid image.'
              : serverMessage,
        );
      case 403:
        return ApiException(
          statusCode: statusCode,
          message: serverMessage.isEmpty
              ? 'The server policy does not allow this request.'
              : serverMessage,
        );
      case 413:
        return const ApiException(
          statusCode: 413,
          message: 'The selected image is too large for the backend.',
        );
      case 422:
        return ApiException(
          statusCode: statusCode,
          field: asNullableString(detail['field']),
          allowedValues: asStringList(detail['allowed_values']),
          message: serverMessage.isEmpty
              ? 'The submitted observation is invalid.'
              : serverMessage,
        );
      default:
        return ApiException(
          statusCode: statusCode,
          message: statusCode >= 500
              ? 'The backend could not complete the prediction.'
              : serverMessage.isEmpty
                  ? 'Request failed with status $statusCode.'
                  : serverMessage,
        );
    }
  }

  static Map<String, dynamic> _cleanObservations(
    Map<String, dynamic>? observations,
  ) {
    if (observations == null) {
      return <String, dynamic>{};
    }
    final result = <String, dynamic>{};
    for (final entry in observations.entries) {
      final value = entry.value;
      if (value == null) {
        continue;
      }
      if (value is String) {
        final trimmed = value.trim();
        if (trimmed.isNotEmpty) {
          result[entry.key] = trimmed;
        }
        continue;
      }
      if (value is List) {
        final cleaned = value
            .where((item) => item != null && item.toString().trim().isNotEmpty)
            .toList(growable: false);
        if (cleaned.isNotEmpty) {
          result[entry.key] = cleaned;
        }
        continue;
      }
      result[entry.key] = value;
    }
    return result;
  }
}
