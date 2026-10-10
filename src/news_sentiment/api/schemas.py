"""Pydantic request and response schemas for all News Sentiment Analyzer API endpoints."""

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Standard Error Envelope Schemas
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Detailed error payload contained in standard error responses."""

    code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable explanation of the error condition")
    details: Any = Field(
        default=None,
        description="Optional diagnostic details or validation items",
    )


class ErrorResponse(BaseModel):
    """Consistent envelope returned for all API error responses."""

    error: ErrorDetail


# ---------------------------------------------------------------------------
# Sentiment Analysis Schemas
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Request payload for multi-text, multi-model sentiment classification."""

    texts: list[Annotated[str, Field(min_length=1, max_length=1000)]] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of news headlines to classify (1-50 items, max 1000 chars each)",
        examples=[
            [
                "Wall Street opens sharply higher on cooler inflation print",
                "Severe quarterly losses trigger corporate restructuring",
            ]
        ],
    )
    models: list[str] | None = Field(
        default=None,
        description=(
            "Optional list of model names (e.g. 'vader', 'roberta'). Defaults to all available."
        ),
        examples=[["vader", "roberta"]],
    )


class ModelPredictionItem(BaseModel):
    """Classification prediction result from a single sentiment model."""

    label: str = Field(..., description="Sentiment category: 'positive', 'neutral', or 'negative'")
    score: float = Field(..., description="Continuous polarity score in [-1.0, 1.0]")
    probabilities: dict[str, float] = Field(..., description="Class probability distribution")
    model_version: str = Field(..., description="Version or pinned checkpoint revision string")


class TextAnalysisResult(BaseModel):
    """Prediction outputs for a single input text across requested models."""

    text: str = Field(..., description="Original input headline text")
    predictions: dict[str, ModelPredictionItem] = Field(
        ..., description="Model predictions keyed by model name"
    )


class AnalyzeResponse(BaseModel):
    """Response payload containing predictions across texts and models."""

    texts_count: int = Field(..., description="Number of analyzed text items")
    models: list[str] = Field(..., description="List of models that produced predictions")
    results: list[TextAnalysisResult] = Field(..., description="Per-text classification results")


# ---------------------------------------------------------------------------
# Explainability Schemas
# ---------------------------------------------------------------------------


class TokenAttributionItem(BaseModel):
    """Attribution weight assigned to an individual word/punctuation token."""

    token: str = Field(..., description="Word or punctuation token from the headline")
    weight: float = Field(
        ...,
        description="Continuous signed attribution weight explaining score delta in [-1.0, 1.0]",
    )


class ExplainRequest(BaseModel):
    """Request payload to explain a prediction score on a headline."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="News headline text to explain (max 1000 characters)",
        examples=["Operating profit rose to EUR 13.1 mn from EUR 8.7 mn"],
    )
    model: str = Field(
        default="vader",
        description="Target model name ('vader', 'roberta', 'finbert', 'fine_tuned')",
        examples=["vader"],
    )
    method: str = Field(
        default="occlusion",
        description="Attribution method: 'occlusion', 'integrated_gradients', or 'shap'",
        examples=["occlusion"],
    )
    article_id: int | None = Field(
        default=None,
        description="Optional database article ID for persistent caching",
        examples=[12],
    )


class ExplainResponse(BaseModel):
    """Response payload containing token attributions explaining a prediction."""

    text: str = Field(..., description="Headline text that was explained")
    model_name: str = Field(..., description="Model name evaluated")
    model_version: str = Field(..., description="Model version or checkpoint revision")
    method: str = Field(..., description="Attribution algorithm applied")
    prediction_label: str = Field(..., description="Predicted sentiment class")
    prediction_score: float = Field(..., description="Continuous polarity score in [-1.0, 1.0]")
    attributions: list[TokenAttributionItem] = Field(
        ..., description="Ordered list of token attributions"
    )


# ---------------------------------------------------------------------------
# Topics Schemas
# ---------------------------------------------------------------------------


class TopicCreateRequest(BaseModel):
    """Request payload to create a news tracking topic."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique topic identifier name (e.g. 'markets', 'climate')",
        examples=["macroeconomics"],
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Search query string used during news provider ingestion",
        examples=["inflation OR interest rates OR central bank"],
    )
    is_active: bool = Field(
        default=True,
        description="Whether this topic is active for automated ingestion runs",
    )


class TopicResponse(BaseModel):
    """Tracking topic metadata with current article counts."""

    id: int = Field(..., description="Topic primary key identifier")
    name: str = Field(..., description="Unique topic name")
    query: str = Field(..., description="Search query string")
    is_active: bool = Field(..., description="Active tracking status")
    created_at: datetime = Field(..., description="Creation timestamp")
    article_count: int = Field(default=0, description="Total ingested articles under this topic")


class TopicsListResponse(BaseModel):
    """List of all configured tracking topics."""

    topics: list[TopicResponse] = Field(..., description="Configured topics")
    total: int = Field(..., description="Total count of topics")


# ---------------------------------------------------------------------------
# Headlines & Pagination Schemas
# ---------------------------------------------------------------------------


class HeadlinePredictionItem(BaseModel):
    """Stored model prediction attached to a headline."""

    model_name: str = Field(..., description="Model name")
    model_version: str = Field(..., description="Model version")
    label: str = Field(..., description="Sentiment label")
    score: float = Field(..., description="Sentiment score in [-1.0, 1.0]")
    probabilities: dict[str, float] = Field(..., description="Class probabilities")
    created_at: datetime = Field(..., description="Timestamp when prediction was saved")


class HeadlineItem(BaseModel):
    """Ingested news article headline with attached model predictions."""

    id: int = Field(..., description="Article primary key identifier")
    title: str = Field(..., description="Article headline title")
    url: str = Field(..., description="Canonical article source URL")
    outlet: str | None = Field(default=None, description="News publisher outlet")
    published_at: datetime | None = Field(default=None, description="Publication timestamp")
    topic: str = Field(..., description="Associated topic name")
    provider: str = Field(..., description="Ingestion provider source")
    predictions: list[HeadlinePredictionItem] = Field(
        default_factory=list, description="Model predictions stored for this headline"
    )


class PaginatedHeadlinesResponse(BaseModel):
    """Paginated collection of headlines matching filter criteria."""

    items: list[HeadlineItem] = Field(..., description="Headlines on current page")
    total: int = Field(..., description="Total matching headline count across all pages")
    page: int = Field(..., description="Current 1-based page index")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total page count")


# ---------------------------------------------------------------------------
# Topic Summary & Trend Analytics Schemas
# ---------------------------------------------------------------------------


class SentimentDistribution(BaseModel):
    """Raw count of headlines per sentiment class."""

    positive: int = Field(..., description="Count of positive headlines")
    neutral: int = Field(..., description="Count of neutral headlines")
    negative: int = Field(..., description="Count of negative headlines")


class SentimentPercentages(BaseModel):
    """Proportion of headlines per sentiment class (0.0 to 100.0)."""

    positive: float = Field(..., description="Percentage positive")
    neutral: float = Field(..., description="Percentage neutral")
    negative: float = Field(..., description="Percentage negative")


class DateRange(BaseModel):
    """Effective filtering date bounds."""

    start: datetime | None = Field(default=None, description="Earliest publication timestamp")
    end: datetime | None = Field(default=None, description="Latest publication timestamp")


class TopicSummaryResponse(BaseModel):
    """Aggregated sentiment overview for a topic within a date range."""

    topic_id: int = Field(..., description="Topic identifier")
    topic_name: str = Field(..., description="Topic name")
    model_name: str = Field(..., description="Model used to compute sentiment scores")
    total_headlines: int = Field(..., description="Total headlines evaluated")
    sentiment_distribution: SentimentDistribution = Field(..., description="Class counts")
    sentiment_percentages: SentimentPercentages = Field(..., description="Class percentages")
    average_score: float = Field(..., description="Arithmetic mean sentiment score in [-1.0, 1.0]")
    date_range: DateRange = Field(..., description="Date range evaluated")


class DailyTrendItem(BaseModel):
    """Daily aggregated sentiment metric point for time-series charting."""

    date: str = Field(..., description="Calendar date in 'YYYY-MM-DD' ISO format")
    average_score: float = Field(..., description="Mean polarity score for the day in [-1.0, 1.0]")
    headline_volume: int = Field(..., description="Number of headlines published on this date")
    positive_count: int = Field(..., description="Count of positive headlines")
    neutral_count: int = Field(..., description="Count of neutral headlines")
    negative_count: int = Field(..., description="Count of negative headlines")


class TopicTrendResponse(BaseModel):
    """Chronological time-series trend of sentiment and headline volume."""

    topic_id: int = Field(..., description="Topic identifier")
    topic_name: str = Field(..., description="Topic name")
    model_name: str = Field(..., description="Model name evaluated")
    time_series: list[DailyTrendItem] = Field(..., description="Chronological daily data points")


# ---------------------------------------------------------------------------
# Models Registry & System Health Schemas
# ---------------------------------------------------------------------------


class ModelEvaluationMetrics(BaseModel):
    """Empirical benchmarking metrics from Phase 3 & 4 evaluations."""

    accuracy: float = Field(..., description="Accuracy on benchmark test set")
    macro_f1: float = Field(..., description="Macro-F1 score across sentiment classes")
    bootstrap_ci_macro_f1: list[float] | None = Field(
        default=None, description="95% non-parametric bootstrap confidence interval"
    )
    sample_size: int = Field(default=0, description="Test split evaluation sample count")


class ModelExplainabilityMetrics(BaseModel):
    """Faithfulness and plausibility evaluation metrics from Phase 5."""

    deletion_aopc_gain: float = Field(
        ..., description="Faithfulness gain over random deletion baseline"
    )
    pct_faithful: float = Field(
        ..., description="Percentage of samples with positive faithfulness gain"
    )
    plausibility_top3_f1: float = Field(
        ..., description="Token-level F1 against human rationale annotations"
    )


class ModelMetadataItem(BaseModel):
    """Metadata, domain description, and evaluation scores for a registered model."""

    name: str = Field(..., description="Registered model name key")
    version: str = Field(..., description="Model version or checkpoint revision")
    domain: str = Field(..., description="Training domain and data characteristics")
    is_contaminated: bool = Field(
        ..., description="True if trained directly on evaluated benchmark dataset"
    )
    contamination_reason: str | None = Field(
        default=None, description="Contamination explanation if flagged"
    )
    evaluation_metrics: ModelEvaluationMetrics | None = Field(
        default=None, description="Benchmark classification metrics"
    )
    explainability_metrics: ModelExplainabilityMetrics | None = Field(
        default=None, description="Faithfulness and plausibility explainability metrics"
    )


class ModelsRegistryResponse(BaseModel):
    """List of all registered sentiment models with complete metadata."""

    models: list[ModelMetadataItem] = Field(..., description="Registered sentiment models")
    total: int = Field(..., description="Count of registered models")


class HealthResponse(BaseModel):
    """System health, environment info, and runtime dependency status."""

    status: str = Field(..., description="Overall service status ('healthy' or 'degraded')")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Semantic version string")
    environment: str = Field(..., description="Active execution environment")
    database: str = Field(..., description="Database connection health ('connected' or 'error')")
    models_loaded: list[str] = Field(..., description="List of preloaded sentiment models")
