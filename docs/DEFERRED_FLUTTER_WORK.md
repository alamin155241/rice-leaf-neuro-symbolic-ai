# Deferred Flutter Work

Flutter work and all Flutter/Dart validation were stopped and explicitly
deferred on 2026-07-31. No further edits are permitted in the frozen frontend
paths during this backend stage.

## Files changed before the freeze

- `frontend_flutter/lib/config/app_config.dart` — added the v2 observation-schema
  endpoint. Appears structurally complete but is not validated.
- `frontend_flutter/lib/models/prediction_result.dart` — added nested v2 parsing,
  fused-result preference, legacy fallbacks, abstention/safety/evidence fields,
  and threshold-map fallback. Partial/unvalidated.
- `frontend_flutter/lib/services/api_service.dart` — added optional
  `observations_json` serialization and observation-schema fetching.
  Partial/unvalidated.
- `frontend_flutter/lib/screens/home_screen.dart` — added a dynamic, collapsed
  guided-observation section and v2 result sections. Partial/unvalidated.
- `frontend_flutter/test/prediction_result_test.dart` — new parser tests for v2,
  legacy, and abstention behavior. Test execution was interrupted/deferred.

`frontend_flutter/test/widget_test.dart` is unchanged relative to the backup.
No verified backup copy was found for `lib/main.dart`, but it was not
intentionally edited. A pre-integration frontend backup exists at
`_backup_pre_neuro_symbolic_integration/frontend_flutter/`.

## Validation status and risk

One `flutter analyze` run completed with **No issues found** after the edits.
Flutter tests did not complete and must not be treated as passed. Later `dart
format`/test attempts stalled or were interrupted before the freeze. The current
files may therefore contain incomplete UI behavior, unformatted code, an
unverified network-loading lifecycle, or test-runner issues.

Do not claim Flutter v2 integration is complete.

## Backend fields for later parsing

Prefer:

- `fusion_result.final_prediction` and `final_confidence`
- `cnn_result`
- `symbolic_result`, including abstention status
- adaptive weights and agreement/conflict fields in `fusion_result`
- `observation_result`
- `safety_result.warnings`
- `management_result` actionability/validation
- `explanation` rule/evidence/citation trace
- `visual_evidence` and its disclaimer
- `runtime_mode` and `artifact_versions`

Fall back to `final_decision`, then `class`, for legacy servers. Treat
`attention_threshold_map_base64` as the preferred threshold map and
`lesion_mask_base64` only as its deprecated alias.

## Later frontend tasks

- Review the partial dynamic form against the final backend schema.
- Decide how to handle free text because the research artifact has no enum
  vocabulary.
- Verify abstention, conflict, safety, evidence, artifact, and management UI.
- Verify upload error display and physical-device behavior.
- Review all parser tests and widget lifecycle behavior.

Commands for the later Flutter stage only:

```powershell
flutter pub get
dart format lib test
flutter analyze
flutter test
```
