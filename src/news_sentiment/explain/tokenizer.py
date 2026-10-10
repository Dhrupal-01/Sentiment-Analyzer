"""Tokenization utilities with character span tracking for faithful text perturbations."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenSpan:
    """Token string with exact start and end character offsets in original text."""

    token: str
    start: int
    end: int


def tokenize_with_spans(text: str) -> list[TokenSpan]:
    """Tokenize text into words and punctuation while tracking character offsets.

    Uses a word/punctuation regex pattern (\\w+|[^\\w\\s]) to preserve exact positions.
    """
    spans: list[TokenSpan] = []
    for match in re.finditer(r"\w+|[^\w\s]", text):
        spans.append(
            TokenSpan(
                token=match.group(0),
                start=match.start(),
                end=match.end(),
            )
        )
    return spans


def remove_token_by_span(text: str, span: TokenSpan) -> str:
    """Produce a perturbed text by removing the token at the specified span offset."""
    prefix = text[: span.start].rstrip()
    suffix = text[span.end :].lstrip()
    combined = f"{prefix} {suffix}" if prefix and suffix else (prefix or suffix)
    return re.sub(r"\s+", " ", combined).strip()


def remove_tokens_by_indices(text: str, spans: list[TokenSpan], indices: set[int]) -> str:
    """Produce perturbed text by omitting tokens at multiple specified indices."""
    if not indices:
        return text
    if len(indices) >= len(spans):
        return ""

    # Reconstruct text by keeping only unselected spans
    parts: list[str] = [spans[i].token for i in range(len(spans)) if i not in indices]
    return " ".join(parts).strip()


def reconstruct_tokens_by_indices(spans: list[TokenSpan], indices: set[int]) -> str:
    """Produce text containing exclusively tokens at the specified indices in original order."""
    if not indices:
        return ""
    sorted_idx = sorted(i for i in indices if 0 <= i < len(spans))
    return " ".join(spans[i].token for i in sorted_idx).strip()
