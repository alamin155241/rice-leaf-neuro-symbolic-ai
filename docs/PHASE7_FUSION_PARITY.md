# Phase 7 Fusion Parity

`neuro_symbolic/fusion_engine.py` implements the Phase 7 notebook functions
without coefficient or threshold changes.

CNN reliability:

```text
0.5 * top_probability + 0.3 * margin + 0.2 * (1 - normalized_entropy)
```

Symbolic reliability:

```text
0.5 * symbolic_score + 0.3 * score_margin + 0.2 * min(1, matched_rules / 4)
```

Insufficient symbolic evidence forces symbolic reliability to zero.
`LOW_OR_CONFLICTED` reliability is multiplied by `0.70`. Adaptive weights are
normalized from reliability and bounded to `[0.10, 0.90]`. Uncertainty thresholds
remain final confidence `0.45` and final margin `0.08`.

Golden tests reproduce all five `fusion_results_v1.json` cases and all three
`conflict_stress_test_results_v1.json` cases, including reliability values,
adaptive weights, fused scores, decisions, conflict detection, and resolution.
No fixed 50/50 fusion is used.

The exact core remains unchanged. Runtime image-only abstention is handled after
the core returns: effective weights become CNN `1.0` and symbolic `0.0`, and
effective scores are normalized CNN probabilities. Responses retain raw Phase 7
weights and scores and set `abstention_policy_applied=true`. For completed
symbolic results, effective and raw weights are identical.

Golden fixtures are vendored byte-for-byte under `tests/golden_data/phase7` and
validated through `GOLDEN_DATA_MANIFEST.json`, removing the test dependency on
the excluded integration source package.
