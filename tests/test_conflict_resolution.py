from conflict_resolution import resolve_rule_conflicts


def make_rule(
    rule_id: str,
    *,
    region: str,
    priority: int,
    recommendation: str,
) -> dict:
    return {
        "rule_id": rule_id,
        "disease": "leaf_blast",
        "applicable_severities": ["moderate"],
        "minimum_confidence": 0.6,
        "maximum_confidence": None,
        "recommendation": recommendation,
        "warning": f"Warning from {rule_id}",
        "source_id": f"source_{rule_id}",
        "source_organization": "Test source",
        "source_title": "Test rule",
        "regional_applicability": [region],
        "validation_status": "pending_expert_validation",
        "version": "1.0.0",
        "priority": priority,
        "safety_priority": 5,
        "notes": "Test fixture",
    }


def test_conflicting_rules_prefer_bangladesh_specific_rule():
    global_rule = make_rule(
        "GLOBAL_RULE",
        region="global",
        priority=50,
        recommendation="Use global guidance.",
    )
    bangladesh_rule = make_rule(
        "BANGLADESH_RULE",
        region="Bangladesh",
        priority=50,
        recommendation="Consult Bangladesh extension guidance.",
    )
    result = resolve_rule_conflicts(
        [global_rule, bangladesh_rule],
        disease="leaf_blast",
        severity="moderate",
        confidence=0.9,
    )
    assert result["selected_rule_id"] == "BANGLADESH_RULE"
    assert result["rejected_rule_ids"] == ["GLOBAL_RULE"]
    assert result["conflicts_detected"]
    assert "regional=40" in result["resolution_explanation"]


def test_no_rules_uses_safe_fallback():
    result = resolve_rule_conflicts(
        [],
        disease="unknown",
        severity="unknown",
        confidence=0.2,
    )
    assert result["selected_rule"] is None
    assert (
        result["selected_recommendation"]
        == "Retake the image or consult a local agricultural expert."
    )
    assert result["resolution_score"] == 0.0
