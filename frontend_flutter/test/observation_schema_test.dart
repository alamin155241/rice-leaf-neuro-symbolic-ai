import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend_flutter/models/observation_schema.dart';

ObservationSchema schemaFixture() {
  final json = jsonDecode(
    File('test/fixtures/observation_schema_v1.json').readAsStringSync(),
  );
  return ObservationSchema.fromJson(Map<String, dynamic>.from(json as Map));
}

void main() {
  test('parses observation schema and authoritative allowed values', () {
    final schema = schemaFixture();
    final shape = schema.fields['lesion_shape']!;

    expect(schema.version, '1.0.0');
    expect(shape.categoricalValuesAvailable, isTrue);
    expect(shape.allowedValues.first.canonicalValue, 'spindle_shaped');
    expect(shape.allowedValues.first.displayName, 'Spindle-shaped');
    expect(shape.allowedValues.first.provenance.sourceIds, ['fixture_source']);
  });

  test('serializes boolean tri-state and omits not specified', () {
    final schema = schemaFixture();
    final draft = ObservationDraft();

    expect(draft.toJson(schema), isEmpty);
    draft.setValue('lesion_present', true);
    expect(draft.toJson(schema), {'lesion_present': true});
    draft.setValue('lesion_present', false);
    expect(draft.toJson(schema), {'lesion_present': false});
    draft.setValue('lesion_present', null);
    expect(draft.toJson(schema), isEmpty);
  });

  test('serializes optional numeric observation as JSON number', () {
    final schema = schemaFixture();
    final draft = ObservationDraft()..setValue('lesion_width_mm', '1.25');

    expect(draft.toJson(schema), {'lesion_width_mm': 1.25});
  });

  test('rejects invalid numeric formatting', () {
    final schema = schemaFixture();
    final draft = ObservationDraft()..setValue('lesion_width_mm', 'wide');

    expect(() => draft.toJson(schema), throwsA(isA<ObservationInputException>()));
  });

  test('omits empty values and research free text by default', () {
    final schema = schemaFixture();
    final draft = ObservationDraft()
      ..setValue('lesion_shape', '')
      ..setValue('other_observations', <String>[])
      ..setValue('dryness', 'user text');

    expect(draft.toJson(schema), isEmpty);
    expect(
      draft.toJson(schema, includeResearchFreeText: true),
      {'dryness': 'user text'},
    );
  });

  test('submits canonical value rather than display label', () {
    final schema = schemaFixture();
    final allowed = schema.fields['lesion_shape']!.allowedValues.first;
    final draft = ObservationDraft()
      ..setCategorical('lesion_shape', allowed);

    expect(allowed.displayName, 'Spindle-shaped');
    expect(draft.toJson(schema), {'lesion_shape': 'spindle_shaped'});
  });
}
