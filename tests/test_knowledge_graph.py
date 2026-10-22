from knowledge_graph import (
    get_confusion_classes,
    get_phenotype_facts,
    get_phenotype_knowledge,
)


EXPECTED_CLASSES = {
    "brown_spot",
    "healthy",
    "leaf_blast",
    "leaf_scald",
    "narrow_brown_spot",
}


def test_graph_contains_exact_supported_classes():
    retrieved = {
        disease
        for disease in EXPECTED_CLASSES
        if get_phenotype_knowledge(disease) is not None
    }
    assert retrieved == EXPECTED_CLASSES


def test_graph_returns_structured_facts_and_confusions():
    knowledge = get_phenotype_knowledge("brown_spot")
    assert knowledge is not None
    assert knowledge["display_name"] == "Brown Spot"
    assert knowledge["symptoms"]
    assert "leaf_blast" in get_confusion_classes("brown_spot")
    assert any(
        fact.startswith("Lesion pattern:")
        for fact in get_phenotype_facts("brown_spot")
    )


def test_missing_disease_knowledge_is_safe():
    assert get_phenotype_knowledge("not_a_supported_disease") is None
    assert get_confusion_classes("not_a_supported_disease") == []
    assert get_phenotype_facts("not_a_supported_disease") == []
