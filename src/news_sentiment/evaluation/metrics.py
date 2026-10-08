import random
from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_CLASSES: list[str] = ["positive", "neutral", "negative"]


@dataclass(frozen=True)
class ClassMetrics:
    """Precision, recall, F1, and support count for a single class."""

    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True)
class EvaluationReport:
    """Comprehensive performance metrics for a model on a dataset."""

    sample_size: int
    accuracy: float
    macro_f1: float
    per_class: dict[str, ClassMetrics]
    confusion_matrix: dict[str, dict[str, int]]  # [true_label][pred_label]
    bootstrap_ci_macro_f1: tuple[float, float]  # (low_95, high_95)


def compute_confusion_matrix(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    classes: Sequence[str] | None = None,
) -> dict[str, dict[str, int]]:
    """Compute 2D confusion matrix counting [true_label][pred_label]."""
    labels = list(classes or DEFAULT_CLASSES)
    matrix: dict[str, dict[str, int]] = {t: dict.fromkeys(labels, 0) for t in labels}

    for t, p in zip(y_true, y_pred, strict=True):
        if t in matrix and p in matrix[t]:
            matrix[t][p] += 1

    return matrix


def compute_classification_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    classes: Sequence[str] | None = None,
    n_bootstrap: int = 1000,
    seed: int = 42,
    confidence_level: float = 0.95,
) -> EvaluationReport:
    """Calculate accuracy, per-class P/R/F1, macro-F1, confusion matrix, and bootstrap 95% CI.

    Args:
        y_true: Ground-truth target labels.
        y_pred: Model predicted labels.
        classes: Ordered list of classification categories.
        n_bootstrap: Number of bootstrap iterations for macro-F1 confidence interval.
        seed: Random seed for reproducible bootstrap sampling.
        confidence_level: Desired coverage probability (default 0.95).

    Returns:
        EvaluationReport instance.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"Mismatched label counts: {len(y_true)} ground-truth vs {len(y_pred)} predicted."
        )

    labels = classes or DEFAULT_CLASSES
    n = len(y_true)
    if n == 0:
        empty_classes = {c: ClassMetrics(0.0, 0.0, 0.0, 0) for c in labels}
        empty_matrix = {t: dict.fromkeys(labels, 0) for t in labels}
        return EvaluationReport(
            sample_size=0,
            accuracy=0.0,
            macro_f1=0.0,
            per_class=empty_classes,
            confusion_matrix=empty_matrix,
            bootstrap_ci_macro_f1=(0.0, 0.0),
        )

    # 1. Accuracy
    correct = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == p)
    accuracy = float(correct / n)

    # 2. Per-class metrics
    per_class: dict[str, ClassMetrics] = {}
    f1_scores: list[float] = []

    for c in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == c and p != c)
        support = sum(1 for t in y_true if t == c)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[c] = ClassMetrics(
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1=round(f1, 4),
            support=support,
        )
        f1_scores.append(f1)

    macro_f1 = float(sum(f1_scores) / len(f1_scores)) if f1_scores else 0.0

    # 3. Confusion Matrix
    matrix = compute_confusion_matrix(y_true, y_pred, labels)

    # 4. Bootstrap 95% Confidence Interval for Macro-F1
    bootstrap_ci = compute_bootstrap_macro_f1_ci(
        y_true=y_true,
        y_pred=y_pred,
        classes=labels,
        n_bootstrap=n_bootstrap,
        seed=seed,
        confidence_level=confidence_level,
    )

    return EvaluationReport(
        sample_size=n,
        accuracy=round(accuracy, 4),
        macro_f1=round(macro_f1, 4),
        per_class=per_class,
        confusion_matrix=matrix,
        bootstrap_ci_macro_f1=bootstrap_ci,
    )


def compute_bootstrap_macro_f1_ci(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    classes: Sequence[str],
    n_bootstrap: int = 1000,
    seed: int = 42,
    confidence_level: float = 0.95,
) -> tuple[float, float]:
    """Compute empirical percentile bootstrap confidence interval for Macro-F1."""
    n = len(y_true)
    if n == 0 or n_bootstrap <= 0:
        return (0.0, 0.0)

    rng = random.Random(seed)
    macro_f1_samples: list[float] = []

    pairs = list(zip(y_true, y_pred, strict=True))

    for _ in range(n_bootstrap):
        # Sample with replacement
        resampled = rng.choices(pairs, k=n)

        # Compute Macro-F1 on resampled set
        f1s: list[float] = []
        for c in classes:
            tp = sum(1 for t, p in resampled if t == c and p == c)
            fp = sum(1 for t, p in resampled if t != c and p == c)
            fn = sum(1 for t, p in resampled if t == c and p != c)
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
            f1s.append(f1)

        macro_f1_samples.append(sum(f1s) / len(f1s) if f1s else 0.0)

    macro_f1_samples.sort()
    alpha = (1.0 - confidence_level) / 2.0
    low_idx = int(alpha * n_bootstrap)
    high_idx = int((1.0 - alpha) * n_bootstrap) - 1
    high_idx = max(0, min(high_idx, n_bootstrap - 1))

    low_val = round(macro_f1_samples[low_idx], 4)
    high_val = round(macro_f1_samples[high_idx], 4)
    return (low_val, high_val)
