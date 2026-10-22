# Artifact Traceability

The runtime package is `research_artifacts/runtime_v1/`. Startup validation
checks file existence, SHA-256, JSON object structure, Phase 5 schema compliance,
runtime-state values, runtime mode, class mapping, model existence, and the
five-output model contract. Paths are project-relative; `NS_ARTIFACT_ROOT` may
override the deployment directory.

| Logical artifact | Version | SHA-256 |
|---|---:|---|
| Phase 5 evidence-aware rules | 1.0.0 | `9BDCD3FB73A2A4EC7F07C77133B2E88282ACDDBF4F08C9B8D10326158E985B06` |
| Phase 5 rule schema | 1.0.0 | `50FA2AF19EEDE6D92BA4D3ECB8DFBB6A9AC1966643752E7B64B47E86F4B92900` |
| Phase 6 reasoning config | 1.0.0 | `CD66857F7D595572D568C88D654C8B422389FA8751FDFDBBD2F2754307BA67D5` |
| Phase 6 observation template | 1.0.0 | `27ADA40C9BC015B854094720FF2228EECD342C6A113B99962078D3BCB6E49BA3` |
| Phase 7 fusion config | 1.0.0 | `88A9ED62F3C180893C6C3BE9D880EEC348231577C0C99DE9621597BD2AD5AD51` |
| Phase 7 CNN output template | 1.0.0 | `6A9614E9B3234AB68607CE976828D4DE5BB9D46670FA81C4F0E95635902608DB` |
| Canonical class mapping | 1.0.0 | `DBBE1EDE6D0845B1C25F624AD8B71B5DF00EED5BCE9F78EDB902603756ECC502` |
| Observation vocabulary | 1.0.0 | `7AF4A3391E168B93B2E17928A1AF369377498F8174AF6F9A60E344CFEB8C548E` |
| Observation vocabulary schema | 1.0.0 | `794323D1437F1A3F2F4817203492DDFD73443594E62C0B69E4B221C2A0575DF3` |

The first six runtime files are byte-identical to their original package files.
The class mapping is integration-generated from the unchanged CNN class order
and exact research labels. Original notebooks, CSVs, and XLSX reports are not
executed or parsed at runtime.

The observation vocabulary is integration-generated from explicit values in
the Phase 5 rules, Phase 6 template, implemented `SYNONYM_MAP`, and phenotype
graph. Its manifest records the source artifacts, deterministic method, and
non-invention statement. Startup additionally validates it against its JSON
Schema, requires exact agreement with all Phase 6 field names, and rejects alias
collisions.
