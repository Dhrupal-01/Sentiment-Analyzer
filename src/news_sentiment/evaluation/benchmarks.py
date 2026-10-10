"""Benchmark dataset management for Financial PhraseBank and in-domain evaluation."""

import hashlib
import json
import random
import urllib.request
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path("data/benchmarks")
FPB_DIR = DATA_DIR / "financial_phrasebank"
FPB_RAW_URL = (
    "https://raw.githubusercontent.com/maxwellsarpong/NLP-financial-text-processing-dataset/"
    "master/Sentences_AllAgree.txt"
)


@dataclass(frozen=True)
class BenchmarkItem:
    """A single labeled sentence in a benchmark dataset."""

    id: int
    text: str
    label: str  # positive, neutral, negative


def ensure_financial_phrasebank(
    dest_dir: Path | None = None,
    seed: int = 42,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
) -> dict[str, Path]:
    """Ensure Financial PhraseBank (AllAgree subset) is downloaded and split deterministically.

    Choice Justification:
    The 100% agreement subset (AllAgree) ensures unambiguous, zero-noise ground-truth
    sentiment where all 5-8 annotators reached complete consensus. Lower agreement subsets
    introduce human annotator variance and subjectivity into model benchmarking.

    Args:
        dest_dir: Target directory (defaults to data/benchmarks/financial_phrasebank).
        seed: Random seed for deterministic train/val/test partitioning.
        train_ratio: Fraction for training split (default 0.70).
        val_ratio: Fraction for validation split (default 0.15).
        test_ratio: Fraction for testing split (default 0.15).

    Returns:
        Dictionary mapping split names to their jsonl file paths.
    """
    target_dir = dest_dir or FPB_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = target_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / "Sentences_AllAgree.txt"

    train_file = target_dir / "train.jsonl"
    val_file = target_dir / "val.jsonl"
    test_file = target_dir / "test.jsonl"
    splits_file = target_dir / "splits.json"
    metadata_file = target_dir / "metadata.json"

    # If already prepared, return immediately
    if train_file.exists() and val_file.exists() and test_file.exists():
        return {
            "train": train_file,
            "val": val_file,
            "test": test_file,
        }

    # 1. Download raw file if not present (checking local repo file first)
    if not raw_file.exists():
        repo_raw = Path("data/benchmarks/financial_phrasebank/raw/Sentences_AllAgree.txt")
        if repo_raw.exists():
            content = repo_raw.read_bytes()
            raw_file.write_bytes(content)
        else:
            req = urllib.request.Request(FPB_RAW_URL, headers={"User-Agent": "NewsSentiment/0.1.0"})
            with urllib.request.urlopen(req) as resp:
                content = resp.read()
            raw_file.write_bytes(content)
    else:
        content = raw_file.read_bytes()

    sha256 = hashlib.sha256(content).hexdigest()

    # 2. Parse sentences and labels
    lines = content.decode("utf-8", errors="replace").strip().split("\n")
    items: list[BenchmarkItem] = []
    class_counts: dict[str, int] = {}

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line or "@" not in line:
            continue
        text, raw_label = line.rsplit("@", 1)
        label = raw_label.strip().lower()
        items.append(BenchmarkItem(id=idx, text=text.strip(), label=label))
        class_counts[label] = class_counts.get(label, 0) + 1

    # 3. Deterministic stratification/splitting by class with fixed seed
    rng = random.Random(seed)
    class_indices: dict[str, list[int]] = {}
    for item in items:
        class_indices.setdefault(item.label, []).append(item.id)

    train_ids: list[int] = []
    val_ids: list[int] = []
    test_ids: list[int] = []

    for label_indices in class_indices.values():
        shuffled = list(label_indices)
        rng.shuffle(shuffled)
        n = len(shuffled)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_ids.extend(shuffled[:n_train])
        val_ids.extend(shuffled[n_train : n_train + n_val])
        test_ids.extend(shuffled[n_train + n_val :])

    train_ids.sort()
    val_ids.sort()
    test_ids.sort()

    # Save splits ID mapping
    splits_data = {
        "seed": seed,
        "splits": {
            "train": train_ids,
            "val": val_ids,
            "test": test_ids,
        },
    }
    splits_file.write_text(json.dumps(splits_data, indent=2), encoding="utf-8")

    # Map items by id
    item_by_id = {it.id: it for it in items}

    # Save JSONL files
    def _save_jsonl(path: Path, ids: list[int]) -> None:
        with path.open("w", encoding="utf-8") as f:
            for item_id in ids:
                it = item_by_id[item_id]
                f.write(json.dumps({"id": it.id, "text": it.text, "label": it.label}) + "\n")

    _save_jsonl(train_file, train_ids)
    _save_jsonl(val_file, val_ids)
    _save_jsonl(test_file, test_ids)

    # Save metadata
    metadata = {
        "dataset_name": "Financial PhraseBank",
        "subset": "Sentences_AllAgree (100% agreement)",
        "source_citation": (
            "Malo, P., Sinha, A., Korhonen, P., Wallenius, J., & Takala, P. (2014). "
            "Good debt or bad debt: Detecting semantic orientations in economic texts. "
            "Journal of the Association for Information Science and Technology, 65(4), 782-796."
        ),
        "source_url": FPB_RAW_URL,
        "license": (
            "Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported (CC BY-NC-SA 3.0)"
        ),
        "sha256": sha256,
        "seed": seed,
        "total_samples": len(items),
        "split_counts": {
            "train": len(train_ids),
            "val": len(val_ids),
            "test": len(test_ids),
        },
        "class_distribution_all": class_counts,
        "justification": (
            "Selected the 100% agreement subset (AllAgree) to establish an unambiguous, zero-noise "
            "gold standard. Sentences with lower agreement (50%, 66%, 75%) contain subjective or "
            "ambiguous framing that introduces inter-annotator noise. Unanimous consensus "
            "guarantees that evaluation errors reflect true model classification failure."
        ),
    }
    metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "train": train_file,
        "val": val_file,
        "test": test_file,
    }


def load_benchmark_split(split_file: Path) -> list[BenchmarkItem]:
    """Load benchmark items from a jsonl split file."""
    if not split_file.exists():
        raise FileNotFoundError(f"Benchmark file not found: {split_file}")

    items: list[BenchmarkItem] = []
    with split_file.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            items.append(BenchmarkItem(id=data["id"], text=data["text"], label=data["label"]))
    return items
