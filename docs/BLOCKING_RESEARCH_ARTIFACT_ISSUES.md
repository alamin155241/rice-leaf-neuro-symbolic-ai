# Blocking Research Artifact Issues

> Status update (2026-07-31): the categorical-vocabulary issue described below
> is resolved by the conservative, provenance-backed Observation Vocabulary v1.
> Fields without sufficient direct evidence intentionally remain non-categorical;
> see `OBSERVATION_VOCABULARY_V1.md`.

## Resolved: categorical observation vocabulary

`phase6_reasoning_engine/neuro_symbolic_input_schema_v1.json` is a sample-shaped
input template. It does not define JSON Schema `properties`, enums, allowed
categorical values, aliases, or invalid-value behavior.

Observation Vocabulary v1 now provides:

- strict rejection of unknown fields, invalid primitive types, and unsupported
  values on fields with a closed vocabulary;
- provenance-backed allowed values and explicit aliases for supported fields;
- a complete `GET /v2/observation-schema` response suitable for later dropdown
  generation;
- `allowed_values: null` only for fields where approved sources remain
  insufficient.

The deliberate non-categorical gaps are a scientific limitation, not a reason to
invent dropdown options. Image-only behavior and Phase 6/7 numeric behavior are
unchanged.

## XLSX independent rendering

The connected spreadsheet artifact runtime was unavailable during this session.
The XLSX reports were inventoried as reference artifacts; runtime and golden
tests use the authoritative JSON/CSV/notebook sources. No XLSX is a runtime
dependency and no workbook was modified.
