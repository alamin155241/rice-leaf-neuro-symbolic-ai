import pytest

from neuro_symbolic import deprecated_evaluate_prediction_rules


LEGACY_RULE = {
    "rule_id": "KB_LEAF_BLAST_MILD_001",
    "disease": "leaf_blast",
    "recommendation": "Legacy recommendation must not be matched.",
}
CLASS_DERIVED_PHENOTYPE = {
    "display_name": "Leaf Blast",
    "symptoms": ["spindle-shaped lesions"],
}


def evaluate(top_confidence=0.95, second_confidence=0.02, attention=4.0):
    with pytest.warns(DeprecationWarning):
        return deprecated_evaluate_prediction_rules(
            top_label="leaf_blast",
            top_confidence=top_confidence,
            second_label="brown_spot",
            second_confidence=second_confidence,
            severity="mild",
            attention_coverage_percent=attention,
            phenotype_knowledge=CLASS_DERIVED_PHENOTYPE,
            applicable_knowledge_rules=[LEGACY_RULE],
        )


def test_deprecated_adapter_never_returns_class_derived_phenotype():
    result = evaluate()
    assert result["phenotype_facts"] == []
    assert result["knowledge_sources"] == []
    assert result["symbolic_diagnosis_performed"] is False


def test_deprecated_adapter_never_marks_legacy_rule_as_matched():
    result = evaluate()
    assert all(rule["rule_id"] != LEGACY_RULE["rule_id"] for rule in result["matched_rules"])
    assert result["matched_rules"] == []


def test_deprecated_adapter_preserves_low_confidence_safety():
    result = evaluate(top_confidence=0.55, second_confidence=0.20)
    assert result["final_decision"] == "uncertain"
    assert result["trust_level"] == "low"
    assert [rule["rule_id"] for rule in result["matched_rules"]] == [
        "SYS_LOW_CONFIDENCE"
    ]


def test_deprecated_adapter_preserves_ambiguity_safety():
    result = evaluate(top_confidence=0.66, second_confidence=0.61)
    assert result["final_decision"] == "possible_leaf_blast_or_brown_spot"
    assert result["ambiguity_detected"] is True
    assert [rule["rule_id"] for rule in result["matched_rules"]] == [
        "SYS_TOP_TWO_AMBIGUITY"
    ]
