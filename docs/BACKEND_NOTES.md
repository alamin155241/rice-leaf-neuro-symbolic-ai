# Rice Leaf Neuro-Symbolic Backend

This workspace contains a FastAPI + TensorFlow rice-leaf diagnosis backend with
the authoritative Phase 5 rule records, the exact Phase 6 notebook reasoner, and
the exact Phase 7 adaptive fusion algorithm.

The trained model was not retrained, converted, or modified. Its SHA-256 before
and after integration is:

`3F91DA161D761F0DA3BC4C157115F44F1A8CD25B3DF624BD2B79AD77A6FC7A94`

## Run the backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Optional environment variables:

- `NS_RUNTIME_MODE=research|staging|production`
- `ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS=true|false` (default false)
- `NS_ARTIFACT_ROOT=<deployment artifact directory>`
- `ALLOWED_ORIGINS=http://localhost:...` (comma separated)
- `MAX_UPLOAD_SIZE_BYTES=10485760`

Run backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Important scientific boundaries:

- Image-only requests do not fabricate phenotype observations. Phase 6
  transparently abstains when no structured observations are supplied.
- CNN class labels are excluded from runtime symbolic observations.
- Grad-CAM is model attention, not validated lesion segmentation.
- `infected_area_percent` and `lesion_mask_base64` are deprecated compatibility
  aliases for attention-based heuristics.
- Held and incomplete rules retain their authoritative Phase 5 states.
- This integration does not demonstrate improved accuracy. Comparative Phase 9
  evaluation is still required before any performance claim.

## Runtime security and reproducibility

`NS_RUNTIME_MODE` is a server-authoritative ceiling. Requests may choose the
same or a more restrictive mode, but cannot escalate from production to staging
or research, or from staging to research. `/health` and `/v2/system-info` report
the configured server mode.

Guided categorical strings are validated against the hashed, provenance-backed
Observation Vocabulary v1. Canonical values and only explicitly sourced aliases
are accepted. Fields without a finite vocabulary remain user-confirmed free
text: research accepts them with a warning, while staging and production require
`ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS=true`. See
`docs/OBSERVATION_VOCABULARY_V1.md`.

When symbolic reasoning abstains, the unchanged Phase 7 result is retained for
audit, while effective runtime weights are CNN `1.0` and symbolic `0.0`. If
safety policy withholds diagnosis, `fusion_result.final_prediction` is null and
the non-authoritative class remains under `candidate_prediction`.

The old `neuro_symbolic.rule_engine` is a deprecated safety-only adapter. It no
longer returns phenotype facts, legacy knowledge matches, or an independent
symbolic diagnosis.

The verified environment is CPython 3.13.2 with TensorFlow 2.21.0. Exact primary
package versions are recorded in `requirements-lock.txt`.

Flutter v2 integration and validation are intentionally deferred. See
`docs/DEFERRED_FLUTTER_WORK.md`.
