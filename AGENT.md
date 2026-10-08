# AGENT Instructions — News Sentiment Analyzer

You are working as the lead engineer on the **News Sentiment Analyzer** project.

---

## Project Brief

### Goal
A production-quality system that collects news headlines, classifies their sentiment with several models, explains each prediction, tracks sentiment over time per topic, and serves all of this through an API and a web dashboard.

### Research Question
How reliable are off-the-shelf and fine-tuned sentiment models on real news headlines, and do their explanations faithfully reflect what drives their predictions? The project must answer this question with empirical evidence and reproducible benchmarks.

### Architecture Overview
- **Language & Layout**: Python 3.11+, `src/` layout, top-level package `news_sentiment`.
- **Ingestion**: Ingestion from multiple news sources into SQLite via SQLAlchemy (Postgres-compatible), with Alembic migrations.
- **Model Layer**: Unified interface abstracting:
  - VADER lexicon-based baseline
  - Pretrained transformer models (e.g., FinBERT, RoBERTa-sentiment)
  - Fine-tuned transformer model
- **Explainability & Evaluation**:
  - Feature attribution / explanation methods (e.g., Integrated Gradients, SHAP, LIME, or attention-based)
  - Faithfulness and plausibility evaluation metrics
  - Robustness and error analysis on ambiguous/domain-specific news headlines
- **API**: FastAPI backend exposing headline ingestion, inference, explanations, and sentiment trends over time.
- **Frontend**: React + TypeScript (Vite) interactive dashboard for real-time sentiment inspection and historical topic tracking.
- **Infrastructure**: Docker & Docker Compose for containerized deployment, GitHub Actions for continuous integration.

---

## Standing Rules

1. **Verify Quality Continuously**: Run lint (`ruff check`, `ruff format --check`), type-check (`mypy`), and test suite (`pytest`) after every change; never leave them failing.
2. **Strict Empirical Integrity**: Never fabricate metrics, benchmark numbers, sample outputs, or labels. Every number in any documentation, report, or paper must be directly produced and verified by a script in this repository.
3. **Secrets Hygiene**: Secrets and API keys must be loaded strictly via environment variables or `.env`, and never committed to version control.
4. **Dependency Prudence**: Ask the user before adding heavy dependencies (such as large deep learning frameworks, heavy visualization libraries, or extra runtimes).
5. **Architectural Decision Records**: Log every non-trivial design decision in `docs/DECISIONS.md` with:
   - Date
   - Decision
   - Reasoning
   - Alternatives rejected
6. **Git Hygiene & Conventional Commits**: Use small, focused commits with conventional prefixes (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`). Commit only using the user's connected Git account (`Dhrupal-01`), never attributing commits to an AI model.
