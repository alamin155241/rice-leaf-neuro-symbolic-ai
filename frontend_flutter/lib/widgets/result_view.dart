import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../models/json_parsing.dart';
import '../models/prediction_result.dart';
import '../models/system_info.dart';

class ResultView extends StatelessWidget {
  const ResultView({
    required this.result,
    required this.onReset,
    required this.onRetry,
    this.systemInfo,
    super.key,
  });

  final PredictionResult result;
  final SystemInfo? systemInfo;
  final VoidCallback onReset;
  final VoidCallback onRetry;

  String _percent(double? value) =>
      value == null ? '' : '${(value * 100).toStringAsFixed(2)}%';

  Widget _row(String label, String value, {Key? key}) {
    if (value.trim().isEmpty) {
      return const SizedBox.shrink();
    }
    return Padding(
      key: key,
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 146,
            child: Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  Widget _chip(String text, Color color, {Key? key}) {
    return Chip(
      key: key,
      label: Text(text),
      backgroundColor: color.withValues(alpha: 0.14),
      side: BorderSide(color: color.withValues(alpha: 0.45)),
    );
  }

  Widget _card({
    required String title,
    required List<Widget> children,
    bool collapsible = false,
    bool initiallyExpanded = false,
    Key? key,
  }) {
    final content = collapsible
        ? ExpansionTile(
            title: Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            initiallyExpanded: initiallyExpanded,
            childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            expandedCrossAxisAlignment: CrossAxisAlignment.stretch,
            children: children,
          )
        : Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),
                ...children,
              ],
            ),
          );
    return Card(
      key: key,
      margin: const EdgeInsets.only(top: 12),
      clipBehavior: Clip.antiAlias,
      child: content,
    );
  }

  List<Widget> _bullets(List<String> values, {bool selectable = false}) {
    if (values.isEmpty) {
      return [const Text('No items reported.')];
    }
    return values
        .map(
          (value) => Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('•  '),
                Expanded(
                  child: selectable ? SelectableText(value) : Text(value),
                ),
              ],
            ),
          ),
        )
        .toList(growable: false);
  }

  Widget _finalDiagnosis() {
    final uncertain = result.isUncertain;
    return _card(
      key: const Key('final-diagnosis-card'),
      title: '1. Final diagnosis',
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(
              result.finalDisplayName,
              key: const Key('final-diagnosis-value'),
              style: ThemeData.light().textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: uncertain ? Colors.orange.shade900 : Colors.green.shade800,
                  ),
            ),
            if (uncertain)
              _chip('Uncertain', Colors.orange, key: const Key('uncertain-chip')),
            if (result.requiresManualReview)
              _chip(
                'Manual review required',
                Colors.red,
                key: const Key('manual-review-chip'),
              ),
          ],
        ),
        if (result.confidence != null)
          _row('Fused confidence', _percent(result.confidence)),
        if (uncertain && result.fusion.candidatePrediction != null)
          _row(
            'Model candidate',
            result.fusion.candidateDisplayName,
            key: const Key('model-candidate-row'),
          ),
        if (result.explanation.summary.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(result.explanation.summary),
        ],
        const SizedBox(height: 12),
        Wrap(
          spacing: 8,
          children: [
            OutlinedButton.icon(
              key: const Key('retry-prediction-button'),
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry prediction'),
            ),
            TextButton.icon(
              key: const Key('reset-result-button'),
              onPressed: onReset,
              icon: const Icon(Icons.clear),
              label: const Text('Reset result'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _contributions() {
    final symbolicName = result.symbolic.abstained
        ? 'Abstained'
        : humanizeIdentifier(
            result.symbolic.prediction ?? result.symbolic.researchPrediction,
          );
    return _card(
      title: '2. Decision contributions',
      children: [
        _row('CNN prediction', result.cnn.displayName),
        _row('CNN confidence', _percent(result.cnn.confidence)),
        _row('Symbolic prediction', symbolicName),
        if (result.symbolic.score != null)
          _row('Symbolic score', result.symbolic.score!.toStringAsFixed(4)),
        if (result.symbolic.reliability != null)
          _row(
            'Symbolic reliability',
            result.symbolic.reliability!.toStringAsFixed(4),
          ),
        if (result.fusion.cnnWeight != null)
          _row(
            'Effective CNN weight',
            result.fusion.cnnWeight!.toStringAsFixed(4),
            key: const Key('effective-cnn-weight'),
          ),
        if (result.fusion.symbolicWeight != null)
          _row(
            'Effective symbolic weight',
            result.fusion.symbolicWeight!.toStringAsFixed(4),
            key: const Key('effective-symbolic-weight'),
          ),
        _row('Agreement status', humanizeIdentifier(result.fusion.agreementStatus)),
        _row('Conflict status', humanizeIdentifier(result.fusion.conflictStatus)),
        if (result.symbolic.abstained)
          const Padding(
            padding: EdgeInsets.only(top: 8),
            child: Text(
              'Symbolic reasoning abstained because sufficient structured phenotype observations were not provided.',
              key: Key('symbolic-abstention-message'),
              style: TextStyle(fontStyle: FontStyle.italic),
            ),
          ),
      ],
    );
  }

  Widget _safety() {
    return _card(
      title: '3. Safety and trust',
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _chip(
              result.safety.lowConfidence ? 'Low confidence' : 'Confidence check passed',
              result.safety.lowConfidence ? Colors.orange : Colors.green,
            ),
            _chip(
              result.safety.ambiguityDetected ? 'Ambiguity detected' : 'No ambiguity flag',
              result.safety.ambiguityDetected ? Colors.orange : Colors.green,
            ),
            _chip(
              result.safety.contradictionDetected
                  ? 'Contradiction detected'
                  : 'No contradiction flag',
              result.safety.contradictionDetected ? Colors.red : Colors.green,
            ),
          ],
        ),
        _row('Trust level', humanizeIdentifier(result.trustLevel)),
        _row(
          'Manual review',
          result.requiresManualReview ? 'Required' : 'Not required by backend',
        ),
        if (result.safety.warnings.isNotEmpty) ...[
          const SizedBox(height: 8),
          const Text('Safety warnings', style: TextStyle(fontWeight: FontWeight.bold)),
          ..._bullets(result.safety.warnings),
        ],
      ],
    );
  }

  Widget _observations() {
    final provided = result.observations.providedFeatures;
    final matched = result.explanation.matchedObservedFeatures;
    return _card(
      title: '4. Observations',
      collapsible: true,
      initiallyExpanded: provided.isNotEmpty,
      children: [
        const Text('Provided observations', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        if (provided.isEmpty)
          const Text('No guided observations were provided.')
        else
          ...provided.map(
            (item) => Card(
              color: Colors.green.withValues(alpha: 0.05),
              child: Padding(
                padding: const EdgeInsets.all(10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      humanizeIdentifier(item.field),
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    _row('Submitted', displayValue(item.submittedValue)),
                    if (item.changed)
                      _row('Normalized', displayValue(item.normalizedValue)),
                    _row('Source', humanizeIdentifier(item.source)),
                    _row('Enum validated', item.enumValidated ? 'Yes' : 'No'),
                  ],
                ),
              ),
            ),
          ),
        const SizedBox(height: 12),
        const Text('Rule-matched observations', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 6),
        ..._bullets(matched),
      ],
    );
  }

  String _traceLine(JsonMap trace) {
    final event = asString(trace['event']);
    if (event.isNotEmpty) {
      return humanizeIdentifier(event);
    }
    final ruleId = asString(trace['rule_id']);
    final condition = asString(trace['condition_text']);
    final fired = asBool(trace['fired']) ? 'fired' : 'not fired';
    return [ruleId, condition, fired].where((item) => item.isNotEmpty).join(' — ');
  }

  String _sourceRecordLine(JsonMap record) {
    return [
      asString(record['rule_id']),
      asString(record['source_document_id']),
      asString(record['runtime_state']),
    ].where((item) => item.isNotEmpty).join(' — ');
  }

  Widget _evidence() {
    final ruleIds = result.explanation.matchedRuleIds.isNotEmpty
        ? result.explanation.matchedRuleIds
        : result.symbolic.matchedRuleIds;
    final evidenceIds = result.explanation.evidenceIds.isNotEmpty
        ? result.explanation.evidenceIds
        : result.symbolic.matchedEvidenceIds;
    final trace = result.explanation.reasoningTrace.isNotEmpty
        ? result.explanation.reasoningTrace
        : result.symbolic.reasoningTrace;
    return _card(
      title: '5. Evidence and reasoning',
      collapsible: true,
      children: [
        ExpansionTile(
          title: const Text('Rule and evidence IDs'),
          children: [
            ..._bullets(ruleIds, selectable: true),
            ..._bullets(evidenceIds, selectable: true),
          ],
        ),
        ExpansionTile(
          title: const Text('Citations and source records'),
          children: [
            ..._bullets(result.explanation.citations),
            ..._bullets(
              result.explanation.sourceRecords.map(_sourceRecordLine).where((item) => item.isNotEmpty).toList(),
              selectable: true,
            ),
          ],
        ),
        ExpansionTile(
          title: const Text('Reasoning trace'),
          children: _bullets(
            trace.map(_traceLine).where((item) => item.isNotEmpty).toList(),
            selectable: true,
          ),
        ),
        ExpansionTile(
          title: const Text('Explanation'),
          children: [
            _row('Summary', result.explanation.summary),
            _row('Why CNN contributed', result.explanation.whyCnnContributed),
            _row(
              'Why symbolic contributed',
              result.explanation.whySymbolicContributed,
            ),
            _row(
              'Why final decision',
              result.explanation.whyFinalPredictionWasSelected,
            ),
            const SizedBox(height: 6),
            ..._bullets(result.explanation.limitations),
          ],
        ),
      ],
    );
  }

  Uint8List? _decodeImage(String encoded) {
    if (encoded.trim().isEmpty) {
      return null;
    }
    try {
      return base64Decode(encoded);
    } on FormatException {
      return null;
    }
  }

  Widget _image(String label, String encoded) {
    final bytes = _decodeImage(encoded);
    if (bytes == null) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          Image.memory(
            bytes,
            height: 220,
            fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => const Text('Visualization unavailable.'),
          ),
        ],
      ),
    );
  }

  Widget _visualEvidence() {
    const requiredDisclaimer =
        'Grad-CAM attention is a model-attention heuristic and is not validated lesion segmentation.';
    return _card(
      title: '6. Visual evidence',
      collapsible: true,
      children: [
        _image('Grad-CAM heatmap', result.visualEvidence.gradcamHeatmapBase64),
        _image('Grad-CAM overlay', result.visualEvidence.gradcamOverlayBase64),
        _image(
          'Model attention threshold map',
          result.visualEvidence.attentionThresholdMapBase64,
        ),
        Text(
          result.visualEvidence.disclaimer.isEmpty
              ? requiredDisclaimer
              : result.visualEvidence.disclaimer,
          key: const Key('gradcam-disclaimer'),
          style: TextStyle(
            fontWeight: FontWeight.w600,
            color: Colors.orange.shade900,
          ),
        ),
      ],
    );
  }

  Widget _severity() {
    return _card(
      title: '7. Attention-based severity estimate',
      children: [
        _row('Severity heuristic', humanizeIdentifier(result.severity)),
        if (result.visualEvidence.attentionCoveragePercent != null)
          _row(
            'Attention coverage',
            '${result.visualEvidence.attentionCoveragePercent!.toStringAsFixed(2)}%',
          ),
        _row(
          'Segmentation validated',
          result.visualEvidence.segmentationValidated ? 'Yes' : 'No',
        ),
        const Text(
          'This is an attention-based heuristic, not an exact infected-area measurement.',
          style: TextStyle(fontStyle: FontStyle.italic),
        ),
      ],
    );
  }

  String _managementSource(Object? source) {
    if (source is Map) {
      final json = asJsonMap(source);
      return [
        asString(json['rule_id']),
        asString(json['source_document_id']),
        asString(json['citation']),
      ].where((item) => item.isNotEmpty).join(' — ');
    }
    return asString(source);
  }

  Widget _management() {
    return _card(
      title: '8. Management guidance',
      collapsible: true,
      initiallyExpanded: true,
      children: [
        _row('Recommendation', result.management.recommendation),
        _row('Warning', result.management.warning),
        _row('Actionable', result.management.actionable ? 'Yes' : 'No'),
        _row('Advisory only', result.management.advisoryOnly ? 'Yes' : 'No'),
        _row(
          'Validation status',
          humanizeIdentifier(result.management.validationStatus),
        ),
        _row('Runtime state', humanizeIdentifier(result.management.runtimeState)),
        if (!result.management.actionable)
          Container(
            key: const Key('management-advisory-badge'),
            margin: const EdgeInsets.symmetric(vertical: 8),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.orange.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text(
              'Advisory research information — not validated treatment instruction.',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        if (result.management.sources.isNotEmpty) ...[
          const Text('Sources', style: TextStyle(fontWeight: FontWeight.bold)),
          ..._bullets(
            result.management.sources
                .map(_managementSource)
                .where((item) => item.isNotEmpty)
                .toList(),
          ),
        ],
      ],
    );
  }

  Widget _technical() {
    final info = systemInfo;
    final artifacts = result.artifacts.isNotEmpty
        ? result.artifacts
        : info?.artifacts ?? const <ArtifactVersionInfo>[];
    return _card(
      title: '9. Technical details',
      collapsible: true,
      children: [
        _row('API version', result.apiVersion),
        _row('Runtime mode', humanizeIdentifier(result.runtimeMode)),
        if (info != null) ...[
          _row('Reasoning engine', info.reasoningEngineVersion),
          _row('Fusion engine', info.fusionEngineVersion),
        ],
        if (result.fusion.rawPhase7CnnWeight != null)
          _row(
            'Raw Phase 7 CNN weight',
            result.fusion.rawPhase7CnnWeight!.toStringAsFixed(4),
          ),
        if (result.fusion.rawPhase7SymbolicWeight != null)
          _row(
            'Raw Phase 7 symbolic weight',
            result.fusion.rawPhase7SymbolicWeight!.toStringAsFixed(4),
          ),
        if (artifacts.isNotEmpty) ...[
          const SizedBox(height: 8),
          const Text('Artifact versions', style: TextStyle(fontWeight: FontWeight.bold)),
          ...artifacts.map(
            (artifact) => SelectableText(
              '${artifact.logicalName}: ${artifact.version} — ${artifact.sha256}',
            ),
          ),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _finalDiagnosis(),
        _contributions(),
        _safety(),
        _observations(),
        _evidence(),
        _visualEvidence(),
        _severity(),
        _management(),
        _technical(),
      ],
    );
  }
}
