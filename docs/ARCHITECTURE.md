# System Architecture — News Sentiment Analyzer

## 1. Executive Summary & Research Motivation

The **News Sentiment Analyzer** is a production-grade system engineered to ingest news headlines across diverse sources, classify sentiment using multiple heterogeneous models, generate interpretable explanations for every prediction, track sentiment trajectories across topics over time, and serve predictions and analytics via a high-performance REST API and an interactive web dashboard.

### Core Research Question
> **How reliable are off-the-shelf and fine-tuned sentiment models on real news headlines, and do their explanations faithfully reflect what drives their predictions?**

News headlines exhibit distinct linguistic characteristics: concise syntax, domain-specific terminology (e.g., financial markets, geopolitical developments), irony, rhetorical questions, and dense emotional phrasing. This project empirically benchmarks:
1. **Model Reliability**: Predictive performance, calibration, and error distributions across Lexicon baselines, off-the-shelf general/financial transformers, and fine-tuned domain models.
2. **Explanation Faithfulness**: Whether attribution methods (e.g., Integrated Gradients, SHAP partition explainers, occlusion/erasure benchmarks) accurately identify the true causal drivers of model decisions or merely provide plausible post-hoc rationalizations.

---

## 2. High-Level Component Architecture

The following diagram illustrates the major architectural components, data boundaries, and subpackage relationships.

```mermaid
graph TD
    subgraph External["External News Feeds"]
        GDELT["GDELT DOC 2.0 API"]
        RSS["Publisher RSS Wire Feeds"]
        NewsAPI["NewsAPI.org (Optional Key-Gated)"]
    end

    subgraph IngestionLayer["Ingestion Layer (src/news_sentiment/sources)"]
        Collector["Ingestion Service & Source Clients"]
        Normalizer["Text Normalizer, Canonicalizer & Deduplicator"]
    end

    subgraph StorageLayer["Storage Layer (src/news_sentiment/storage)"]
        SQLAlchemy["SQLAlchemy Declarative ORM (SQLite / Postgres)"]
        Alembic["Alembic Migrations"]
        DB[(News Sentiment Database)]
    end

    subgraph ModelLayer["Model Layer (src/news_sentiment/models)"]
        ModelInterface["SentimentModel (Unified Interface)"]
        VADER["VADER Baseline"]
        Pretrained["Pretrained Transformers (FinBERT / RoBERTa)"]
        FineTuned["Fine-Tuned Domain Model"]
        Registry["Model Registry & InferencePipeline"]
    end

    subgraph ExplainEvalLayer["Explainability & Evaluation (src/news_sentiment/explain & evaluation)"]
        Explainer["Attribution Service (Occlusion / IG / SHAP)"]
        Faithfulness["Faithfulness Benchmarks (AOPC Deletion & Insertion)"]
        Metrics["Evaluation Suite (Macro-F1, Bootstrap CIs, Calibration)"]
    end

    subgraph ServingLayer["API & Access Layer (src/news_sentiment/api & cli)"]
        FastAPI["FastAPI REST API (/api/v1)"]
        CLI["Typer CLI (newsent)"]
    end

    subgraph PresentationLayer["Presentation Layer (frontend/)"]
        WebUI["React 19 + TypeScript (Vite) Dashboard"]
    end

    External --> Collector
    Collector --> Normalizer
    Normalizer --> SQLAlchemy
    SQLAlchemy --> DB
    Alembic --> DB

    ModelInterface -.-> VADER
    ModelInterface -.-> Pretrained
    ModelInterface -.-> FineTuned
    Registry --> ModelInterface

    Collector --> Registry
    Registry --> Explainer
    Explainer --> Faithfulness
    Registry --> Metrics

    SQLAlchemy --> FastAPI
    DB --> FastAPI
    FastAPI --> WebUI
    FastAPI --> CLI
    CLI --> Registry
```

---

## 3. End-to-End Data and Inference Flow

The data flow spans news ingestion, sentiment classification, feature attribution, trend persistence, and frontend delivery.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Analyst
    participant UI as React Dashboard
    participant API as FastAPI Backend (/api/v1)
    participant Ingest as Ingestion Service (sources)
    participant Models as Model Layer & Registry (models)
    participant Explain as Explainability Service (explain)
    participant DB as Database (SQLAlchemy)

    User->>UI: Select topic & date range
    UI->>API: GET /api/v1/topics/{id}/trend
    API->>DB: Query aggregated sentiment over time
    DB-->>API: Return daily scores and article volume series
    API-->>UI: Deliver JSON series for Recharts visualizer

    Note over Ingest,DB: Background Ingestion & Scheduled Inference Pipeline
    Ingest->>Ingest: Fetch headlines from GDELT, RSS, or NewsAPI
    Ingest->>DB: Store canonical articles & metadata (Article table)
    Ingest->>Models: Batch predict sentiment across active models
    Models-->>Ingest: PredictionResult (label, probabilities, signed score)
    Ingest->>DB: Persist predictions (ArticlePrediction table)

    User->>UI: Inspect headline prediction & attribution
    UI->>API: POST /api/v1/explain {text, model, method}
    API->>Explain: Run token attribution (Occlusion, IG, or SHAP)
    Explain-->>API: Token attributions (list of tokens and signed weights)
    API-->>UI: Visual explanation payload
    UI-->>User: Render interactive token attribution heatmap
```

---

## 4. Package & Module Blueprint

The codebase uses a strict `src/` layout under the root package `news_sentiment`:

| Subpackage | Responsibility | Key Classes / Modules |
| :--- | :--- | :--- |
| `news_sentiment.config` | Settings & logging | `Settings` (Pydantic Settings), `configure_logging`, `JSONFormatter`, `ConsoleFormatter` |
| `news_sentiment.sources` | Ingestion connectors | `BaseSourceClient`, `GDELTSourceClient`, `RSSSourceClient`, `NewsAPISourceClient`, `IngestionService` |
| `news_sentiment.storage` | Persistence & schema | SQLAlchemy declarative models (`Article`, `ArticlePrediction`, `ArticleAnnotation`, `Topic`, `IngestionRun`), `TopicRepository`, `ArticleRepository`, Alembic migrations |
| `news_sentiment.models` | Inference abstraction | `SentimentModel`, `PredictionResult`, `VaderModel`, `HFTransformerModel`, `InferencePipeline`, model registry |
| `news_sentiment.explain` | Explainability engine | `BaseExplainer`, `OcclusionExplainer`, `IntegratedGradientsExplainer`, `ShapPartitionExplainer`, `ExplanationService` |
| `news_sentiment.evaluation`| Empirical evaluation | Faithfulness metrics (AOPC deletion/insertion, plausibility token-F1), classification benchmarks, bootstrap CIs, contamination check |
| `news_sentiment.api` | Web service API | FastAPI routes (`/health`, `/api/v1/health`, `/api/v1/topics`, `/api/v1/analyze`, `/api/v1/explain`, `/api/v1/models`, `/api/v1/jobs/collect-and-analyze`) |
| `news_sentiment.cli` | Command-line tool | `newsent` Typer CLI: `version`, `collect`, `analyze`, `compare`, `topics`, `label`, `label-agreement`, `explain` |
| `frontend/` | Web Dashboard | React 19 + TypeScript (Vite), time-series charts, headline explorer, model comparison matrix, explanation heatmap |
| `scripts/` | Data & evaluation scripts | Reproducible scripts (`evaluate.py`, `faithfulness.py`, `train.py`, `seed_in_domain_data.py`) |

---

## 5. Model Layer & Unified Interface Design

To enable fair, rigorous empirical comparison, all sentiment models adhere to a single unified contract:

```python
class SentimentModel(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique model identifier (e.g. 'vader', 'roberta', 'finbert', 'fine_tuned')."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Model or checkpoint version."""
        pass

    @abstractmethod
    def predict(self, texts: list[str]) -> list[PredictionResult]:
        """Generate sentiment predictions for a batch of texts."""
        pass

    def predict_one(self, text: str) -> PredictionResult:
        """Convenience method to predict sentiment for a single text."""
        return self.predict([text])[0]
```

### Models Benchmarked:
1. **Lexicon Baseline**: VADER (Rule-based lexical sentiment engine with compound score normalization).
2. **Pretrained General Transformer**: RoBERTa fine-tuned on tweets/social text (`cardiffnlp/twitter-roberta-base-sentiment-latest`).
3. **Pretrained Domain Transformer**: FinBERT (`ProsusAI/finbert`, domain-adapted for financial news).
4. **Custom Fine-Tuned Transformer**: DistilRoBERTa fine-tuned on financial sentence benchmarks with domain gap evaluation.

---

## 6. Explainability and Faithfulness Evaluation

Explainability answers *why* a model made a specific prediction. The evaluation pipeline answers *whether that explanation is faithful*.

1. **Attribution Methods**:
   - **Leave-One-Out Occlusion**: Token masking with negation-aware delta attribution.
   - **Integrated Gradients**: Path-integral gradient baselines via Captum for transformer embeddings.
   - **SHAP Partition Explainer**: Game-theoretic Shapley value estimation using hierarchical text partitioning.
2. **Faithfulness Benchmarking**:
   - **Progressive Deletion Curves (AOPC)**: If top attributed tokens are causally important, deleting them progressively causes rapid decay in model confidence. Evaluated against a 10-permutation random-token baseline.
   - **Progressive Insertion Curves**: Verifies sufficiency when restoring top tokens into neutral baselines.
   - **Plausibility Agreement**: Token-level F1 comparing model attributions with human rationale annotations.

---

## 7. Serving, Deployment, and Quality Assurance

- **API Layer**: FastAPI application exposing versioned `/api/v1` asynchronous endpoints, in-memory CPU model preloading at lifespan startup, and strict Pydantic payload validation.
- **Frontend Layer**: React 19 + TypeScript powered by Vite, providing responsive charts for temporal topic sentiment and interactive saliency heatmaps.
- **Continuous Integration**: GitHub Actions executing on every pull request and push:
  - Linting & formatting check with `ruff`
  - Strict type checking with `mypy` on `src/news_sentiment`
  - Fast test execution and minimum coverage check with `pytest` and `pytest-cov` (target $\ge 80\%$)
- **Docker Deployment**: Multi-stage Dockerfile packaging the FastAPI application with CPU-only torch, Uvicorn, and docker-compose for the full local stack.
