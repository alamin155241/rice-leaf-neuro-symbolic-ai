# FastAPI v2 Integration

## Endpoints

The typed API service supports `GET /health`, `GET /v2/system-info`,
`GET /v2/observation-schema`, and multipart `POST /predict`. The app never sends
`runtime_mode`; the backend remains authoritative.

Every prediction sends the image under multipart field `file`. The optional
`observations_json` field is encoded with `jsonEncode` only when at least one
non-null, non-empty observation exists. Empty objects, strings, lists, untouched
defaults, and null values are removed.

## Diagnosis priority

For v2 responses, `fusion_result.final_prediction` and
`fusion_result.final_confidence` are authoritative. Display names prefer
`fusion_result.display_name`, then a human-readable canonical value. Legacy
fallback uses `final_decision`, then `class`.

A present-but-null v2 `final_prediction` remains `Uncertain`. The
`candidate_prediction` appears separately as **Model candidate** and is never
promoted to the final diagnosis. Manual-review state is read from fusion and
safety results.

The parser tolerates missing optional objects, null predictions, empty rule and
evidence lists, numeric integers/doubles, absent visualizations, and the previous
legacy response structure.

## Observation form

The advanced section is collapsed by default. Dropdown labels and canonical
values come exclusively from `GET /v2/observation-schema`:

- display `display_name`;
- submit `canonical_value`;
- never hardcode scientific options in Dart.

Boolean fields offer Not specified/Yes/No. Not specified is omitted. Numeric
fields remain optional JSON numbers and use no frontend range unless the schema
provides one. Fields without authoritative categorical values are isolated in a
research-only subsection, disabled by default, and labelled **User-confirmed,
not vocabulary validated**.

Selecting a vocabulary value means only that it passed enum validation. The UI
uses backend-returned matched observations to describe rule matches.

## Errors

The service provides stable messages for invalid images (400), policy blocks
(403), oversized images (413), invalid observations (422), server errors (500),
timeouts, and unavailable backends. Safe 422 details display the affected field
and allowed canonical values when supplied by the backend. Internal stack traces
are never expected or rendered.

## Result layout

The result page presents final diagnosis first, followed by effective CNN and
symbolic contributions, safety, provided versus matched observations, evidence
and reasoning, Grad-CAM attention, attention-based severity, management status,
and collapsed technical details. Raw Phase 7 weights are technical-only.

Grad-CAM and the attention threshold map are model-attention heuristics, not
validated lesion segmentation or exact disease area. The legacy
`lesion_mask_base64` is only a fallback for a missing threshold-map field.
