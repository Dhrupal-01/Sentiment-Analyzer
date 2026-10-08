"""Statistical metrics for inter-model agreement and Cohen's kappa calculations."""

from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DisagreementItem:
    """A headline where two or more models assigned different sentiment labels."""

    title: str
    predictions: dict[str, dict[str, Any]]  # {model_name: {"label": ..., "score": ...}}


@dataclass(frozen=True)
class PairwiseMetric:
    """Pairwise agreement metrics between two models."""

    model_a: str
    model_b: str
    sample_size: int
    agreement_rate: float
    cohen_kappa: float


def compute_agreement_rate(labels_a: list[str], labels_b: list[str]) -> float:
    """Compute raw percentage agreement between two sequences of labels."""
    if not labels_a or not labels_b or len(labels_a) != len(labels_b):
        return 0.0

    agreed = sum(1 for a, b in zip(labels_a, labels_b, strict=True) if a == b)
    return float(agreed / len(labels_a))


def compute_cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Calculate Cohen's kappa coefficient (κ) for inter-model categorical agreement.

    Formula:
        κ = (p_o - p_e) / (1 - p_e)
    where:
        p_o = observed agreement proportion
        p_e = hypothetical chance agreement proportion
    """
    n = len(labels_a)
    if n == 0 or len(labels_b) != n:
        return 0.0

    # Observed agreement
    p_o = sum(1 for a, b in zip(labels_a, labels_b, strict=True) if a == b) / n

    # Marginal category distributions
    count_a = Counter(labels_a)
    count_b = Counter(labels_b)
    all_categories = set(count_a.keys()).union(set(count_b.keys()))

    # Expected agreement by chance
    p_e = sum((count_a[c] / n) * (count_b[c] / n) for c in all_categories)

    if p_e >= 1.0:
        return 1.0

    kappa = (p_o - p_e) / (1.0 - p_e)
    return float(kappa)


def compare_model_predictions(
    model_labels: dict[str, list[str]],
) -> list[PairwiseMetric]:
    """Calculate pairwise agreement and Cohen's kappa across multiple models.

    Args:
        model_labels: Dictionary mapping model_name -> list of string labels
                      (must all have identical length and indexing).

    Returns:
        List of PairwiseMetric results for each unique pair.
    """
    model_names = list(model_labels.keys())
    results: list[PairwiseMetric] = []

    for i in range(len(model_names)):
        for j in range(i + 1, len(model_names)):
            m_a = model_names[i]
            m_b = model_names[j]
            list_a = model_labels[m_a]
            list_b = model_labels[m_b]

            agree = compute_agreement_rate(list_a, list_b)
            kappa = compute_cohen_kappa(list_a, list_b)

            results.append(
                PairwiseMetric(
                    model_a=m_a,
                    model_b=m_b,
                    sample_size=len(list_a),
                    agreement_rate=agree,
                    cohen_kappa=kappa,
                )
            )

    return results
