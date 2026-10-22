import 'package:flutter/material.dart';

import '../models/observation_schema.dart';

class ObservationFormController extends ChangeNotifier {
  final ObservationDraft _draft = ObservationDraft();
  bool _researchFreeTextEnabled = false;
  int _revision = 0;

  bool get researchFreeTextEnabled => _researchFreeTextEnabled;
  int get revision => _revision;
  Object? valueFor(String field) => _draft.valueFor(field);

  void setValue(String field, Object? value) {
    _draft.setValue(field, value);
    notifyListeners();
  }

  void setResearchFreeTextEnabled(bool enabled) {
    _researchFreeTextEnabled = enabled;
    notifyListeners();
  }

  Map<String, dynamic> toJson(ObservationSchema schema) {
    return _draft.toJson(
      schema,
      includeResearchFreeText: _researchFreeTextEnabled,
    );
  }

  void clear() {
    _draft.clear();
    _researchFreeTextEnabled = false;
    _revision += 1;
    notifyListeners();
  }
}

class ObservationForm extends StatelessWidget {
  const ObservationForm({
    required this.schema,
    required this.controller,
    super.key,
  });

  final ObservationSchema schema;
  final ObservationFormController controller;

  Widget _dropdown(ObservationFieldSchema field) {
    final items = <DropdownMenuItem<Object>>[];
    if (field.supportsBoolean) {
      items.addAll(const [
        DropdownMenuItem<Object>(value: true, child: Text('Yes')),
        DropdownMenuItem<Object>(value: false, child: Text('No')),
      ]);
    }
    if (field.categoricalValuesAvailable) {
      items.addAll(
        field.allowedValues.map(
          (value) => DropdownMenuItem<Object>(
            value: value.canonicalValue,
            child: Text(value.displayName),
          ),
        ),
      );
    }
    return DropdownButtonFormField<Object>(
      key: Key('observation-dropdown-${field.name}'),
      value: controller.valueFor(field.name),
      isExpanded: true,
      decoration: InputDecoration(
        labelText: field.displayName,
        helperText: field.categoricalValuesAvailable
            ? 'Options supplied by the backend vocabulary'
            : 'Optional schema-defined boolean',
        border: const OutlineInputBorder(),
      ),
      hint: const Text('Not specified'),
      items: items,
      onChanged: (value) => controller.setValue(field.name, value),
    );
  }

  Widget _numberField(ObservationFieldSchema field) {
    return TextFormField(
      key: ValueKey('number-${field.name}-${controller.revision}'),
      initialValue: controller.valueFor(field.name)?.toString(),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(
        labelText: field.displayName,
        helperText: 'Optional number; no range is invented by the app',
        border: const OutlineInputBorder(),
      ),
      onChanged: (value) => controller.setValue(field.name, value),
    );
  }

  Widget _researchField(ObservationFieldSchema field) {
    return TextFormField(
      key: ValueKey('research-${field.name}-${controller.revision}'),
      initialValue: controller.valueFor(field.name)?.toString(),
      maxLines: field.supportsArray ? 2 : 1,
      decoration: InputDecoration(
        labelText: field.displayName,
        helperText: field.supportsArray
            ? 'User-confirmed, not vocabulary validated; separate items with commas'
            : 'User-confirmed, not vocabulary validated',
        border: const OutlineInputBorder(),
      ),
      onChanged: (value) => controller.setValue(field.name, value),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final primaryFields = schema.primaryFields.toList(growable: false);
        final researchFields = schema.researchOnlyFields.toList(growable: false);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Only confirm symptoms you directly observed. These selections are optional.',
            ),
            const SizedBox(height: 12),
            ...primaryFields.map(
              (field) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: field.supportsNumber
                    ? _numberField(field)
                    : _dropdown(field),
              ),
            ),
            if (researchFields.isNotEmpty)
              ExpansionTile(
                key: const Key('research-only-observations'),
                title: const Text('Research-only unvalidated fields'),
                subtitle: const Text(
                  'Disabled by default and may be rejected by staging or production policy.',
                ),
                childrenPadding: const EdgeInsets.fromLTRB(0, 0, 0, 12),
                children: [
                  SwitchListTile(
                    key: const Key('enable-research-free-text'),
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Enable research-only free text'),
                    subtitle: const Text(
                      'User-confirmed, not vocabulary validated',
                    ),
                    value: controller.researchFreeTextEnabled,
                    onChanged: controller.setResearchFreeTextEnabled,
                  ),
                  if (controller.researchFreeTextEnabled)
                    ...researchFields.map(
                      (field) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: _researchField(field),
                      ),
                    ),
                ],
              ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                key: const Key('clear-observations-button'),
                onPressed: controller.clear,
                icon: const Icon(Icons.clear_all),
                label: const Text('Clear observations'),
              ),
            ),
          ],
        );
      },
    );
  }
}
