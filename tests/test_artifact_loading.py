import hashlib
import json
from pathlib import Path

from neuro_symbolic.artifact_loader import (
    artifact_info,
    load_rules,
    validate_runtime_artifacts,
)


GOLDEN_ROOT = Path(__file__).resolve().parent / "golden_data"


def test_runtime_artifacts_validate_and_rules_preserve_states():
    hashes = validate_runtime_artifacts()
    assert len(hashes) == 10
    rules = load_rules()
    assert len(rules) == 63
    assert {rule["runtime_state"] for rule in rules} == {
        "ACTIVE_CANDIDATE",
        "STAGING_CANDIDATE",
        "EVIDENCE_SUPPORTED_HOLD",
        "HOLD_PARSE_INCOMPLETE",
    }
    assert artifact_info()["phase5_evidence_aware_rules"]["version"] == "1.0.0"


def test_self_contained_golden_data_matches_manifest():
    manifest = json.loads(
        (GOLDEN_ROOT / "GOLDEN_DATA_MANIFEST.json").read_text(encoding="utf-8")
    )
    for record in manifest["files"]:
        path = GOLDEN_ROOT / record["relative_path"]
        assert path.stat().st_size == record["size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == record[
            "sha256"
        ]
