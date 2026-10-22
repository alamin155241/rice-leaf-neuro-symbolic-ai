"""Typed access to management rules that are pending expert validation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict


class KnowledgeRule(TypedDict):
    rule_id: str
    disease: str
    applicable_severities: list[str]
    minimum_confidence: float
    maximum_confidence: float | None
    recommendation: str
    warning: str
    source_id: str
    source_organization: str
    source_title: str
    regional_applicability: list[str]
    validation_status: str
    version: str
    priority: int
    safety_priority: int
    notes: str


KNOWLEDGE_PATH = Path(__file__).with_name("validated_knowledge.json")


@lru_cache(maxsize=1)
def _load_rules() -> tuple[KnowledgeRule, ...]:
    with KNOWLEDGE_PATH.open("r", encoding="utf-8") as knowledge_file:
        document = json.load(knowledge_file)
    rules = document.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError("Knowledge base must contain a 'rules' list.")
    return tuple(rules)


def _copy_rule(rule: KnowledgeRule) -> KnowledgeRule:
    copied: dict[str, Any] = dict(rule)
    copied["applicable_severities"] = list(rule["applicable_severities"])
    copied["regional_applicability"] = list(rule["regional_applicability"])
    return copied  # type: ignore[return-value]


def get_rules_for_disease(disease: str) -> list[KnowledgeRule]:
    """Return disease-specific rules plus general safety rules."""
    normalized = disease.strip().lower()
    return [
        _copy_rule(rule)
        for rule in _load_rules()
        if rule["disease"] in {normalized, "*"}
    ]


def get_applicable_rules(
    disease: str, severity: str, confidence: float
) -> list[KnowledgeRule]:
    """Filter rules by class, severity, and inclusive confidence bounds."""
    normalized_severity = severity.strip().lower()
    applicable: list[KnowledgeRule] = []
    for rule in get_rules_for_disease(disease):
        severities = rule["applicable_severities"]
        if normalized_severity not in severities and "*" not in severities:
            continue
        if confidence < float(rule["minimum_confidence"]):
            continue
        maximum = rule.get("maximum_confidence")
        if maximum is not None and confidence > float(maximum):
            continue
        applicable.append(rule)
    return applicable


def get_source_summaries(rule_ids: list[str]) -> list[str]:
    """Return de-duplicated source summaries for the requested rule IDs."""
    requested = set(rule_ids)
    summaries: list[str] = []
    seen_sources: set[str] = set()
    for rule in _load_rules():
        if rule["rule_id"] not in requested:
            continue
        source_id = rule["source_id"]
        if source_id in seen_sources:
            continue
        seen_sources.add(source_id)
        summaries.append(
            f"{source_id} — {rule['source_organization']}: "
            f"{rule['source_title']} "
            f"[{rule['validation_status']}, version {rule['version']}]"
        )
    return summaries
