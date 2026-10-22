"""Structured phenotype knowledge retrieval for supported rice-leaf classes."""

from .graph_query import (
    get_confusion_classes,
    get_phenotype_facts,
    get_phenotype_knowledge,
)

__all__ = [
    "get_confusion_classes",
    "get_phenotype_facts",
    "get_phenotype_knowledge",
]
