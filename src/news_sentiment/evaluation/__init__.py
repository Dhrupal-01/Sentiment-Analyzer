"""Evaluation, benchmark datasets, contamination checks, and error analysis."""

from news_sentiment.evaluation.benchmarks import (
    BenchmarkItem,
    ensure_financial_phrasebank,
    load_benchmark_split,
)
from news_sentiment.evaluation.contamination import (
    ContaminationStatus,
    check_contamination,
)
from news_sentiment.evaluation.error_analysis import (
    ErrorAnalysisResult,
    MisclassifiedHeadline,
    analyze_model_errors,
    categorize_misclassification,
)
from news_sentiment.evaluation.metrics import (
    ClassMetrics,
    EvaluationReport,
    compute_bootstrap_macro_f1_ci,
    compute_classification_metrics,
    compute_confusion_matrix,
)
from news_sentiment.evaluation.runner import (
    BenchmarkRunner,
    ModelEvaluationOutput,
)

__all__ = [
    "BenchmarkItem",
    "BenchmarkRunner",
    "ClassMetrics",
    "ContaminationStatus",
    "ErrorAnalysisResult",
    "EvaluationReport",
    "MisclassifiedHeadline",
    "ModelEvaluationOutput",
    "analyze_model_errors",
    "categorize_misclassification",
    "check_contamination",
    "compute_bootstrap_macro_f1_ci",
    "compute_classification_metrics",
    "compute_confusion_matrix",
    "ensure_financial_phrasebank",
    "load_benchmark_split",
]
