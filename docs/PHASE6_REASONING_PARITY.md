# Phase 6 Reasoning Parity

`neuro_symbolic/reasoning_engine.py` is a direct module refactor of the Phase 6B
notebook functions: normalization, observation flattening, token matching, rule
completeness and mode gating, relevance gating, phrase scoring, diagnostic
conclusion handling, contribution calculation, disease normalization, confidence
category, and trace construction.

Golden tests use the five stored Phase 6 cases and a numeric tolerance of
`1e-4`. They verify symbolic prediction, score, disease scores, matched rule
order, contribution, condition and conclusion matches, evidence mode, source
document ID, and master record ID against both
`reasoning_test_results_v1.json` and `reasoning_trace_v1.csv`.

## Anti-circularity correction

The notebook's `flatten_observations` appends the CNN predicted class. That would
make CNN output appear as independent symbolic evidence. Runtime operation
therefore excludes the CNN class. A narrowly named
`include_cnn_label_for_parity=True` option exists only in golden tests to
reproduce the published notebook fixtures.

Image-only runtime requests contain no fabricated phenotype observations and
return:

```json
{
  "status": "insufficient_observation_evidence",
  "matched_rule_count": 0,
  "reliability": 0.0
}
```

Guided observations can drive matching and each supplied field is marked
`user_confirmed`.

Golden fixtures are now vendored byte-for-byte under `tests/golden_data/phase6`
and hashed in `tests/golden_data/GOLDEN_DATA_MANIFEST.json`. Tests no longer
depend on the larger integration source package, so they remain runnable in the
model-free backend audit package.

The historical `rule_engine.py` no longer provides a second reasoning pipeline.
Its deprecated compatibility function returns safety-only legacy structure,
empty phenotype/source fields, and no legacy knowledge-rule matches.
