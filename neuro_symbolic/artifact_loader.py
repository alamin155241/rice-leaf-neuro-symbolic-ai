"""Cached loading and integrity validation for versioned research artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARTIFACT_ROOT = PROJECT_ROOT / "research_artifacts" / "runtime_v1"
SUPPORTED_RUNTIME_MODES = {"research", "staging", "production"}
RUNTIME_MODE_RESTRICTIVENESS = {
    "production": 0,
    "staging": 1,
    "research": 2,
}
REQUIRED_RUNTIME_STATES = {
    "ACTIVE_CANDIDATE",
    "STAGING_CANDIDATE",
    "EVIDENCE_SUPPORTED_HOLD",
    "HOLD_PARSE_INCOMPLETE",
}


def artifact_root() -> Path:
    configured = os.getenv("NS_ARTIFACT_ROOT")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_ARTIFACT_ROOT


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    path = artifact_root() / "artifact_manifest_v1.json"
    if not path.is_file():
        raise RuntimeError("Research artifact manifest is missing.")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document.get("artifacts"), list):
        raise RuntimeError("Research artifact manifest has no artifacts list.")
    return document


def _manifest_record(logical_name: str) -> dict[str, Any]:
    for record in load_manifest()["artifacts"]:
        if record.get("logical_name") == logical_name:
            return record
    raise RuntimeError(f"Artifact is absent from manifest: {logical_name}")


@lru_cache(maxsize=None)
def load_json_artifact(logical_name: str) -> dict[str, Any]:
    record = _manifest_record(logical_name)
    path = artifact_root() / Path(record["runtime_relative_path"]).name
    if not path.is_file():
        raise RuntimeError(f"Required research artifact is missing: {logical_name}")
    actual_hash = sha256_file(path)
    if actual_hash != str(record["sha256"]).upper():
        raise RuntimeError(f"Research artifact hash mismatch: {logical_name}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError(f"Research artifact must contain an object: {logical_name}")
    return document


@lru_cache(maxsize=1)
def load_rules() -> tuple[dict[str, Any], ...]:
    rule_base = load_json_artifact("phase5_evidence_aware_rules")
    schema = load_json_artifact("phase5_rule_schema")
    rules = rule_base.get("rules")
    if not isinstance(rules, list):
        raise RuntimeError("Phase 5 rule artifact has no rules list.")
    compiled_rule_base = load_json_artifact("compiled_diagnostic_rules")
    compiled_rules = compiled_rule_base.get("rules")
    if not isinstance(compiled_rules, list):
        raise RuntimeError("Compiled diagnostic artifact has no rules list.")
    all_rules = [*rules, *compiled_rules]
    base_rule_ids = {str(rule.get("rule_id", "")) for rule in rules}
    compiled_rule_ids = [
        str(rule.get("rule_id", "")) for rule in compiled_rules
    ]
    if len(compiled_rule_ids) != len(set(compiled_rule_ids)) or (
        base_rule_ids & set(compiled_rule_ids)
    ):
        raise RuntimeError("Compiled diagnostic rule identifiers must be unique.")
    validator = Draft202012Validator(schema)
    for index, rule in enumerate(all_rules):
        errors = list(validator.iter_errors(rule))
        if errors:
            raise RuntimeError(
                f"Phase 5 rule {index} does not match rule_schema_v1.json: "
                f"{errors[0].message}"
            )
        state = rule.get("runtime_state")
        if state not in REQUIRED_RUNTIME_STATES:
            raise RuntimeError(f"Unsupported Phase 5 runtime state: {state}")
    return tuple(all_rules)


class RuntimeModeEscalationError(ValueError):
    """Raised when a request tries to exceed the server's configured mode."""


def _validate_runtime_mode(value: str, *, source: str) -> str:
    mode = value.strip().lower()
    if mode not in SUPPORTED_RUNTIME_MODES:
        raise ValueError(
            f"Invalid {source} runtime mode. Expected research, staging, or production."
        )
    return mode


def get_server_runtime_mode() -> str:
    """Return the server-authoritative maximum mode from NS_RUNTIME_MODE."""
    return _validate_runtime_mode(
        os.getenv("NS_RUNTIME_MODE", "research"), source="server"
    )


def get_runtime_mode(requested: str | None = None) -> str:
    """Resolve a request without permitting escalation above server policy."""
    server_mode = get_server_runtime_mode()
    if requested is None or not requested.strip():
        return server_mode
    request_mode = _validate_runtime_mode(requested, source="requested")
    if (
        RUNTIME_MODE_RESTRICTIVENESS[request_mode]
        > RUNTIME_MODE_RESTRICTIVENESS[server_mode]
    ):
        raise RuntimeModeEscalationError(
            "Requested runtime mode exceeds the server's permitted mode."
        )
    return request_mode


def validate_runtime_artifacts() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for record in load_manifest()["artifacts"]:
        logical_name = record["logical_name"]
        load_json_artifact(logical_name)
        hashes[logical_name] = str(record["sha256"]).upper()
    load_rules()
    return hashes


def artifact_info() -> dict[str, dict[str, str]]:
    return {
        record["logical_name"]: {
            "version": str(record.get("version", "")),
            "sha256": str(record["sha256"]).upper(),
            "role": str(record.get("role", "")),
        }
        for record in load_manifest()["artifacts"]
    }
