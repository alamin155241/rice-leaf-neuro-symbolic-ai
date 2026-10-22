# Pre-v2 Flutter State

Recorded before the controlled FastAPI v2 Flutter integration.

## Existing response fields

The current parser reads legacy fields including `class`, `final_decision`,
`confidence`, `cause`, `prevention`, `recommendation`, `warning`, `trust_level`,
`severity`, attention/infected-area percentages, second prediction, probability
maps, reasoning notes, phenotype facts, knowledge sources, matched rules,
conflicts, selected rule, ambiguity/contradiction flags, and the three legacy
visualization strings.

It also partially reads nested `cnn_result`, `symbolic_result`, `fusion_result`,
`safety_result`, `observation_result`, `visual_evidence`, `management_result`, and
`explanation`. The partial model does not yet represent the complete v2 contract
or safety-withheld final/candidate distinction.

## Existing screens and flow

The application has one `HomeScreen`. It provides gallery image selection,
preview, a prediction progress state, backend error text/snackbars, a collapsed
advanced-observation section, and expansion-tile result sections. Image-only
submission is already the default workflow.

## Backend URL configuration

`BACKEND_BASE_URL` is supplied with `--dart-define`. Before this update its
default is `http://192.168.1.100:8000`; endpoint strings are derived in
`lib/config/app_config.dart`. The integration will retain dart-define support and
replace manual string concatenation with `Uri` path construction.

## Previously modified Flutter files

The earlier deferred backend stage records partial, unvalidated changes in:

- `lib/config/app_config.dart`
- `lib/models/prediction_result.dart`
- `lib/services/api_service.dart`
- `lib/screens/home_screen.dart`
- `test/prediction_result_test.dart`

`test/widget_test.dart` was previously unchanged. The partial work had one
successful analyzer run, but Flutter tests were never confirmed complete.

## Current limitations

- Observation fields are rendered mostly as unrestricted text inputs rather
  than authoritative schema-backed dropdowns.
- Observation schema parsing is untyped.
- Safety-withheld null final predictions and candidates are not fully separated.
- Provided and rule-matched observations are not fully represented.
- API errors do not decode safe 422 field/allowed-value details.
- Health and system-information methods are missing.
- The result page omits multiple v2 safety, management, trace, and technical
  fields.
- Unit/widget fixtures and offline service mocks are incomplete.

## Backup

The source-only backup created immediately before this integration is:

`frontend_flutter_backup_before_v2/`

It contains only `lib/`, `test/`, `pubspec.yaml`, `pubspec.lock`, and
`android/app/src/main/AndroidManifest.xml`. It excludes build output, Gradle
caches, APKs, and `.dart_tool`.
