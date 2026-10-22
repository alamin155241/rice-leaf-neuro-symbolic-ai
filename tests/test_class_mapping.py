import pytest

from neuro_symbolic.class_mapping import (
    CNN_CLASS_ORDER,
    to_canonical_key,
    to_research_label,
    validate_class_mapping,
)


def test_exact_five_class_mapping():
    validate_class_mapping(5)
    assert CNN_CLASS_ORDER == [
        "brown_spot",
        "healthy",
        "leaf_blast",
        "leaf_scald",
        "narrow_brown_spot",
    ]
    assert to_research_label("narrow_brown_spot") == "Narrow Brown Leaf Spot"
    assert to_canonical_key("Healthy Rice Leaf") == "healthy"


def test_unknown_class_is_rejected():
    with pytest.raises(ValueError):
        to_research_label("invented_class")
