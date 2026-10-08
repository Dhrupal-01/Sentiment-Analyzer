import re
from collections.abc import Sequence
from dataclasses import dataclass

TAXONOMY_CATEGORIES = [
    "negation",
    "domain_terms",
    "sarcasm",
    "mixed_sentiment",
    "neutral_reporting_of_negative_events",
    "other",
]

# Regular expressions for taxonomy categorization
PAT_NEGATION = re.compile(
    r"\b(not|n't|never|no|hardly|scarcely|barely|fail(ed|s|ing)?|"
    r"deny|denies|denied|without|lack(ing|s)?|despite|prevent(ed|s|ing)?)\b",
    re.IGNORECASE,
)

PAT_DOMAIN_TERMS = re.compile(
    r"\b(recall(s|ed|ing)?|cut(s|ting)?|strike(s|ing)?|yield(s)?|"
    r"slashe(s|d)?|restructur(e|ing|ed)|layoff(s)?|debt|rate hike|hikes|"
    r"short(ing|ed)?|bailout|default(ed|s)?|shares|securities)\b",
    re.IGNORECASE,
)

PAT_SARCASM = re.compile(
    r"(\"[A-Za-z\s-]+\"|'[A-Za-z\s-]+'|\b(so-called|alleged(ly)?|supposed(ly)?)\b)",
    re.IGNORECASE,
)

PAT_MIXED_SENTIMENT = re.compile(
    r"\b(but|however|although|though|yet|while|even as|in spite of|offset by)\b",
    re.IGNORECASE,
)

PAT_NEUTRAL_REPORTING = re.compile(
    r"\b(killed|dead|death|dies|crash|accident|fire|earthquake|storm|flood|"
    r"probe|investigat|charges|arrest|police|lawsuit|sued|trial|testimony|dispute)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MisclassifiedHeadline:
    """Detailed record of an individual misclassification."""

    text: str
    true_label: str
    pred_label: str
    pred_score: float
    category: str


@dataclass(frozen=True)
class ErrorAnalysisResult:
    """Aggregated taxonomy counts and representative sampled headline errors."""

    model_name: str
    total_samples: int
    total_errors: int
    category_counts: dict[str, int]
    samples_by_category: dict[str, list[MisclassifiedHeadline]]


def categorize_misclassification(
    text: str,
    true_label: str,
    pred_label: str,
) -> str:
    """Categorize an individual error into the standardized 5-class taxonomy."""
    # 1. Neutral reporting of an adverse event
    if (
        true_label == "neutral"
        and pred_label in ("negative", "positive")
        and PAT_NEUTRAL_REPORTING.search(text)
    ):
        return "neutral_reporting_of_negative_events"

    # 2. Negation reversal failure
    if PAT_NEGATION.search(text):
        return "negation"

    # 3. Mixed sentiment multi-clause contradiction
    if PAT_MIXED_SENTIMENT.search(text):
        return "mixed_sentiment"

    # 4. Sarcasm, scare quotes, or irony
    if PAT_SARCASM.search(text):
        return "sarcasm"

    # 5. Domain-specific terminology
    if PAT_DOMAIN_TERMS.search(text):
        return "domain_terms"

    return "other"


def analyze_model_errors(
    texts: Sequence[str],
    y_true: Sequence[str],
    y_pred: Sequence[str],
    scores: Sequence[float],
    model_name: str,
    max_samples_per_category: int = 5,
) -> ErrorAnalysisResult:
    """Group all misclassifications into categories and sample representative headlines."""
    category_counts = dict.fromkeys(TAXONOMY_CATEGORIES, 0)
    samples_by_category: dict[str, list[MisclassifiedHeadline]] = {
        cat: [] for cat in TAXONOMY_CATEGORIES
    }

    total_errors = 0

    for text, t, p, sc in zip(texts, y_true, y_pred, scores, strict=True):
        if t != p:
            total_errors += 1
            cat = categorize_misclassification(text, t, p)
            category_counts[cat] = category_counts.get(cat, 0) + 1

            if len(samples_by_category[cat]) < max_samples_per_category:
                samples_by_category[cat].append(
                    MisclassifiedHeadline(
                        text=text,
                        true_label=t,
                        pred_label=p,
                        pred_score=round(sc, 4),
                        category=cat,
                    )
                )

    return ErrorAnalysisResult(
        model_name=model_name,
        total_samples=len(texts),
        total_errors=total_errors,
        category_counts=category_counts,
        samples_by_category=samples_by_category,
    )
