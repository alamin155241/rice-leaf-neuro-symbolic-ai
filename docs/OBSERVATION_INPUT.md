# Structured Observation Input

Image-only operation leaves every unavailable phenotype field unknown. It does
not infer lesion shape, color, center, margin, size, distribution, leaf region,
halo, blighting, dryness, or other symptoms from the CNN or Grad-CAM.

Optional multipart `observations_json` accepts fields represented by the Phase 6
input template. Pydantic rejects unknown fields and invalid data types. Every
supplied field is recorded with source `user_confirmed`. Attention coverage and
severity heuristic are separately recorded with source
`gradcam_attention_heuristic` and are not used as phenotype observations.

Example:

```json
{
  "lesion_present": true,
  "lesion_shape": "spindle-shaped",
  "lesion_center_color": "greyish",
  "leaf_region": "leaf blade",
  "other_observations": ["leaf blast spot present"]
}
```

The submitted text is user-provided. Explicit aliases normalize before Phase 6;
for example, `spindle-shaped` becomes `spindle_shaped` and `greyish` becomes
`gray`. Both submitted and normalized values remain in the response trace.

`None`, empty strings, empty lists, and empty objects are removed before
provenance assignment. Therefore an empty JSON object and the default empty
`other_observations` list behave as image-only input and are not marked
`user_confirmed`.

The response distinguishes:

- `provided_observed_features`: submitted value, normalized value,
  `user_confirmed` provenance, and enum-validation status;
- `matched_observed_features`: normalized observations referenced by fired Phase
  6 rule matches only.

A provided value may remain unmatched. It is never labelled matched merely
because the user supplied it.

The supplementary `observation_vocabulary_v1.json` supplies closed,
provenance-backed values only where the approved sources support them.
Unsupported strings on those fields return HTTP 422. Fields still lacking a
vocabulary retain `allowed_values: null`: research accepts their free text with
`enum_validated=false`; staging and production require the server-controlled
`ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS=true` override.
