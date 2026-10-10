# Changelog

All notable changes to the **News Sentiment Analyzer** system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-10

Initial production release of the News Sentiment Analyzer: an end-to-end multi-model sentiment classification, token attribution explainability, time-series tracking, and research evaluation system.

### Added

#### Phase 1: Ingestion & Storage Architecture
- Normalized data model with SQLAlchemy 2.0 and Alembic schema migrations (`articles`, `topics`, `predictions`, `ingestion_runs`, `duplicates`, `article_explanations`).
- Multi-provider ingestion interfaces for GDELT DOC 2.0 API, RSS feeds (`feedparser`), and NewsAPI.
- Resilient network fetching with exponential backoff (`tenacity`), per-provider sliding-window rate limiting, and typed exception hierarchies.
- Two-stage deduplication pipeline (exact URL SHA-256 fingerprinting + normalized headline string cleaning).
- Idempotent ingestion runs with full audit logging.

#### Phase 2: Model Layer & Inference Pipeline
- Unified `SentimentModel` interface standardizing label predictions, polarity scores in $[-1.0, 1.0]$, and class probability distributions across disparate architectures.
- VADER rule-based lexicon implementation with tuned threshold bounds ($\pm 0.05$).
- Hugging Face `HFTransformerModel` abstraction for PyTorch sequence-classification models with pinned revisions.
- Registered out-of-the-box support for RoBERTa Sentiment (`cardiffnlp/twitter-roberta-base-sentiment-latest`) and FinBERT (`ProsusAI/finbert`).
- High-throughput batch inference pipeline (`InferencePipeline`) scoring unanalyzed headlines with append-only persistence.

#### Phase 3: Labeled Benchmark Dataset & Evaluation Suite
- Stratified news headline labeling CLI (`newsent label`) with interactive terminal UI.
- Gold standard in-domain test dataset (`data/benchmarks/in_domain_test.jsonl`, $N = 300$) balanced across 5 news beats (`markets`, `tech`, `climate`, `politics`, `world`).
- Dual-annotator agreement protocol achieving Cohen's Kappa $\kappa = 0.814$.
- Financial PhraseBank benchmark integration ($N = 2,264$) with 100% agreement subset and immutable split indices (`seed=42`).
- Benchmark contamination detection registry (`news_sentiment.evaluation.contamination`) flagging in-sample memorization.
- Percentile bootstrap confidence interval generation ($B = 1,000$) for Macro-F1 with zero manual entry in reports.

#### Phase 4: Encoder Fine-Tuning & Domain Gap Analysis
- Multi-seed fine-tuning script (`scripts/train.py`) and Google Colab / Kaggle GPU notebook (`notebooks/finetune_sentiment.ipynb`) for DistilRoBERTa (`distilbert/distilroberta-base`).
- Validation split Macro-F1 checkpoint selection across 3 seeds (`[42, 43, 44]`) reporting mean $\pm$ standard deviation.
- Strict isolation and quarantine of held-out test splits.
- Domain gap quantification ($\Delta_{\text{domain}} = \text{Macro-F1}_{\text{FPB}} - \text{Macro-F1}_{\text{InDomain}}$).
- Formal Model Card documentation (`docs/MODEL_CARD.md`).

#### Phase 5: Explainability & Faithfulness Evaluation
- Unified token attribution interface `explain(text, model, method) -> list[TokenAttribution]` attributing continuous prediction scores.
- Leave-one-out occlusion with explicit grammatical negation handling (preventing inverted phrases like `"not good"` from misattributing positive polarity to `"good"`).
- Dual transformer explainers: Captum Integrated Gradients on word embeddings and SHAP Partitioning over text coalitions.
- Quantitative faithfulness evaluation (`scripts/faithfulness.py`) measuring progressive token deletion/insertion Area Over the Perturbation Curve (AOPC) against a 10-permutation random baseline.
- Human rationale plausibility evaluation on 100 annotated news headlines measuring token-level Precision, Recall, and F1.
- Top-$k$ token attribution Jaccard agreement matrices across models and explainers.

#### Phase 6: FastAPI Backend Production Service
- Versioned `/api/v1` REST API architecture:
  - `POST /api/v1/analyze`: Multi-text batch inference across selected models.
  - `POST /api/v1/explain`: Real-time token attribution calculation with dual-tier caching.
  - `GET /api/v1/topics` and `POST /api/v1/topics`: Topic management and tracking.
  - `GET /api/v1/topics/{id}/headlines`: Paginated, filterable headline explorer.
  - `GET /api/v1/topics/{id}/summary`: Class distribution, percentages, and mean polarity.
  - `GET /api/v1/topics/{id}/trend`: Daily sentiment time-series and headline volumes.
  - `GET /api/v1/models`: Model registry discovery with evaluation and explainability metrics.
  - `GET /api/v1/health`: Liveness beacon with model and database statuses.
  - `POST /api/v1/jobs/collect-and-analyze`: Protected automated ingestion and inference endpoint.
- Standardized error envelope (`{"error": {"code": str, "message": str, "details": Any}}`).
- Lifespan preloading for zero cold-start CPU inference.
- Sliding-window in-memory IP rate limiter (120 req/min).

#### Phase 7: Interactive React Dashboard (Vite + React 19 + TypeScript)
- Typed API client generated directly from OpenAPI schema via `openapi-typescript`.
- Curated Vanilla CSS design system with responsive dark mode, glassmorphism cards, glowing cyan accents, and shimmer skeletons.
- 5 comprehensive pages:
  - **Topic Dashboard**: KPI metrics, Recharts dual-axis volume/score trend, donut distribution, filterable headline table, per-model toggle.
  - **Headline Detail**: Multi-model prediction cards, interactive token highlighter (scaled opacity by weight, red/green signed valence), method toggle, top-token bar chart.
  - **Try It Live**: Real-time headline tester with presets and side-by-side multi-model attributions.
  - **Model Comparison**: Pairwise agreement matrix heatmap and model disagreement explorer with score deltas.
  - **Research Results**: Benchmark tables, domain gap cards, faithfulness perturbation gains, and contamination badges.
- Vitest + Testing Library test suite (16 tests across 5 suites).

#### Phase 8: Deployment, CI/CD, Documentation & Release
- Multi-stage Docker backend container with CPU-only PyTorch and non-root security isolation.
- Multi-stage Docker frontend container served via Nginx with SPA routing and API reverse-proxy.
- `docker-compose.yml` orchestrating API, web dashboard, and persistent volume storage.
- Automated daily scheduled collection via GitHub Actions cron and standalone bash runner (`scripts/scheduled_collection.sh`).
- Complete GitHub Actions CI pipeline covering backend linting, typechecking, pytest coverage ($\ge 80\%$), frontend lint/test/build, and Docker container verification.
- Release workflow publishing tagged GitHub Releases (`v*`).
- Documentation suite: `docs/DEPLOYMENT.md`, `docs/DATA_CARD.md`, `CHANGELOG.md`, `docs/DECISIONS.md`, and comprehensive `README.md`.
