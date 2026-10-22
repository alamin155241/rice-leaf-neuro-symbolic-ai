import 'dart:convert';
import 'dart:io';

import 'package:frontend_flutter/models/observation_schema.dart';
import 'package:frontend_flutter/models/prediction_result.dart';
import 'package:frontend_flutter/models/system_info.dart';
import 'package:frontend_flutter/services/api_service.dart';

Map<String, dynamic> loadFixture(String name) {
  return Map<String, dynamic>.from(
    jsonDecode(File('test/fixtures/$name').readAsStringSync()) as Map,
  );
}

class FakeApi implements RiceLeafApi {
  FakeApi({
    PredictionResult? result,
    ObservationSchema? schema,
    this.predictionError,
  })  : result = result ??
            PredictionResult.fromJson(
              loadFixture('api_v2_full_response.json'),
            ),
        schema = schema ??
            ObservationSchema.fromJson(
              loadFixture('observation_schema_v1.json'),
            );

  final PredictionResult result;
  final ObservationSchema schema;
  final ApiException? predictionError;
  int predictionCalls = 0;
  Map<String, dynamic>? capturedObservations;

  @override
  Future<BackendHealth> healthCheck() async {
    return const BackendHealth(
      status: 'ok',
      apiVersion: '2.0.0',
      runtimeMode: 'research',
    );
  }

  @override
  Future<ObservationSchema> getObservationSchema() async => schema;

  @override
  Future<SystemInfo> getSystemInfo() async {
    return const SystemInfo(
      apiVersion: '2.0.0',
      runtimeMode: 'research',
      modelFilename: 'rice_model_fixed.keras',
      modelSha256: 'MODEL_HASH',
      classOrder: <String>[],
      reasoningEngineVersion: '1.0.0',
      fusionEngineVersion: '1.0.0',
      artifacts: <ArtifactVersionInfo>[],
    );
  }

  @override
  Future<PredictionResult> predictDisease(
    String imagePath, {
    Map<String, dynamic>? observations,
    void Function(double progress)? onProgress,
  }) async {
    predictionCalls += 1;
    capturedObservations = observations;
    onProgress?.call(0.5);
    if (predictionError != null) {
      throw predictionError!;
    }
    onProgress?.call(1);
    return result;
  }
}
