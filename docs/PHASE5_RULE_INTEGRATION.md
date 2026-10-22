# Phase 5 Rule Integration

The runtime authority is `research_artifacts/runtime_v1/evidence_aware_rules_v1.json`.
It is a byte-identical deployment copy of the original Phase 5 JSON and is
validated record-by-record against `rule_schema_v1.json`.

## Inventory

- Total unique rules: 61
- `ACTIVE_CANDIDATE`: 1
- `STAGING_CANDIDATE`: 15
- `EVIDENCE_SUPPORTED_HOLD`: 41
- `HOLD_PARSE_INCOMPLETE`: 4

Rule type counts are 21 diagnostic, 13 environmental support, 11 healthy
baseline, 8 supporting knowledge, 7 management, and 1 severity.

The loader preserves every source record, including rule ID, conditions,
conclusion, priority, provisional weight, runtime state, runtime-enabled flag,
validation object, provenance, evidence IDs, source document, citation, record
IDs, original value, normalized value, and notes.

Management records are filtered separately after diagnosis. The supplied
management rules have stored `NEEDS_*` validation categories; these are not
relabelled as expert validated. When no authoritative actionable record exists,
the API returns a conservative fallback and may expose research candidates only
as advisory records.

The original package is unchanged and Excel/CSV reports are not runtime
dependencies.
