# Pre-Integration Audit

## Scope and baseline

This audit was completed before modifying application source for the Phase 5,
Phase 6, and Phase 7 integration.

- Project root: the current workspace root.
- Git status: Git is not configured in this directory, so no repository or
  history was initialized.
- Source backup: `_backup_pre_neuro_symbolic_integration/`
- Model: `models/rice_model_fixed.keras`
- Pre-integration SHA-256:
  `3F91DA161D761F0DA3BC4C157115F44F1A8CD25B3DF624BD2B79AD77A6FC7A94`
- Existing backend test baseline: 12 passed.

The backup contains only source and configuration files expected to change. It
does not contain model files, virtual environments, Flutter build output, APKs,
or caches.

## Current runtime pipeline

Before this integration, the working request flow was:

1. `main.py` accepts an uploaded image.
2. `predictor.py` loads `rice_model_fixed.keras` once.
3. The image is converted to RGB, resized to 224 × 224, and processed through
   EfficientNet preprocessing.
4. The CNN returns probabilities in this hardcoded order:
   `brown_spot`, `healthy`, `leaf_blast`, `leaf_scald`,
   `narrow_brown_spot`.
5. Grad-CAM is generated from the last four-dimensional layer.
6. A threshold of 0.45 is applied to the Grad-CAM heatmap and reported as
   attention coverage, with `infected_area_percent` retained as a legacy alias.
7. `predictor.py` retrieves class-selected phenotype knowledge and a local draft
   knowledge base.
8. `neuro_symbolic/rule_engine.py` applies confidence, ambiguity, attention, and
   class-selected phenotype logic.
9. `conflict_resolution/conflict_resolver.py` selects one management rule using
   application-defined scores.
10. FastAPI serializes legacy fields and Base64 images.

## Current modules and dependencies

### Backend

- `main.py`: FastAPI routes, upload checks, response model, legacy
  cause/prevention strings.
- `predictor.py`: TensorFlow model loading, image preprocessing, CNN inference,
  Grad-CAM, attention heuristic, and the active prototype reasoning pipeline.
- `neuro_symbolic/rule_engine.py`: prototype symbolic/safety matching.
- `conflict_resolution/conflict_resolver.py`: management recommendation
  precedence.
- `knowledge_base/knowledge_service.py`: loads the locally authored
  `validated_knowledge.json`.
- `knowledge_graph/graph_query.py`: loads class-indexed phenotype descriptions.
- `rules.py`: deprecated compatibility wrapper.

Runtime dependencies are FastAPI, Uvicorn, python-multipart, Pillow, NumPy, and
TensorFlow. Pytest is used for tests. The working environment is Python 3.13 /
TensorFlow 2.21.

### Flutter

- `lib/services/api_service.dart`: uploads the image and parses JSON through a
  typed result.
- `lib/models/prediction_result.dart`: supports legacy and current prototype
  fields.
- `lib/screens/home_screen.dart`: image selection, preview, progress, expandable
  result sections, and Base64 visualization display.
- `lib/config/app_config.dart`: compile-time backend base URL.

## Current API response

`POST /predict` returns these top-level fields:

- `class`, `final_decision`, `confidence`
- `cause`, `prevention`, `recommendation`, `warning`
- `trust_level`, `severity`
- `infected_area_percent`, `attention_coverage_percent`
- `second_class`, `second_confidence`, `all_probabilities`
- `reasoning_notes`, `phenotype_facts`, `knowledge_sources`
- `matched_rules`, `conflicts_detected`, `selected_rule`
- `conflict_resolution_note`
- `ambiguity_detected`, `contradiction_detected`
- `gradcam_heatmap_base64`, `gradcam_overlay_base64`,
  `lesion_mask_base64`

The endpoint has a 10 MB upload limit and generic internal-error handling.

## Current Flutter parsing

The client prefers `class`, then the older `final_label` and
`neural_prediction` fields. It currently has no nested API-v2 model, no adaptive
fusion fields, and no guided observation payload. The backend URL can be
overridden with `BACKEND_BASE_URL`.

## Existing tests

The baseline suite has 12 passing backend tests:

- phenotype graph retrieval and unknown-class behavior;
- high/low confidence and ambiguity safeguards;
- consistent and contradictory healthy predictions;
- management conflict scoring and fallback;
- legacy response-field compatibility.

One Flutter widget test verifies that the home screen renders.

The existing tests do not cover the authoritative research artifacts, runtime
state gating, Phase 6 numeric parity, Phase 7 adaptive fusion parity,
anti-circularity, structured observations, API v2, or model-hash preservation.

## VS Code and Pylance observations

- No workspace-level Python analysis configuration is present.
- The environment does not contain `pyright`, so a command-line Pylance-equivalent
  audit could not be run.
- Two narrow `type: ignore[return-value]` comments exist in
  `knowledge_graph/graph_query.py` and `knowledge_base/knowledge_service.py`.
  They should be removed rather than expanding analysis suppression.
- The Python 3.10 / TensorFlow 2.8 `newenv` cannot load the active Keras model;
  `.venv` is the compatible environment.

## Conflicting, duplicate, and stale rule systems

1. `knowledge_base/validated_knowledge.json` is a locally authored draft and is
   not the authoritative Phase 5 rule base.
2. `knowledge_graph/phenotype_graph.json` provides general class knowledge, but
   the prototype presents class-selected descriptions as if they were image
   observations. This is circular and scientifically invalid.
3. `neuro_symbolic/rule_engine.py` is not the Phase 6 notebook algorithm.
4. `conflict_resolution/conflict_resolver.py` resolves management guidance; it
   is not the Phase 7 diagnostic conflict resolver.
5. `rules.py` is retained only for compatibility.
6. Phase 5 contains a duplicate `HRULE_001` identifier for two different
   healthy-baseline records. The source records must be preserved unchanged and
   identified by additional provenance when uniqueness is required.

## Authoritative research files

### Phase 5

- `evidence_aware_rules_v1.json` — 61 unique rule records.
- `rule_schema_v1.json` — partial JSON Schema for rule records.
- `phase5_rule_statistics_v1.json`
- `rule_validation_report_v1.csv`
- `duplicate_rule_report_v1.csv`
- `evidence_aware_rules_v1.csv`
- reference XLSX reports and master dataset.

Phase 5 runtime states:

- `ACTIVE_CANDIDATE`: 1
- `STAGING_CANDIDATE`: 15
- `EVIDENCE_SUPPORTED_HOLD`: 41
- `HOLD_PARSE_INCOMPLETE`: 4

### Phase 6

- `Phase6B_Neuro_Symbolic_Reasoning_Engine.ipynb`
- `reasoning_engine_config_v1.json`
- `neuro_symbolic_input_schema_v1.json`
- `reasoning_test_results_v1.json`
- `reasoning_trace_v1.csv`
- reference XLSX report.

The notebook was inspected cell by cell. Its implemented functions include
normalization, observation flattening, runtime-state gating, phrase matching,
rule evaluation, disease scoring, symbolic confidence categories, and exported
traces.

### Phase 7

- `Phase7_Adaptive_CNN_Symbolic_Fusion.ipynb`
- `fusion_engine_config_v1.json`
- `cnn_output_schema_v1.json`
- `fusion_results_v1.json`
- `conflict_stress_test_results_v1.json`
- `fusion_summary_v1.csv`
- reference XLSX report.

The notebook was inspected cell by cell. Its implemented functions include
probability normalization, normalized entropy, CNN reliability, symbolic
reliability, bounded adaptive weights, score fusion, diagnostic conflict
detection, and decision-status assignment.

The XLSX files are reference/report artifacts, not runtime sources. The required
spreadsheet artifact-tool runtime was not available in this session, so the XLSX
files could not receive an independent rendered workbook audit. Their exported
JSON and CSV counterparts were inspected and will be the parity sources. No
runtime behavior will be inferred from an unread workbook.

## Critical scientific findings

1. The Phase 6 notebook's `flatten_observations` function appends the CNN
   predicted class to the observation list. Golden research outputs therefore
   include a circular signal. Runtime integration must remove this signal.
   Notebook parity will be tested in a clearly isolated compatibility mode;
   safe runtime mode will never treat the CNN label as observed phenotype.
2. The existing application does not extract lesion morphology or color.
   Image-only input must leave those values missing and normally produce
   symbolic abstention.
3. Grad-CAM supplies attention only. It cannot populate phenotype fields or
   validate lesion area.
4. The Phase 6 input artifact is a template, not a categorical JSON Schema. It
   lists fields and primitive examples but provides no allowed categorical
   vocabulary. Strict enum validation and a finite guided-observation UI cannot
   be derived from it without a supplementary authoritative vocabulary.
5. Only the active healthy identity rule is allowed in production, and it still
   requires an explicit observation (`Oryza_sativa` identity). An image-only
   request cannot satisfy it.
6. Research mode legitimately evaluates evidence-supported holds. Those matches
   are advisory research evidence, not actionable expert-validated management.
7. The Phase 7 notebook uses dynamic reliability weights with 0.10/0.90 bounds.
   Those formulas must be copied exactly; management policy scores must never be
   fed into diagnostic fusion.

## Anticipated migration risks

- Preserving exact notebook golden parity while removing circular runtime input
  requires an explicitly isolated parity option.
- Phase 5 duplicate IDs require provenance-aware identifiers in traces without
  changing source records.
- The Phase 5 schema is intentionally partial and does not validate every nested
  field.
- Existing Flutter models assume a flat response and require additive nested-v2
  parsing without breaking legacy behavior.
- Base64 responses remain large.
- Model import is expensive; pure research-engine tests must not import
  TensorFlow.
- Production mode may have no diagnostic symbolic match and must abstain rather
  than activating held rules.
- No performance improvement may be claimed without Phase 9 evaluation.

## Migration policy

- Preserve the model, preprocessing, class order, Grad-CAM gradient path, and
  legacy response fields.
- Copy only authoritative JSON artifacts into a versioned runtime directory.
- Validate hashes and class mapping at startup.
- Keep image-only observations empty except for explicitly sourced attention
  metadata.
- Keep diagnostic and management conflict resolution separate.
- Preserve original research artifacts byte-for-byte.
- Document any parity or schema blocker instead of inventing missing logic.
