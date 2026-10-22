import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend_flutter/models/prediction_result.dart';

Map<String, dynamic> fixture(String name) {
  return Map<String, dynamic>.from(
    jsonDecode(File('test/fixtures/$name').readAsStringSync()) as Map,
  );
}

void main() {
  test('parses full v2 response and prioritizes fused diagnosis', () {
    final result = PredictionResult.fromJson(
      fixture('api_v2_full_response.json'),
    );

    expect(result.finalPrediction, 'leaf_blast');
    expect(result.finalDisplayName, 'Leaf Blast');
    expect(result.confidence, 0.81);
    expect(result.cnn.prediction, 'brown_spot');
    expect(result.symbolic.prediction, 'leaf_blast');
    expect(result.fusion.cnnWeight, 0.45);
    expect(result.symbolic.matchedRules.single.ruleId, 'EA_RULE_TEST');
    expect(result.management.actionable, isFalse);
    expect(result.artifacts.single.logicalName, 'observation_vocabulary');
  });

  test('parses legacy response without nested v2 fields', () {
    final result = PredictionResult.fromJson(fixture('legacy_response.json'));

    expect(result.finalPrediction, 'leaf_scald');
    expect(result.finalDisplayName, 'Leaf Scald');
    expect(result.confidence, 0.91);
    expect(result.cnn.prediction, 'leaf_scald');
    expect(result.visualEvidence.attentionThresholdMapBase64, isNotEmpty);
  });

  test('null final prediction remains uncertain and does not use candidate', () {
    final result = PredictionResult.fromJson(
      fixture('api_v2_safety_uncertain.json'),
    );

    expect(result.finalPrediction, isNull);
    expect(result.finalDisplayName, 'Uncertain');
    expect(result.isUncertain, isTrue);
    expect(result.fusion.candidatePrediction, 'leaf_blast');
    expect(result.fusion.candidateDisplayName, 'Leaf Blast');
    expect(result.requiresManualReview, isTrue);
  });

  test('represents symbolic abstention and effective weights', () {
    final result = PredictionResult.fromJson(
      fixture('api_v2_symbolic_abstention.json'),
    );

    expect(result.symbolic.abstained, isTrue);
    expect(result.symbolic.prediction, isNull);
    expect(result.symbolic.reliability, 0);
    expect(result.fusion.abstentionPolicyApplied, isTrue);
    expect(result.fusion.cnnWeight, 1);
    expect(result.fusion.symbolicWeight, 0);
    expect(result.fusion.rawPhase7SymbolicWeight, 0.1);
  });

  test('separates provided and backend-matched observations', () {
    final result = PredictionResult.fromJson(
      fixture('api_v2_guided_observation.json'),
    );

    final provided = result.observations.providedFeatures.single;
    expect(provided.submittedValue, 'greyish');
    expect(provided.normalizedValue, 'gray');
    expect(provided.enumValidated, isTrue);
    expect(result.explanation.matchedObservedFeatures, [
      'lesion center color gray',
    ]);
  });

  test('uses threshold-map field before legacy lesion-mask fallback', () {
    final current = PredictionResult.fromJson({
      'visual_evidence': {'attention_threshold_map_base64': 'current'},
      'lesion_mask_base64': 'legacy',
    });
    final legacy = PredictionResult.fromJson({
      'lesion_mask_base64': 'legacy',
    });

    expect(current.visualEvidence.attentionThresholdMapBase64, 'current');
    expect(legacy.visualEvidence.attentionThresholdMapBase64, 'legacy');
  });

  test('missing optional nested fields parse safely', () {
    final result = PredictionResult.fromJson(<String, dynamic>{});

    expect(result.finalPrediction, isNull);
    expect(result.finalDisplayName, 'Uncertain');
    expect(result.symbolic.matchedRules, isEmpty);
    expect(result.explanation.evidenceIds, isEmpty);
    expect(result.gradcamHeatmapBase64, isEmpty);
  });
}
