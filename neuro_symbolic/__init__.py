"""Authoritative public interfaces for neuro-symbolic diagnosis."""

from typing import Any

from .rule_engine import evaluate_prediction_rules as deprecated_evaluate_prediction_rules


def orchestrate_diagnosis(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Lazily dispatch to the authoritative orchestration pipeline."""
    from .orchestrator import orchestrate_diagnosis as implementation

    return implementation(*args, **kwargs)


def reasoning_engine(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Lazily dispatch to the exact Phase 6 implementation."""
    from .reasoning_engine import reasoning_engine as implementation

    return implementation(*args, **kwargs)


def fuse_predictions(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Lazily dispatch to the exact Phase 7 implementation."""
    from .fusion_engine import fuse_predictions as implementation

    return implementation(*args, **kwargs)

# Import compatibility for older callers. It is intentionally excluded from
# __all__ so it cannot be mistaken for the authoritative reasoning interface.
evaluate_prediction_rules = deprecated_evaluate_prediction_rules

__all__ = [
    "orchestrate_diagnosis",
    "reasoning_engine",
    "fuse_predictions",
    "deprecated_evaluate_prediction_rules",
]
