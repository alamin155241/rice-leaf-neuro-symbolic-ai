# Changelog

## 1.1.0 - 2026-07-31

- Added a hash-manifested, provenance-backed vocabulary for all 21 Phase 6
  observation fields and a Draft 2020-12 validation schema.
- Added strict canonical/explicit-alias normalization and HTTP 422 rejection for
  unsupported categorical values.
- Preserved submitted and normalized values, enum-validation status, user
  provenance, and matched rule conditions in reasoning traces.
- Kept unsupported free-text fields explicit and applied server-controlled
  staging/production gating without changing Phase 6 or Phase 7 scoring.
- Added the full observation vocabulary to `GET /v2/observation-schema`.
- Added backend tests covering the 22 requested vocabulary, integrity, policy,
  reasoning, golden-parity, and model-immutability behaviors.

## 1.0.1 - 2026-07-31

- Made `NS_RUNTIME_MODE` a server-authoritative ceiling and rejected request
  escalation.
- Converted the prototype rule engine to a deprecated safety-only adapter.
- Added effective CNN-only weighting for symbolic abstention while preserving
  raw Phase 7 results.
- Corrected authoritative final versus candidate prediction semantics.
- Separated provided observations from observations matched by fired rules.
- Filtered empty guided defaults before assigning user provenance.
- Added production gating for unvalidated guided free text.
- Vendored and hash-manifested self-contained Phase 6/7 golden fixtures.
- Added a verified primary dependency lock for CPython 3.13.2.
- Scoped root pytest discovery to the live `tests/` directory.

## 1.0.0 - 2026-07-31

- Added a hashed, versioned runtime artifact package.
- Added centralized five-class validation and mapping.
- Refactored the exact Phase 6 notebook reasoner into cached Python modules.
- Refactored the exact Phase 7 adaptive fusion algorithm.
- Removed class-derived phenotype knowledge from the active prediction path.
- Added transparent image-only symbolic abstention.
- Added optional strictly typed guided observations with user provenance.
- Separated safety, diagnostic conflict, and management resolution.
- Added constrained, evidence-traceable explanations.
- Added FastAPI v2 nested outputs and new health/system/schema endpoints while
  preserving legacy fields.
- Added `attention_threshold_map_base64` and retained the deprecated
  `lesion_mask_base64` alias.
- Added golden, anti-circularity, gating, actionability, API, hash, and smoke
  tests.
- Preserved the model file, preprocessing, class order, and Grad-CAM pipeline.
- Deferred Flutter v2 completion and validation.
