#!/usr/bin/env python3
"""Fine-tune encoder models with multi-seed variance logging and validation checkpoint selection.

Evaluates checkpoints strictly on the validation split. Never touches test sets during training.
"""

import argparse
import csv
import json
import math
import random
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

from news_sentiment.evaluation.metrics import compute_classification_metrics


def load_jsonl_dataset(path: Path) -> list[dict[str, Any]]:
    """Load jsonl dataset into memory."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def calculate_mean_std(values: list[float]) -> tuple[float, float]:
    """Calculate sample mean and standard deviation."""
    n = len(values)
    if n == 0:
        return 0.0, 0.0
    mean = sum(values) / n
    if n <= 1:
        return round(mean, 4), 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std = math.sqrt(variance)
    return round(mean, 4), round(std, 4)


class MetricLogger:
    """Logs training and evaluation telemetry to CSV."""

    def __init__(self, csv_path: Path) -> None:
        self.csv_path = csv_path
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.fieldnames = [
            "run_id",
            "seed",
            "epoch",
            "step",
            "split",
            "loss",
            "accuracy",
            "macro_f1",
            "f1_positive",
            "f1_neutral",
            "f1_negative",
        ]
        if not self.csv_path.exists():
            with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()

    def log(self, record: dict[str, Any]) -> None:
        """Append metric row to CSV."""
        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            row = {k: record.get(k, "") for k in self.fieldnames}
            writer.writerow(row)


def run_dry_run_training(
    config: dict[str, Any],
    train_data: list[dict[str, Any]],
    val_data: list[dict[str, Any]],
    test_data: list[dict[str, Any]] | None,
    indomain_data: list[dict[str, Any]] | None,
    logger: MetricLogger,
) -> dict[str, Any]:
    """Execute fast simulated training for tests, validation, and zero-GPU environments."""
    output_dir = Path(config["training"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    best_dir = output_dir / "best"
    best_dir.mkdir(parents=True, exist_ok=True)

    seeds = config["training"]["seeds"]
    num_epochs = config["training"]["num_train_epochs"]
    seed_val_f1s: list[float] = []
    seed_val_accs: list[float] = []
    seed_test_f1s: list[float] = []
    seed_test_accs: list[float] = []
    seed_indomain_f1s: list[float] = []
    seed_indomain_accs: list[float] = []

    per_seed_results = []
    best_seed = seeds[0]
    best_val_f1 = -1.0

    for seed in seeds:
        rng = random.Random(seed)
        seed_dir = output_dir / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)

        # Simulate epochs
        for epoch in range(1, num_epochs + 1):
            epoch_loss = 0.8 / epoch + rng.uniform(-0.02, 0.02)
            # Progressive improvement on validation
            val_acc = min(0.92, 0.72 + (epoch * 0.04) + rng.uniform(-0.015, 0.015))
            val_f1 = min(0.90, 0.68 + (epoch * 0.045) + rng.uniform(-0.015, 0.015))

            batch_sz = config["training"]["per_device_train_batch_size"]
            step_num = epoch * (len(train_data) // batch_sz)

            logger.log(
                {
                    "run_id": f"dry_run_{seed}",
                    "seed": seed,
                    "epoch": epoch,
                    "step": step_num,
                    "split": "validation",
                    "loss": round(epoch_loss, 4),
                    "accuracy": round(val_acc, 4),
                    "macro_f1": round(val_f1, 4),
                    "f1_positive": round(val_f1 + 0.02, 4),
                    "f1_neutral": round(val_f1 + 0.04, 4),
                    "f1_negative": round(val_f1 - 0.05, 4),
                }
            )

        final_val_f1 = round(val_f1, 4)
        final_val_acc = round(val_acc, 4)
        seed_val_f1s.append(final_val_f1)
        seed_val_accs.append(final_val_acc)

        if final_val_f1 > best_val_f1:
            best_val_f1 = final_val_f1
            best_seed = seed

        # Evaluate on test sets if provided
        test_f1 = round(final_val_f1 - rng.uniform(0.005, 0.025), 4)
        test_acc = round(final_val_acc - rng.uniform(0.005, 0.02), 4)
        seed_test_f1s.append(test_f1)
        seed_test_accs.append(test_acc)

        # In-domain test set exhibits the key DOMAIN GAP (~10-15% drop)
        indomain_gap = rng.uniform(0.12, 0.16)
        indomain_f1 = round(test_f1 - indomain_gap, 4)
        indomain_acc = round(test_acc - indomain_gap + 0.02, 4)
        seed_indomain_f1s.append(indomain_f1)
        seed_indomain_accs.append(indomain_acc)

        per_seed_results.append(
            {
                "seed": seed,
                "val_macro_f1": final_val_f1,
                "val_accuracy": final_val_acc,
                "test_macro_f1": test_f1,
                "test_accuracy": test_acc,
                "indomain_macro_f1": indomain_f1,
                "indomain_accuracy": indomain_acc,
                "checkpoint_path": str(seed_dir),
            }
        )

    # Save mock checkpoint config to best/
    mock_config = {
        "_name_or_path": config["model"]["base_model"],
        "architectures": ["RobertaForSequenceClassification"],
        "id2label": config["model"]["id2label"],
        "label2id": config["model"]["label2id"],
        "num_labels": 3,
        "best_seed": best_seed,
        "best_val_macro_f1": best_val_f1,
    }
    (best_dir / "config.json").write_text(json.dumps(mock_config, indent=2), encoding="utf-8")

    mean_val_f1, std_val_f1 = calculate_mean_std(seed_val_f1s)
    mean_val_acc, std_val_acc = calculate_mean_std(seed_val_accs)
    mean_test_f1, std_test_f1 = calculate_mean_std(seed_test_f1s)
    mean_test_acc, std_test_acc = calculate_mean_std(seed_test_accs)
    mean_id_f1, std_id_f1 = calculate_mean_std(seed_indomain_f1s)
    mean_id_acc, std_id_acc = calculate_mean_std(seed_indomain_accs)

    domain_gap_f1 = round(mean_test_f1 - mean_id_f1, 4)
    domain_gap_acc = round(mean_test_acc - mean_id_acc, 4)

    summary = {
        "status": "completed",
        "mode": "dry_run_simulation",
        "model_architecture": config["model"]["base_model"],
        "best_seed": best_seed,
        "seeds": seeds,
        "per_seed_results": per_seed_results,
        "validation_metrics": {
            "macro_f1_mean": mean_val_f1,
            "macro_f1_std": std_val_f1,
            "accuracy_mean": mean_val_acc,
            "accuracy_std": std_val_acc,
        },
        "financial_phrasebank_test_metrics": {
            "macro_f1_mean": mean_test_f1,
            "macro_f1_std": std_test_f1,
            "accuracy_mean": mean_test_acc,
            "accuracy_std": std_test_acc,
        },
        "in_domain_news_test_metrics": {
            "macro_f1_mean": mean_id_f1,
            "macro_f1_std": std_id_f1,
            "accuracy_mean": mean_id_acc,
            "accuracy_std": std_id_acc,
        },
        "domain_gap": {
            "macro_f1_drop": domain_gap_f1,
            "accuracy_drop": domain_gap_acc,
            "relative_f1_degradation_pct": round((domain_gap_f1 / mean_test_f1) * 100, 2),
            "description": (
                f"Macro-F1 drops by {domain_gap_f1:.3f} "
                f"({round((domain_gap_f1 / mean_test_f1) * 100, 1)}%) "
                "when transferring from Financial PhraseBank to broad in-domain news headlines."
            ),
        },
        "best_checkpoint_path": str(best_dir),
    }

    return summary


def run_hf_training(
    config: dict[str, Any],
    train_data: list[dict[str, Any]],
    val_data: list[dict[str, Any]],
    test_data: list[dict[str, Any]] | None,
    indomain_data: list[dict[str, Any]] | None,
    logger: MetricLogger,
) -> dict[str, Any]:
    """Execute multi-seed training with Hugging Face Trainer."""
    try:
        import torch
        from transformers import (
            AutoModelForSequenceClassification,
            AutoTokenizer,
            Trainer,
            TrainingArguments,
            set_seed,
        )
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch and Transformers are required for full model training. "
            "Install them with: pip install 'news-sentiment[ml]'\n"
            "Or run training on free GPU in Google Colab / Kaggle via "
            "notebooks/finetune_sentiment.ipynb.\n"
            "To test the training pipeline locally on CPU without PyTorch, "
            "run with: python scripts/train.py --dry-run"
        ) from exc

    output_dir = Path(config["training"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    best_dir = output_dir / "best"

    base_model_id = config["model"]["base_model"]
    id2label = {int(k): v for k, v in config["model"]["id2label"].items()}
    label2id = {k: int(v) for k, v in config["model"]["label2id"].items()}
    max_length = config["data"]["max_length"]

    tokenizer = AutoTokenizer.from_pretrained(base_model_id)

    def _prepare_dataset(records: list[dict[str, Any]]) -> Any:
        texts = [r["text"] for r in records]
        labels = [label2id[r["label"].lower()] for r in records]
        encodings = tokenizer(
            texts,
            truncation=True,
            padding="max_length",
            max_length=max_length,
            return_tensors="pt",
        )

        class _Dataset(torch.utils.data.Dataset):
            def __len__(self) -> int:
                return len(labels)

            def __getitem__(self, idx: int) -> dict[str, Any]:
                item = {k: v[idx] for k, v in encodings.items()}
                item["labels"] = torch.tensor(labels[idx], dtype=torch.long)
                return item

        return _Dataset()

    train_dataset = _prepare_dataset(train_data)
    val_dataset = _prepare_dataset(val_data)

    def compute_metrics(eval_pred: Any) -> dict[str, float]:
        logits, labels = eval_pred
        preds = logits.argmax(axis=-1)
        pred_labels = [id2label[int(p)] for p in preds]
        true_labels = [id2label[int(t)] for t in labels]
        report = compute_classification_metrics(true_labels, pred_labels)
        return {
            "accuracy": report.accuracy,
            "macro_f1": report.macro_f1,
            "f1_positive": report.per_class["positive"].f1,
            "f1_neutral": report.per_class["neutral"].f1,
            "f1_negative": report.per_class["negative"].f1,
        }

    seeds = config["training"]["seeds"]
    seed_val_f1s: list[float] = []
    seed_val_accs: list[float] = []
    seed_test_f1s: list[float] = []
    seed_test_accs: list[float] = []
    seed_indomain_f1s: list[float] = []
    seed_indomain_accs: list[float] = []
    per_seed_results = []

    best_seed = seeds[0]
    best_val_f1 = -1.0
    best_seed_model_dir: Path | None = None

    for seed in seeds:
        print(f"\n==================== Starting Training: Seed {seed} ====================")
        set_seed(seed)
        seed_output_dir = output_dir / f"seed_{seed}"

        model = AutoModelForSequenceClassification.from_pretrained(
            base_model_id,
            num_labels=len(id2label),
            id2label=id2label,
            label2id=label2id,
        )

        t_cfg = config["training"]
        training_args = TrainingArguments(
            output_dir=str(seed_output_dir),
            learning_rate=float(t_cfg["learning_rate"]),
            per_device_train_batch_size=int(t_cfg["per_device_train_batch_size"]),
            per_device_eval_batch_size=int(t_cfg["per_device_eval_batch_size"]),
            num_train_epochs=int(t_cfg["num_train_epochs"]),
            weight_decay=float(t_cfg["weight_decay"]),
            warmup_ratio=float(t_cfg["warmup_ratio"]),
            eval_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="macro_f1",
            greater_is_better=True,
            save_total_limit=1,
            seed=seed,
            report_to="none",
            logging_steps=10,
        )

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=val_dataset,
            tokenizer=tokenizer,
            compute_metrics=compute_metrics,
        )

        trainer.train()
        val_eval = trainer.evaluate()
        val_acc = round(float(val_eval.get("eval_accuracy", 0.0)), 4)
        val_f1 = round(float(val_eval.get("eval_macro_f1", 0.0)), 4)
        seed_val_accs.append(val_acc)
        seed_val_f1s.append(val_f1)

        logger.log(
            {
                "run_id": f"seed_{seed}",
                "seed": seed,
                "epoch": config["training"]["num_train_epochs"],
                "step": trainer.state.global_step,
                "split": "validation",
                "loss": round(float(val_eval.get("eval_loss", 0.0)), 4),
                "accuracy": val_acc,
                "macro_f1": val_f1,
                "f1_positive": round(float(val_eval.get("eval_f1_positive", 0.0)), 4),
                "f1_neutral": round(float(val_eval.get("eval_f1_neutral", 0.0)), 4),
                "f1_negative": round(float(val_eval.get("eval_f1_negative", 0.0)), 4),
            }
        )

        # Save checkpoint for this seed
        trainer.save_model(str(seed_output_dir / "best"))

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_seed = seed
            best_seed_model_dir = seed_output_dir / "best"

        # Evaluate on test split (strictly after training has finished)
        test_f1, test_acc = 0.0, 0.0
        if test_data:
            test_dataset = _prepare_dataset(test_data)
            test_eval = trainer.evaluate(test_dataset)
            test_f1 = round(float(test_eval.get("eval_macro_f1", 0.0)), 4)
            test_acc = round(float(test_eval.get("eval_accuracy", 0.0)), 4)
            seed_test_f1s.append(test_f1)
            seed_test_accs.append(test_acc)

        # Evaluate on in-domain test set
        id_f1, id_acc = 0.0, 0.0
        if indomain_data:
            id_dataset = _prepare_dataset(indomain_data)
            id_eval = trainer.evaluate(id_dataset)
            id_f1 = round(float(id_eval.get("eval_macro_f1", 0.0)), 4)
            id_acc = round(float(id_eval.get("eval_accuracy", 0.0)), 4)
            seed_indomain_f1s.append(id_f1)
            seed_indomain_accs.append(id_acc)

        per_seed_results.append(
            {
                "seed": seed,
                "val_macro_f1": val_f1,
                "val_accuracy": val_acc,
                "test_macro_f1": test_f1,
                "test_accuracy": test_acc,
                "indomain_macro_f1": id_f1,
                "indomain_accuracy": id_acc,
                "checkpoint_path": str(seed_output_dir / "best"),
            }
        )

    # Copy the overall best seed model to best_dir
    if best_seed_model_dir and best_seed_model_dir.exists():
        if best_dir.exists():
            shutil.rmtree(best_dir)
        shutil.copytree(best_seed_model_dir, best_dir)

    mean_val_f1, std_val_f1 = calculate_mean_std(seed_val_f1s)
    mean_val_acc, std_val_acc = calculate_mean_std(seed_val_accs)
    mean_test_f1, std_test_f1 = calculate_mean_std(seed_test_f1s)
    mean_test_acc, std_test_acc = calculate_mean_std(seed_test_accs)
    mean_id_f1, std_id_f1 = calculate_mean_std(seed_indomain_f1s)
    mean_id_acc, std_id_acc = calculate_mean_std(seed_indomain_accs)

    has_test = bool(seed_test_f1s and seed_indomain_f1s)
    domain_gap_f1 = round(mean_test_f1 - mean_id_f1, 4) if has_test else 0.0
    domain_gap_acc = round(mean_test_acc - mean_id_acc, 4) if has_test else 0.0
    rel_f1_drop = round((domain_gap_f1 / mean_test_f1) * 100, 2) if mean_test_f1 > 0 else 0.0

    summary = {
        "status": "completed",
        "mode": "huggingface_trainer",
        "model_architecture": base_model_id,
        "best_seed": best_seed,
        "seeds": seeds,
        "per_seed_results": per_seed_results,
        "validation_metrics": {
            "macro_f1_mean": mean_val_f1,
            "macro_f1_std": std_val_f1,
            "accuracy_mean": mean_val_acc,
            "accuracy_std": std_val_acc,
        },
        "financial_phrasebank_test_metrics": {
            "macro_f1_mean": mean_test_f1,
            "macro_f1_std": std_test_f1,
            "accuracy_mean": mean_test_acc,
            "accuracy_std": std_test_acc,
        },
        "in_domain_news_test_metrics": {
            "macro_f1_mean": mean_id_f1,
            "macro_f1_std": std_id_f1,
            "accuracy_mean": mean_id_acc,
            "accuracy_std": std_id_acc,
        },
        "domain_gap": {
            "macro_f1_drop": domain_gap_f1,
            "accuracy_drop": domain_gap_acc,
            "relative_f1_degradation_pct": rel_f1_drop,
            "description": (
                f"Macro-F1 drops by {domain_gap_f1:.3f} "
                "when transferring from Financial PhraseBank to broad in-domain news headlines."
            ),
        },
        "best_checkpoint_path": str(best_dir),
    }

    # Optional Push to Hub
    if config.get("hub", {}).get("push_to_hub", False):
        hub_id = config["hub"].get("hub_model_id")
        if hub_id:
            print(f"Pushing best model checkpoint to Hugging Face Hub: {hub_id}...")
            best_model = AutoModelForSequenceClassification.from_pretrained(best_dir)
            best_model.push_to_hub(hub_id)
            tokenizer.push_to_hub(hub_id)
            summary["hub_model_id"] = hub_id

    return summary


def main() -> int:
    """CLI execution entrypoint for fine-tuning pipeline."""
    parser = argparse.ArgumentParser(
        description="Fine-tune headline sentiment model across multiple seeds."
    )
    parser.add_argument(
        "--config", default="configs/train.yaml", help="Path to YAML training configuration."
    )
    parser.add_argument(
        "--seeds", default=None, help="Comma-separated random seeds (e.g. '42,43,44')."
    )
    parser.add_argument(
        "--epochs", type=int, default=None, help="Override number of training epochs."
    )
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate.")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute simulated training for offline verification.",
    )
    parser.add_argument(
        "--push-to-hub", action="store_true", help="Push best model to Hugging Face Hub."
    )
    parser.add_argument(
        "--eval-test", action="store_true", default=True, help="Evaluate on held-out test splits."
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        return 1

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Apply CLI overrides
    if args.seeds:
        config["training"]["seeds"] = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    if args.epochs:
        config["training"]["num_train_epochs"] = args.epochs
    if args.lr:
        config["training"]["learning_rate"] = args.lr
    if args.batch_size:
        config["training"]["per_device_train_batch_size"] = args.batch_size
    if args.push_to_hub:
        config["hub"]["push_to_hub"] = True

    train_path = Path(config["data"]["train_path"])
    val_path = Path(config["data"]["val_path"])
    test_path = Path(config["data"]["test_path"]) if args.eval_test else None
    indomain_path = Path(config["data"]["in_domain_path"]) if args.eval_test else None

    print(f"Loading training data from: {train_path}")
    print(f"Loading validation data from: {val_path}")
    train_data = load_jsonl_dataset(train_path)
    val_data = load_jsonl_dataset(val_path)
    test_data = load_jsonl_dataset(test_path) if test_path and test_path.exists() else None
    indomain_data = (
        load_jsonl_dataset(indomain_path) if indomain_path and indomain_path.exists() else None
    )

    logging_dir = Path(config["training"]["logging_dir"])
    logging_dir.mkdir(parents=True, exist_ok=True)
    csv_logger = MetricLogger(logging_dir / "metrics.csv")

    print(f"Seeds to train: {config['training']['seeds']}")
    print(f"Base model: {config['model']['base_model']}")

    if args.dry_run:
        print("\n[Running in Dry-Run Mode]")
        summary = run_dry_run_training(
            config=config,
            train_data=train_data,
            val_data=val_data,
            test_data=test_data,
            indomain_data=indomain_data,
            logger=csv_logger,
        )
    else:
        try:
            summary = run_hf_training(
                config=config,
                train_data=train_data,
                val_data=val_data,
                test_data=test_data,
                indomain_data=indomain_data,
                logger=csv_logger,
            )
        except RuntimeError as exc:
            print(f"\n{exc}", file=sys.stderr)
            return 1

    # Save summary JSON
    summary_path = logging_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote training summary report to: {summary_path}")

    # Display results table
    v = summary["validation_metrics"]
    t = summary["financial_phrasebank_test_metrics"]
    id_m = summary["in_domain_news_test_metrics"]
    gap = summary["domain_gap"]

    val_acc_pct = f"{v['accuracy_mean'] * 100:.1f}% ± {v['accuracy_std'] * 100:.1f}%"
    fpb_acc_pct = f"{t['accuracy_mean'] * 100:.1f}% ± {t['accuracy_std'] * 100:.1f}%"
    id_acc_pct = f"{id_m['accuracy_mean'] * 100:.1f}% ± {id_m['accuracy_std'] * 100:.1f}%"

    print("\n" + "=" * 76)
    print("                 MULTI-SEED TRAINING & DOMAIN GAP REPORT")
    print("=" * 76)
    print(f"Best Seed:               {summary['best_seed']}")
    print(f"Validation Macro-F1:     {v['macro_f1_mean']:.3f} ± {v['macro_f1_std']:.3f}")
    print(f"Validation Accuracy:     {val_acc_pct}")
    print("-" * 76)
    print(f"FPB Test Macro-F1:       {t['macro_f1_mean']:.3f} ± {t['macro_f1_std']:.3f}")
    print(f"FPB Test Accuracy:       {fpb_acc_pct}")
    print("-" * 76)
    print(f"In-Domain News Macro-F1: {id_m['macro_f1_mean']:.3f} ± {id_m['macro_f1_std']:.3f}")
    print(f"In-Domain News Accuracy: {id_acc_pct}")
    print("=" * 76)
    print(f"DOMAIN GAP (Macro-F1):   {gap['macro_f1_drop']:+.3f} (FPB Test -> In-Domain News)")
    print(f"Relative Degradation:    {gap['relative_f1_degradation_pct']:.1f}% drop across domains")
    print("=" * 76)

    return 0


if __name__ == "__main__":
    sys.exit(main())
