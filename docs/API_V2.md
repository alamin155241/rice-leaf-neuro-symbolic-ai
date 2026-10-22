# FastAPI v2

## Endpoints

- `GET /` — compatibility health message.
- `GET /health` — status, API version, and runtime mode.
- `GET /v2/system-info` — non-sensitive model filename/hash, class order,
  artifact versions/hashes, and engine versions.
- `GET /v2/observation-schema` — all Phase 6 fields, input types, authoritative
  categorical values, display names, explicit aliases, provenance, and limits.
- `POST /predict` — multipart image prediction.

`POST /predict` fields:

- `file` (required)
- `observations_json` (optional JSON object)
- `runtime_mode` (optional: research, staging, production)
- `include_visualizations` (optional boolean, default true)

Unknown observation fields, invalid types, malformed JSON, and invalid runtime
modes return HTTP 422. Invalid/empty images return 400, oversized uploads return
413, and unexpected server failures return a generic 500 while details remain
in server logs.

The requested mode cannot exceed the server's `NS_RUNTIME_MODE` ceiling.
Escalation attempts return HTTP 403. `/health` and `/v2/system-info` always
report the server-authoritative mode.

Unsupported categorical strings also return HTTP 422. The response detail uses
this safe shape and does not expose an internal path or stack trace:

```json
{
  "error": "unsupported_observation_value",
  "field": "lesion_shape",
  "message": "Unsupported categorical value for 'lesion_shape'.",
  "allowed_values": ["spindle_shaped", "diamond_shaped", "oval", "oblong", "elongated", "narrow"]
}
```

An observation-schema field with a vocabulary returns structured
`allowed_values` entries containing `canonical_value`, `display_name`,
`original_values`, `aliases`, and `provenance`. A field without a closed
categorical vocabulary returns `allowed_values: null` and
`categorical_values_available: false`. Boolean values are returned separately
under `boolean_allowed_values`.

## Nested v2 response

The response includes `cnn_result`, `observation_result`, `visual_evidence`,
`safety_result`, `symbolic_result`, `fusion_result`, `management_result`,
`explanation`, `runtime_mode`, and `artifact_versions`.

`fusion_result.final_prediction` is the authoritative v2 diagnosis and may be
null when safety or unresolved uncertainty withholds diagnosis.
`candidate_prediction` retains the non-authoritative fusion candidate.
`display_name` becomes `Uncertain` when final prediction is null, while
`candidate_display_name` identifies the candidate. `class` and `confidence`
retain their legacy CNN meanings and legacy `final_decision` becomes `uncertain`
when diagnosis is withheld.

For image-only symbolic abstention, `cnn_weight=1.0`,
`symbolic_weight=0.0`, and `abstention_policy_applied=true`. The response also
contains `raw_phase7_cnn_weight`, `raw_phase7_symbolic_weight`, and raw Phase 7
scores for audit. Completed symbolic results expose identical raw and effective
weights.

Explanation separates `provided_observed_features` (value and provenance) from
`matched_observed_features` (only observations reported by fired Phase 6 rules).
Each provided feature also reports `submitted_value`, `normalized_value`,
`enum_validated`, validation type, and vocabulary provenance where applicable.

## Legacy compatibility

All previous top-level fields remain, including visualization Base64 fields.
`infected_area_percent` is an alias of heuristic attention coverage.
`lesion_mask_base64` is a deprecated alias of
`attention_threshold_map_base64`; neither is validated lesion segmentation.

Legacy cause/prevention strings remain only as general compatibility display
content with provenance `legacy_general_guidance`. They carry no invented
evidence IDs or validation claim.
