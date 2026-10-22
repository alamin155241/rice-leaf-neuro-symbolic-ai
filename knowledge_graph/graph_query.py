"""Typed, read-only access to the JSON phenotype knowledge graph.

This module retrieves structured facts. It intentionally does not decide a
diagnosis, severity, recommendation, or treatment.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TypedDict


class PhenotypeKnowledge(TypedDict):
    display_name: str
    symptoms: list[str]
    lesion_patterns: list[str]
    affected_plant_parts: list[str]
    favourable_conditions: list[str]
    possible_confusion_classes: list[str]
    prevention_facts: list[str]
    management_facts: list[str]
    evidence_source_ids: list[str]


GRAPH_PATH = Path(__file__).with_name("phenotype_graph.json")


@lru_cache(maxsize=1)
def _load_graph() -> dict[str, PhenotypeKnowledge]:
    with GRAPH_PATH.open("r", encoding="utf-8") as graph_file:
        document = json.load(graph_file)
    diseases = document.get("diseases", {})
    if not isinstance(diseases, dict):
        raise ValueError("Phenotype graph must contain a 'diseases' object.")
    return diseases


def get_phenotype_knowledge(disease: str) -> PhenotypeKnowledge | None:
    """Return structured knowledge for a disease, or ``None`` when unknown."""
    normalized = disease.strip().lower()
    knowledge = _load_graph().get(normalized)
    if knowledge is None:
        return None

    # Return fresh list values so callers cannot mutate the cached graph.
    return {
        key: list(value) if isinstance(value, list) else value
        for key, value in knowledge.items()
    }  # type: ignore[return-value]


def get_confusion_classes(disease: str) -> list[str]:
    """Return class identifiers that may be visually confused with ``disease``."""
    knowledge = get_phenotype_knowledge(disease)
    if knowledge is None:
        return []
    return list(knowledge["possible_confusion_classes"])


def get_phenotype_facts(disease: str) -> list[str]:
    """Flatten key graph relationships into human-readable evidence facts."""
    knowledge = get_phenotype_knowledge(disease)
    if knowledge is None:
        return []

    facts: list[str] = []
    category_labels = (
        ("symptoms", "Symptom"),
        ("lesion_patterns", "Lesion pattern"),
        ("affected_plant_parts", "Affected part"),
        ("favourable_conditions", "Favourable condition"),
    )
    for field, label in category_labels:
        facts.extend(f"{label}: {value}" for value in knowledge[field])
    return facts
