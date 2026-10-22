"""Validated mapping between CNN keys and authoritative research labels."""

from __future__ import annotations

from functools import lru_cache

from .artifact_loader import load_json_artifact


CNN_CLASS_ORDER = [
    "brown_spot",
    "healthy",
    "leaf_blast",
    "leaf_scald",
    "narrow_brown_spot",
]


@lru_cache(maxsize=1)
def _mapping() -> dict:
    document = load_json_artifact("canonical_class_mapping")
    if document.get("cnn_class_order") != CNN_CLASS_ORDER:
        raise RuntimeError("Runtime class mapping does not match CNN class order.")
    records = document.get("classes", [])
    if len(records) != len(CNN_CLASS_ORDER):
        raise RuntimeError("Runtime class mapping must contain exactly five classes.")
    return document


def validate_class_mapping(model_output_count: int | None = None) -> None:
    _mapping()
    if model_output_count is not None and model_output_count != len(CNN_CLASS_ORDER):
        raise RuntimeError(
            f"Model output count is {model_output_count}; expected five classes."
        )


def to_research_label(label: str) -> str:
    normalized = label.strip()
    for record in _mapping()["classes"]:
        if normalized in {
            record["canonical_key"],
            record["research_label"],
            record["display_name"],
        }:
            return record["research_label"]
    raise ValueError(f"Unknown rice-leaf class label: {label}")


def to_canonical_key(label: str) -> str:
    normalized = label.strip()
    for record in _mapping()["classes"]:
        if normalized in {
            record["canonical_key"],
            record["research_label"],
            record["display_name"],
        }:
            return record["canonical_key"]
    raise ValueError(f"Unknown rice-leaf class label: {label}")


def display_name(label: str) -> str:
    canonical = to_canonical_key(label)
    return next(
        record["display_name"]
        for record in _mapping()["classes"]
        if record["canonical_key"] == canonical
    )


def canonical_probabilities_to_research(
    probabilities: dict[str, float],
) -> dict[str, float]:
    return {
        to_research_label(key): float(value) for key, value in probabilities.items()
    }


def research_probabilities_to_canonical(
    probabilities: dict[str, float],
) -> dict[str, float]:
    return {
        to_canonical_key(key): float(value) for key, value in probabilities.items()
    }
