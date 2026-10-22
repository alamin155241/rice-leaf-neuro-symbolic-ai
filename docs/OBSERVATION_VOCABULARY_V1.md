# Observation Vocabulary v1

`observation_vocabulary_v1.json` is the runtime contract for the 21 fields in
the Phase 6 observation template. It was produced conservatively from explicit
Phase 5 rule conditions, the Phase 6 field template, aliases already implemented
in `SYNONYM_MAP`, and explicit values in the existing phenotype graph. No
internet material, CNN labels, inferred botanical categories, guessed aliases,
or new scientific citations were used.

## Extraction and canonicalization

Source text is retained with each categorical value. Canonical keys use
lowercase snake case: surrounding whitespace is trimmed, spaces and hyphens are
replaced with underscores, and repeated underscores are collapsed. At request
time, the backend accepts a canonical key, an original source surface form, or
an explicitly listed alias. Comparison is case-insensitive and trims surrounding
whitespace; it does not create additional space/hyphen synonyms.

Similar concepts remain separate unless existing Phase 6 normalization or a
source record explicitly establishes equivalence. In particular,
`spindle_shaped`, `diamond_shaped`, and `oval` are separate; `brown` and
`light_brown` are separate. An unsupported description such as `ellipse-like`
is not guessed into a category.

## Coverage

Authoritative categorical strings are available for 12 fields:

- `lesion_shape`, `lesion_color`, `lesion_center_color`
- `lesion_margin_color`, `lesion_size`, `leaf_region`, `halo_color`
- `yellowing`, `visual_status`, `vigor`, `leaf_age`, `growth_stage`

Nine fields deliberately have no categorical string enum:

- Schema booleans: `lesion_present`, `halo_present`, `zonation_present`,
  `coalescence`
- Schema number: `lesion_width_mm` (no invented range)
- Unvalidated string/array fields: `lesion_distribution`, `other_observations`
- Mixed boolean/free-text fields: `blighting`, `dryness`

`yellowing` is also mixed-type: its boolean support is schema-defined, while
the string `yellowing` has evidence provenance. Boolean `true` and `false` are
not presented as scientific disease categories.

## Provenance and validation

Every categorical entry records original values, source text, source artifact,
source ID, and any available rule IDs, evidence IDs, record IDs, and citation.
Alias records identify their implemented or source-surface origin. The JSON
Schema and startup checks verify structure, exact Phase 6 field coverage, and
per-field alias collision safety.

Unsupported values on a categorical field return HTTP 422 with the field and a
safe canonical-value list. A field without a vocabulary accepts non-empty free
text in research mode with `enum_validated=false`. Staging and production block
that free text unless the server sets
`ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS=true`. Evidence-backed categorical values
do not require that override.

These terms are distinct:

- Provided observation: the value submitted by the user.
- Normalized observation: the accepted canonical value passed to Phase 6.
- Enum-validated observation: a value accepted by the closed, provenance-backed
  vocabulary.
- Rule-matched observation: an observation used by a Phase 6 condition in a rule
  that actually fired.

Vocabulary membership alone never marks a rule as matched and makes no claim of
improved diagnostic accuracy.
