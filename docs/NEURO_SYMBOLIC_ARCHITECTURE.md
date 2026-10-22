# Neuro-Symbolic Backend Architecture

## Runtime flow

```text
image
  -> unchanged CNN inference (224 x 224 RGB, EfficientNet preprocessing)
  -> unchanged Grad-CAM gradients and visualizations
  -> structured observation preparation
  -> Phase 6 evidence-aware reasoning
  -> Phase 7 adaptive reliability-weighted fusion
  -> diagnostic conflict semantics
  -> separate management actionability resolution
  -> constrained explanation
  -> FastAPI v2 + legacy response
```

`predictor.py` owns the unchanged model/image/Grad-CAM operations and delegates
all decision logic to `neuro_symbolic/orchestrator.py`. Artifacts are loaded once
through cached functions and verified against the runtime manifest.

The historical `neuro_symbolic/rule_engine.py` interface is retained only as a
deprecated safety adapter. It ignores class-derived phenotype and legacy rule
arguments, emits `DeprecationWarning`, and can return only deterministic system
safeguards. `knowledge_base/` and `knowledge_graph/` remain historical
compatibility modules and are not part of active diagnosis.

## Scientific separation

- Safety rules are deterministic application policy. They may force uncertainty
  or retake guidance but never contribute phenotype evidence.
- Diagnostic conflict resolution interprets CNN-symbolic agreement and Phase 7
  outputs.
- Management resolution happens only after diagnosis and cannot change disease
  class or fusion scores.
- `knowledge_graph/` and `knowledge_base/` are retained for compatibility but
  are not used by the active orchestrated predictor. Their class-driven phenotype
  descriptions are never presented as observed image evidence.

## Runtime modes

- `production`: `ACTIVE_CANDIDATE` only.
- `staging`: active and `STAGING_CANDIDATE`.
- `research`: active, staging, and `EVIDENCE_SUPPORTED_HOLD`.
- `HOLD_PARSE_INCOMPLETE` never executes.

Research-mode execution does not change a record's state or make it actionable.

`NS_RUNTIME_MODE` defines the maximum server-permitted mode using production <
staging < research. A request may reduce privilege but cannot increase it.

## Raw Phase 7 versus effective runtime fusion

The Phase 7 core remains byte-for-formula compatible with its notebook,
including the minimum 0.1 modality bound. Orchestration applies a separate
abstention policy: insufficient symbolic observation evidence produces effective
weights CNN 1.0 and symbolic 0.0 and uses normalized CNN probabilities as
effective scores. Raw Phase 7 weights and scores remain in the response for
audit. Completed symbolic results use the raw Phase 7 weights unchanged.

Diagnostic resolution then distinguishes an authoritative final prediction from
the fusion candidate. Safety-forced uncertainty publishes no final class,
retains the candidate separately, and requires manual review.
