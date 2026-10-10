"""Faithfulness, plausibility, and inter-method agreement evaluation metrics."""

import random
import re
from dataclasses import dataclass

from news_sentiment.explain.base import TokenAttribution
from news_sentiment.explain.tokenizer import (
    reconstruct_tokens_by_indices,
    remove_tokens_by_indices,
    tokenize_with_spans,
)
from news_sentiment.models.base import SentimentModel


@dataclass(frozen=True)
class PerturbationCurve:
    """Step-by-step perturbation score trajectory and computed AOPC."""

    step_scores: list[float]
    score_deltas: list[float]
    aopc: float


@dataclass(frozen=True)
class FaithfulnessResult:
    """Complete deletion and insertion evaluation comparing method against random baseline."""

    deletion_curve: PerturbationCurve
    insertion_curve: PerturbationCurve
    random_deletion_aopc: float
    random_insertion_aopc: float
    deletion_aopc_gain: float  # method deletion AOPC - random deletion AOPC

    def is_faithful(self) -> bool:
        """A method is faithful if its deletion AOPC exceeds the random-token baseline."""
        return self.deletion_aopc_gain > 0.0


def compute_faithfulness_curves(
    text: str,
    attributions: list[TokenAttribution],
    model: SentimentModel,
    max_steps: int = 5,
    random_samples: int = 10,
    seed: int = 42,
) -> FaithfulnessResult:
    """Evaluate deletion and insertion curves with AOPC against random-token baseline.

    Args:
        text: Input headline text.
        attributions: TokenAttribution list explaining the prediction.
        model: SentimentModel instance.
        max_steps: Maximum tokens to perturb (typically up to 5 tokens for headlines).
        random_samples: Number of random permutations for baseline averaging.
        seed: Random seed for baseline reproducibility.

    Returns:
        FaithfulnessResult containing curves, AOPC, and random baseline comparison.
    """
    clean_text = text.strip()
    spans = tokenize_with_spans(clean_text)
    if not spans or not attributions:
        empty_curve = PerturbationCurve(step_scores=[], score_deltas=[], aopc=0.0)
        return FaithfulnessResult(
            deletion_curve=empty_curve,
            insertion_curve=empty_curve,
            random_deletion_aopc=0.0,
            random_insertion_aopc=0.0,
            deletion_aopc_gain=0.0,
        )

    initial_pred = model.predict_one(clean_text)
    initial_score = initial_pred.score
    total_tokens = len(spans)
    k_steps = min(max_steps, total_tokens)

    # Rank tokens by absolute attribution weight descending
    # Match spans to attributions by position index
    indexed_attrs = [(i, abs(attr.weight)) for i, attr in enumerate(attributions[:total_tokens])]
    ranked_indices = [idx for idx, _ in sorted(indexed_attrs, key=lambda x: x[1], reverse=True)]

    # 1. Deletion Curve: Progressively delete top-k most important tokens
    del_scores: list[float] = []
    del_deltas: list[float] = []
    for step in range(1, k_steps + 1):
        del_set = set(ranked_indices[:step])
        perturbed_text = remove_tokens_by_indices(clean_text, spans, del_set)
        score = model.predict_one(perturbed_text).score if perturbed_text else 0.0
        del_scores.append(round(score, 4))
        delta = abs(initial_score - score)
        del_deltas.append(round(delta, 4))

    del_aopc = round(sum(del_deltas) / k_steps, 4) if k_steps > 0 else 0.0
    deletion_curve = PerturbationCurve(
        step_scores=del_scores,
        score_deltas=del_deltas,
        aopc=del_aopc,
    )

    # 2. Insertion Curve: Progressively insert top-k most important tokens into empty baseline
    ins_scores: list[float] = []
    ins_deltas: list[float] = []
    baseline_score = 0.0  # neutral reference baseline
    for step in range(1, k_steps + 1):
        ins_set = set(ranked_indices[:step])
        reconstructed_text = reconstruct_tokens_by_indices(spans, ins_set)
        score = model.predict_one(reconstructed_text).score if reconstructed_text else 0.0
        ins_scores.append(round(score, 4))
        delta = abs(score - baseline_score)
        ins_deltas.append(round(delta, 4))

    ins_aopc = round(sum(ins_deltas) / k_steps, 4) if k_steps > 0 else 0.0
    insertion_curve = PerturbationCurve(
        step_scores=ins_scores,
        score_deltas=ins_deltas,
        aopc=ins_aopc,
    )

    # 3. Random Baseline: Average AOPC over random token permutations
    rng = random.Random(seed)
    random_del_deltas: list[float] = []
    random_ins_deltas: list[float] = []

    for _ in range(random_samples):
        shuffled = list(range(total_tokens))
        rng.shuffle(shuffled)
        run_del_deltas: list[float] = []
        run_ins_deltas: list[float] = []

        for step in range(1, k_steps + 1):
            perm_set = set(shuffled[:step])
            # Deletion
            del_txt = remove_tokens_by_indices(clean_text, spans, perm_set)
            s_del = model.predict_one(del_txt).score if del_txt else 0.0
            run_del_deltas.append(abs(initial_score - s_del))

            # Insertion
            ins_txt = reconstruct_tokens_by_indices(spans, perm_set)
            s_ins = model.predict_one(ins_txt).score if ins_txt else 0.0
            run_ins_deltas.append(abs(s_ins - baseline_score))

        if run_del_deltas:
            random_del_deltas.append(sum(run_del_deltas) / k_steps)
        if run_ins_deltas:
            random_ins_deltas.append(sum(run_ins_deltas) / k_steps)

    avg_rand_del_aopc = (
        round(sum(random_del_deltas) / len(random_del_deltas), 4) if random_del_deltas else 0.0
    )
    avg_rand_ins_aopc = (
        round(sum(random_ins_deltas) / len(random_ins_deltas), 4) if random_ins_deltas else 0.0
    )
    gain = round(del_aopc - avg_rand_del_aopc, 4)

    return FaithfulnessResult(
        deletion_curve=deletion_curve,
        insertion_curve=insertion_curve,
        random_deletion_aopc=avg_rand_del_aopc,
        random_insertion_aopc=avg_rand_ins_aopc,
        deletion_aopc_gain=gain,
    )


def normalize_token_set(tokens: list[str]) -> set[str]:
    """Normalize tokens (lowercase, alphanumeric filtering) for overlap comparison."""
    clean: set[str] = set()
    for t in tokens:
        cleaned = re.sub(r"[^\w]", "", t.lower().strip())
        if cleaned:
            clean.add(cleaned)
    return clean


def compute_token_f1(
    predicted_tokens: list[str],
    ground_truth_tokens: list[str],
) -> tuple[float, float, float]:
    """Compute token-level Precision, Recall, and F1 between predicted tokens and human rationales.

    Returns:
        (precision, recall, f1)
    """
    pred_set = normalize_token_set(predicted_tokens)
    true_set = normalize_token_set(ground_truth_tokens)

    if not pred_set or not true_set:
        return 0.0, 0.0, 0.0

    overlap = len(pred_set & true_set)
    precision = overlap / len(pred_set)
    recall = overlap / len(true_set)

    if precision + recall == 0:
        return 0.0, 0.0, 0.0

    f1 = 2 * (precision * recall) / (precision + recall)
    return round(precision, 4), round(recall, 4), round(f1, 4)


def compute_jaccard_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Compute Jaccard similarity index between two token sets: |A ∩ B| / |A ∪ B|."""
    set_a = normalize_token_set(tokens_a)
    set_b = normalize_token_set(tokens_b)

    if not set_a and not set_b:
        return 1.0
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    intersection = len(set_a & set_b)
    return round(intersection / union, 4)
