"""Benchmark contamination registry and data leakage detection."""

from dataclasses import dataclass

FINBERT_FPB_REASON = (
    "FinBERT (ProsusAI/finbert) was fine-tuned directly on the Financial PhraseBank dataset. "
    "Evaluating FinBERT on Financial PhraseBank constitutes evaluating on in-domain training "
    "data (data leakage). It must be excluded from fair out-of-domain comparisons on this "
    "benchmark."
)

KNOWN_CONTAMINATIONS: dict[str, dict[str, str]] = {
    "finbert": {"financial_phrasebank": FINBERT_FPB_REASON},
    "ProsusAI/finbert": {"financial_phrasebank": FINBERT_FPB_REASON},
}


@dataclass(frozen=True)
class ContaminationStatus:
    """Contamination status for a model evaluated on a benchmark."""

    model_name: str
    benchmark_name: str
    is_contaminated: bool
    reason: str | None


def check_contamination(model_name: str, benchmark_name: str) -> ContaminationStatus:
    """Check whether a model was pre-trained or fine-tuned on the given benchmark.

    Args:
        model_name: Identifier of the sentiment model.
        benchmark_name: Canonical identifier of the benchmark dataset.

    Returns:
        ContaminationStatus indicating whether the model is contaminated on this benchmark.
    """
    clean_model = model_name.strip().lower()
    clean_bench = benchmark_name.strip().lower()

    for m_key, bench_map in KNOWN_CONTAMINATIONS.items():
        if m_key.lower() == clean_model:
            for b_key, reason in bench_map.items():
                if b_key.lower() == clean_bench:
                    return ContaminationStatus(
                        model_name=model_name,
                        benchmark_name=benchmark_name,
                        is_contaminated=True,
                        reason=reason,
                    )

    return ContaminationStatus(
        model_name=model_name,
        benchmark_name=benchmark_name,
        is_contaminated=False,
        reason=None,
    )
