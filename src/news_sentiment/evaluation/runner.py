"""End-to-end benchmark evaluation runner and report generation."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from news_sentiment.evaluation.benchmarks import (
    BenchmarkItem,
    ensure_financial_phrasebank,
    load_benchmark_split,
)
from news_sentiment.evaluation.contamination import ContaminationStatus, check_contamination
from news_sentiment.evaluation.error_analysis import ErrorAnalysisResult, analyze_model_errors
from news_sentiment.evaluation.metrics import EvaluationReport, compute_classification_metrics
from news_sentiment.models.base import SentimentModel
from news_sentiment.storage.database import get_db_session
from news_sentiment.storage.repository import AnnotationRepository


@dataclass(frozen=True)
class ModelEvaluationOutput:
    """Evaluation output for a single model on a dataset."""

    model_name: str
    model_version: str
    dataset_name: str
    contamination: ContaminationStatus
    metrics: EvaluationReport
    error_analysis: ErrorAnalysisResult


class BenchmarkRunner:
    """Orchestrates model evaluation across public benchmarks and in-domain annotations."""

    def __init__(self, output_dir: Path = Path("reports/eval")) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_in_domain_dataset(
        self,
        annotator_id: str | None = None,
        reference_file: Path | None = None,
    ) -> list[BenchmarkItem]:
        """Load in-domain ground truth from database annotations or reference JSONL."""
        if reference_file and reference_file.exists():
            return load_benchmark_split(reference_file)

        # Query human annotations from database
        with get_db_session() as session:
            annos = AnnotationRepository.get_annotations(
                session=session,
                annotator_id=annotator_id,
                exclude_skipped=True,
            )
            items: list[BenchmarkItem] = []
            for a in annos:
                if a.article:
                    items.append(
                        BenchmarkItem(
                            id=a.article.id,
                            text=a.article.title,
                            label=a.label.lower(),
                        )
                    )
            return items

    def load_financial_phrasebank_test(self) -> list[BenchmarkItem]:
        """Ensure Financial PhraseBank is initialized and load the deterministic test split."""
        splits = ensure_financial_phrasebank()
        return load_benchmark_split(splits["test"])

    def evaluate_model_on_dataset(
        self,
        model: SentimentModel,
        dataset_name: str,
        items: list[BenchmarkItem],
    ) -> ModelEvaluationOutput:
        """Run inference and evaluate metrics for one model on a dataset."""
        contamination = check_contamination(model.name, dataset_name)

        if not items:
            empty_report = compute_classification_metrics([], [])
            empty_errors = analyze_model_errors([], [], [], [], model.name)
            return ModelEvaluationOutput(
                model_name=model.name,
                model_version=model.version,
                dataset_name=dataset_name,
                contamination=contamination,
                metrics=empty_report,
                error_analysis=empty_errors,
            )

        texts = [it.text for it in items]
        y_true = [it.label for it in items]

        # Model inference
        predictions = model.predict(texts)
        y_pred = [p.label for p in predictions]
        scores = [p.score for p in predictions]

        metrics = compute_classification_metrics(y_true, y_pred)
        errors = analyze_model_errors(
            texts=texts,
            y_true=y_true,
            y_pred=y_pred,
            scores=scores,
            model_name=model.name,
        )

        return ModelEvaluationOutput(
            model_name=model.name,
            model_version=model.version,
            dataset_name=dataset_name,
            contamination=contamination,
            metrics=metrics,
            error_analysis=errors,
        )

    def run_all_evaluations(
        self,
        models: list[SentimentModel],
        in_domain_items: list[BenchmarkItem] | None = None,
        annotator_id: str | None = None,
        reference_file: Path | None = None,
    ) -> dict[str, list[ModelEvaluationOutput]]:
        """Run all models on both in-domain and Financial PhraseBank datasets."""
        # 1. Financial PhraseBank test split
        fpb_items = self.load_financial_phrasebank_test()

        # 2. In-domain dataset
        if in_domain_items is not None:
            id_items = in_domain_items
        else:
            id_items = self.load_in_domain_dataset(
                annotator_id=annotator_id,
                reference_file=reference_file,
            )

        results: dict[str, list[ModelEvaluationOutput]] = {
            "financial_phrasebank": [],
            "in_domain": [],
        }

        for model in models:
            res_fpb = self.evaluate_model_on_dataset(
                model=model,
                dataset_name="financial_phrasebank",
                items=fpb_items,
            )
            results["financial_phrasebank"].append(res_fpb)

            res_id = self.evaluate_model_on_dataset(
                model=model,
                dataset_name="in_domain",
                items=id_items,
            )
            results["in_domain"].append(res_id)

        return results

    def save_reports(
        self,
        results: dict[str, list[ModelEvaluationOutput]],
        json_path: Path | None = None,
        md_path: Path | None = None,
    ) -> tuple[Path, Path]:
        """Save evaluation results as machine-readable JSON and formatted Markdown."""
        out_json = json_path or (self.output_dir / "benchmark_results.json")
        out_md = md_path or (self.output_dir / "evaluation_report.md")

        # Serialized JSON
        serializable: dict[str, Any] = {}
        for ds_name, outputs in results.items():
            serializable[ds_name] = [asdict(o) for o in outputs]

        out_json.write_text(json.dumps(serializable, indent=2), encoding="utf-8")

        # Render Markdown
        md_content = self.render_markdown_report(results)
        out_md.write_text(md_content, encoding="utf-8")

        return out_json, out_md

    def render_markdown_report(
        self,
        results: dict[str, list[ModelEvaluationOutput]],
    ) -> str:
        """Render complete evaluation results into GitHub-flavored Markdown."""
        lines: list[str] = [
            "# Model Evaluation and Benchmark Report",
            "",
            "> Automated evaluation report generated by `scripts/evaluate.py`.",
            "",
            "## 1. Executive Summary Table",
            "",
            "| Dataset | Model | Accuracy | Macro-F1 (95% CI) | Status / Contamination |",
            "| :--- | :--- | :---: | :---: | :--- |",
        ]

        for ds_name, outputs in results.items():
            ds_title = (
                "Financial PhraseBank (Test)"
                if ds_name == "financial_phrasebank"
                else "In-Domain News (Test)"
            )
            for o in outputs:
                ci_low, ci_high = o.metrics.bootstrap_ci_macro_f1
                ci_str = f"[{ci_low:.3f}, {ci_high:.3f}]"
                if o.contamination.is_contaminated:
                    status_str = "⚠️ **Contaminated** (in-sample training benchmark)"
                else:
                    status_str = "✅ Uncontaminated (zero-shot out-of-domain)"

                if o.metrics.sample_size == 0:
                    lines.append(
                        f"| {ds_title} | `{o.model_name}` | N/A | N/A | No annotations present |"
                    )
                else:
                    acc_pct = f"{o.metrics.accuracy * 100:.1f}%"
                    f1_val = f"{o.metrics.macro_f1:.3f} {ci_str}"
                    lines.append(
                        f"| {ds_title} | `{o.model_name}` | {acc_pct} | {f1_val} | {status_str} |"
                    )

        lines.extend(
            [
                "",
                "---",
                "",
                "## 2. Detailed Per-Class Performance",
                "",
            ]
        )

        for ds_name, outputs in results.items():
            ds_title = (
                "Financial PhraseBank (AllAgree Test Split)"
                if ds_name == "financial_phrasebank"
                else "In-Domain News Headlines"
            )
            lines.extend(
                [
                    f"### Dataset: {ds_title}",
                    "",
                ]
            )
            for o in outputs:
                if o.metrics.sample_size == 0:
                    continue
                lines.extend(
                    [
                        f"#### Model: `{o.model_name}` (version: {o.model_version})",
                        "",
                        "| Class | Precision | Recall | F1-Score | Support |",
                        "| :--- | :---: | :---: | :---: | :---: |",
                    ]
                )
                for c_name, c_metric in o.metrics.per_class.items():
                    p_val = f"{c_metric.precision:.3f}"
                    r_val = f"{c_metric.recall:.3f}"
                    f_val = f"{c_metric.f1:.3f}"
                    sup = c_metric.support
                    lines.append(f"| {c_name.capitalize()} | {p_val} | {r_val} | {f_val} | {sup} |")
                cm = o.metrics.confusion_matrix
                lines.extend(
                    [
                        "",
                        "**Confusion Matrix** (Rows: True, Columns: Predicted):",
                        "",
                        "| True \\ Pred | Positive | Neutral | Negative |",
                        "| :--- | :---: | :---: | :---: |",
                        f"| **Positive** | {cm['positive']['positive']} | "
                        f"{cm['positive']['neutral']} | {cm['positive']['negative']} |",
                        f"| **Neutral** | {cm['neutral']['positive']} | "
                        f"{cm['neutral']['neutral']} | {cm['neutral']['negative']} |",
                        f"| **Negative** | {cm['negative']['positive']} | "
                        f"{cm['negative']['neutral']} | {cm['negative']['negative']} |",
                        "",
                    ]
                )

        lines.extend(
            [
                "---",
                "",
                "## 3. Error Analysis Taxonomy Breakdown",
                "",
                "Misclassifications categorized across 5 linguistic failure modes:",
                "",
            ]
        )

        for ds_name, outputs in results.items():
            ds_title = (
                "Financial PhraseBank"
                if ds_name == "financial_phrasebank"
                else "In-Domain Headlines"
            )
            hdr_cols = (
                "| Model | Total Errors | Negation | Domain Terms | Sarcasm | "
                "Mixed Sentiment | Neutral Reporting of Negative Events | Other |"
            )
            lines.extend(
                [
                    f"### {ds_title} Error Distribution",
                    "",
                    hdr_cols,
                    "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
                ]
            )
            for o in outputs:
                if o.metrics.sample_size == 0:
                    continue
                c = o.error_analysis.category_counts
                lines.append(
                    f"| `{o.model_name}` | {o.error_analysis.total_errors} | "
                    f"{c.get('negation', 0)} | {c.get('domain_terms', 0)} | "
                    f"{c.get('sarcasm', 0)} | {c.get('mixed_sentiment', 0)} | "
                    f"{c.get('neutral_reporting_of_negative_events', 0)} | "
                    f"{c.get('other', 0)} |"
                )
            lines.append("")

        lines.extend(
            [
                "### Sampled Error Case Examples",
                "",
            ]
        )
        for ds_name, outputs in results.items():
            for o in outputs:
                has_samples = any(o.error_analysis.samples_by_category.values())
                if not has_samples:
                    continue
                lines.append(f"#### Model `{o.model_name}` on {ds_name}")
                for cat, samples in o.error_analysis.samples_by_category.items():
                    if not samples:
                        continue
                    cat_title = cat.replace("_", " ").title()
                    lines.append(f"\n- **Category: {cat_title}**")
                    for s in samples[:3]:
                        pred_desc = f"Predicted: `{s.pred_label}` (score: {s.pred_score:+.2f})"
                        lines.append(f'  - *"{s.text}"*\n    True: `{s.true_label}` | {pred_desc}')
                lines.append("")

        return "\n".join(lines)
