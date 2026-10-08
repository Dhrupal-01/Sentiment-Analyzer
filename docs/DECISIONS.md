# Architecture Decision Records (ADR)

This document tracks all non-trivial technical and architectural decisions for the **News Sentiment Analyzer** project.

---

## ADR-001: Project Layout and Package Structure
- **Date**: 2026-10-08
- **Decision**: Adopt the canonical `src/` layout with `src/news_sentiment` as the root package, separating code from project metadata, tests, scripts, and documentation.
- **Reasoning**:
  - Eliminates accidental imports of the local working directory during testing (`import news_sentiment` only resolves if installed in the active environment or wheel).
  - Enforces reproducible packaging and packaging isolation.
  - Aligns with modern Python packaging best practices (PEP 517/PEP 621).
- **Alternatives Rejected**:
  - Flat layout (root `news_sentiment/` directory): Rejected due to import leakage and ambiguity between installed vs local source files during pytest execution.

---

## ADR-002: Build Backend — Hatchling (PEP 517 / PEP 621)
- **Date**: 2026-10-08
- **Decision**: Use `hatchling` as the build backend in `pyproject.toml`.
- **Reasoning**:
  - Modern, fast, and fully compliant with PEP 621 declarative metadata and PEP 517 build standards.
  - Native editable install support (`pip install -e .`).
  - Zero heavy binary dependencies or lockfile idiosyncrasies.
- **Alternatives Rejected**:
  - `setuptools` with `setup.py` / `setup.cfg`: Rejected as legacy and unnecessarily verbose.
  - `poetry-core` / Poetry: Rejected to avoid imposing Poetry tooling constraints on developers who prefer standard pip/venv workflows.
  - `flit`: Rejected due to less flexible build target customization compared to Hatchling.

---

## ADR-003: Configuration Management via Pydantic Settings
- **Date**: 2026-10-08
- **Decision**: Use `pydantic-settings` (`BaseSettings`) with environment variable parsing and `.env` fallback.
- **Reasoning**:
  - Strong runtime validation, type coercion, and schema introspection.
  - Native compatibility with FastAPI and Pydantic v2.
  - Clean separation of secrets and environment configuration.
- **Alternatives Rejected**:
  - Raw `os.environ` / `python-dotenv` without validation: Rejected due to lack of type safety, validation, and error reporting.
  - `dynaconf`: Rejected as an unnecessarily heavy dependency for our configuration scope.

---

## ADR-004: Dual-Mode Structured Logging Architecture
- **Date**: 2026-10-08
- **Decision**: Implement structured logging supporting both machine-readable JSON format (`JSONFormatter`) and human-readable formatted console output (`ConsoleFormatter`), controlled by the `LOG_FORMAT` environment variable.
- **Reasoning**:
  - Production deployments (Docker, Kubernetes) and log collectors (e.g., Datadog, ELK, CloudWatch) require structured JSON logs with ISO-8601 timestamps and key-value metadata.
  - Local terminal development benefits significantly from readable, concise console outputs.
  - Standard library `logging` implementation avoids introducing heavy third-party logging engines.
- **Alternatives Rejected**:
  - `loguru`: Rejected to adhere to dependency prudence and preserve native compatibility with standard logging handlers from FastAPI, Uvicorn, and SQLAlchemy.
  - Unstructured `print` statements: Rejected as non-viable for production software.

---

## ADR-005: Command-Line Interface via Typer
- **Date**: 2026-10-08
- **Decision**: Build the CLI (`newsent`) using `typer`.
- **Reasoning**:
  - Leverages Python type annotations for automatic parsing, validation, help generation, and shell autocompletion.
  - Underpinned by `click`, offering robust terminal handling while minimizing boilerplate.
  - Clean entrypoint defined in `[project.scripts]`.
- **Alternatives Rejected**:
  - `argparse`: Rejected due to boilerplate verbosity and lack of modern type-hint driven syntax.
  - Raw `click`: Rejected because Typer offers more readable code with type hints.

---

## ADR-006: Strict Type Checking and Fast Linting Strategy
- **Date**: 2026-10-08
- **Decision**: Mandate strict type checking via `mypy` on `src/news_sentiment` and comprehensive linting/formatting via `ruff`.
- **Reasoning**:
  - `ruff` replaces Black, Flake8, and isort with 10-100x faster execution, accelerating the feedback loop.
  - `mypy --strict` catches subtle type errors, `None` dereferences, and missing return types before runtime.
  - Standing rule requires lint, type-check, and tests to pass on every change.
- **Alternatives Rejected**:
  - Separate `black` + `flake8` + `isort`: Rejected due to execution overhead and configuration fragmentation.
  - Loose / permissive typing: Rejected because production reliability is an explicit project goal.

---

## ADR-007: News Ingestion Sources & Terms of Use Compliance
- **Date**: 2026-10-08
- **Decision**: Implement three complementary news sources (GDELT DOC 2.0 as primary default, Publisher RSS feeds via `feedparser`, and NewsAPI as an optional key-gated provider). Explicitly document and adhere to each source's terms of service:
  1. **GDELT DOC 2.0 API (Default)**:
     - *Terms of Use*: Open access public research project. No API key required. Permits research and non-commercial/commercial indexing and headline analytics. Requires responsible rate pacing (enforced via `rate_limit_gdelt`, minimum 1.0s spacing).
  2. **Publisher RSS Feeds (Feedparser)**:
     - *Terms of Use*: Standard publisher RSS terms permit reading and syndicating headline titles, summaries, and canonical URLs for monitoring and non-commercial personal/research indexing under copyright Fair Use. Scraping or republishing full article body text is strictly prohibited and not implemented.
  3. **NewsAPI.org (Optional)**:
     - *Terms of Use*: The free Developer tier is strictly restricted to development, testing, and non-commercial personal projects. It enforces a 100 requests per 24-hour quota, up to 24-hour article publication delays, and requires attribution. Configured as an optional provider, only activated when an explicit `NEWSAPI_KEY` is provided.
- **Reasoning**:
  - Guarantees immediate zero-configuration out-of-the-box functionality via GDELT and RSS without requiring external API keys.
  - Maintains strict legal and terms-of-service compliance across all sources.
- **Alternatives Rejected**:
  - Web scraping HTML news pages directly: Rejected due to fragile DOM parsing, frequent anti-bot blocks (Cloudflare, Akamai), and copyright/TOS violation risks.
  - Commercial paid APIs (Bloomberg, Factiva, Reuters News API): Rejected to keep the project open-source and reproducible without costly subscriptions.

---

## ADR-008: Multi-Stage Deduplication and Audit Trail Architecture
- **Date**: 2026-10-08
- **Decision**: Deduplicate articles using a two-stage filter (exact URL canonicalization and normalized-title matching), and audit duplicate occurrences in an `article_duplicates` table rather than silently dropping them.
- **Reasoning**:
  - Ingesting headlines across multiple providers inherently produces duplicates when multiple outlets syndicate the same AP/Reuters story or when marketing query parameters vary.
  - Stage 1 canonicalizes URLs by lowercasing scheme/domain and stripping tracking parameters (`utm_*`, `gclid`, `fbclid`, `ref`).
  - Stage 2 normalizes headline titles by lowercasing, stripping punctuation, and removing publisher suffixes (e.g. ` - Reuters`, ` | BBC News`, ` — Wall Street Journal`).
  - Storing duplicates in `article_duplicates` preserves auditability, allows measuring cross-source duplication rates, and keeps the canonical `articles` table pristine for model inference and evaluation.
- **Alternatives Rejected**:
  - Silent drops (`INSERT OR IGNORE` without logging): Rejected because it destroys operational provenance and prevents evaluating cross-outlet syndication overlap.
  - Fuzzy Levenshtein / embedding similarity in database queries: Rejected as overly slow for high-throughput ingestion; deterministic normalized titles provide predictable, indexed O(1) performance.

---

## ADR-009: Relational Persistence with SQLAlchemy 2.0 and Alembic
- **Date**: 2026-10-08
- **Decision**: Use SQLAlchemy 2.0 Declarative Mapping (`Mapped` and `mapped_column`) with Alembic version-controlled migrations for both SQLite (local development/testing) and PostgreSQL (production).
- **Reasoning**:
  - SQLite zero-configuration database enables fully offline tests and local iteration.
  - Generic SQLAlchemy column types (`DateTime(timezone=True)`, `String`, `Text`, `Boolean`) guarantee clean portability to PostgreSQL in production Docker containers.
  - Alembic tracks schema changes with explicit migration revisions (`0001_initial_schema.py`).
- **Alternatives Rejected**:
  - Raw SQLite `sqlite3` driver with raw SQL strings: Rejected due to lack of portability to PostgreSQL and missing schema migration management.
  ---

## ADR-010: Model Layer Interface, Registry, and Traceable Prediction Storage
- **Date**: 2026-10-08
- **Decision**: Define an abstract `SentimentModel` interface with `name`, `version`, and `predict(texts) -> list[Prediction]`. Predictions are registered in an immutable relational table with a composite unique constraint on `(article_id, model_name, model_version)`.
- **Reasoning**:
  - Reproducibility and experiment tracking: Machine learning predictions must always be traceable to the exact model name and version that produced them.
  - Non-destructive updates: Existing prediction rows are never overwritten. When a new model version is released or registered, new rows are appended. This allows longitudinal tracking of model drift and side-by-side performance comparisons.
  - Optional ML dependencies: Heavy frameworks (`torch`, `transformers`) are isolated in the `[ml]` optional extra. The core package can be installed and run anywhere using VADER with minimal resource usage and zero GPU/torch dependencies.
- **Alternatives Rejected**:
  - Storing only a single `sentiment` column on the `articles` table: Rejected because it prevents comparing multiple models on the same article and destroys historical lineage when models are retrained.
  - Overwriting predictions on rerun: Rejected because it breaks auditability and prevents retrospective evaluation.

---

## ADR-011: VADER Lexicon Baseline and Uncalibrated Proportions Caveat
- **Date**: 2026-10-08
- **Decision**: Implement `VaderModel` as a lightweight rule-based baseline using `vaderSentiment`, applying standard compound score thresholds of $\pm 0.05$ (positive if compound $\ge 0.05$, negative if compound $\le -0.05$, else neutral).
- **Caveat & Calibration Notice**:
  - VADER outputs `pos`, `neu`, and `neg` proportions that sum to 1.0. It is critical to note that **these proportions are not calibrated Bayesian or frequentist probabilities**.
  - They represent the ratio of lexicon-matched token valence intensities relative to total sentence length. Users and downstream modules must not treat them as calibrated posterior class probabilities $P(\text{class} \mid \text{text})$.
  - For continuous evaluation, VADER's normalized compound score in $[-1.0, 1.0]$ is used directly as the model `score`.
- **Alternatives Rejected**:
  - TextBlob: Rejected because VADER provides superior handling of punctuation, casing emphasis, and negations in short headline strings.

---

## ADR-012: Pretrained Transformer Models, Continuous Score Alignment, and Training Domain Discrepancies
- **Date**: 2026-10-08
- **Decision**: Implement `HFTransformerModel` wrapping Hugging Face sequence classification pipelines with pinned model revisions and explicit label mappings. Calculate continuous score as $\text{score} = P(\text{positive}) - P(\text{negative}) \in [-1.0, 1.0]$. Register two initial pretrained models representing distinct linguistic domains:
  1. `cardiffnlp/twitter-roberta-base-sentiment-latest` (`roberta`):
     - *Training Domain*: Social media posts / Twitter tweets (~124M tweets, fine-tuned on TweetEval sentiment).
     - *Linguistic Characteristics*: Optimized for informal text, colloquial phrasing, idioms, and punctuation intensity. Tends to interpret strong rhetoric or sensationalist news headlines with heightened valence.
  2. `ProsusAI/finbert` (`finbert`):
     - *Training Domain*: Financial news and analyst reports (Financial PhraseBank, corporate earnings transcripts).
     - *Linguistic Characteristics*: Specialized for market terminology (e.g. "growth", "losses", "cut", "downgrade"). Tends to classify general political or social news as neutral, while responding sharply to macroeconomic signals.
- **Continuous Score Formula**:
  - By computing $\text{score} = P(\text{positive}) - P(\text{negative})$, transformer outputs align directly with VADER's compound score scale in $[-1.0, 1.0]$, enabling direct quantitative correlation, scatter analysis, and drift metrics.
- **Comparative Metrics**:
  - Implement pairwise agreement rate and Cohen's kappa ($\kappa = \frac{p_o - p_e}{1 - p_e}$) directly in pure Python without introducing heavy scikit-learn dependencies to evaluate inter-model concordance.
- **Alternatives Rejected**:
  - Using argmax class confidence as `score`: Rejected because confidence in $[0, 1]$ does not capture directionality or polar intensity across classes.

