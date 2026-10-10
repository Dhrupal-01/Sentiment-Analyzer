"""Comprehensive integration tests for all News Sentiment Analyzer FastAPI endpoints."""

from datetime import UTC, datetime

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from news_sentiment.api.main import create_app
from news_sentiment.api.rate_limit import SimpleRateLimiter, get_rate_limiter
from news_sentiment.config.settings import Settings
from news_sentiment.storage.models import Article, Prediction, Topic


def test_health_endpoints(client: TestClient) -> None:
    """Verify both /health and /api/v1/health return healthy status and metadata."""
    for path in ["/health", "/api/v1/health"]:
        resp = client.get(path)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["environment"] == "testing"
        assert "version" in data
        assert data["database"] == "connected"
        assert "vader" in data["models_loaded"]


def test_root_endpoint(client: TestClient) -> None:
    """Verify root index endpoint returns application info and docs links."""
    resp = client.get("/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "name" in data
    assert data["docs_url"] == "/docs"
    assert data["api_v1"] == "/api/v1"


def test_openapi_and_docs_available(client: TestClient) -> None:
    """Verify OpenAPI specification and interactive Swagger docs are complete and accessible."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == status.HTTP_200_OK

    openapi_resp = client.get("/openapi.json")
    assert openapi_resp.status_code == status.HTTP_200_OK
    spec = openapi_resp.json()
    paths = spec["paths"]

    # Verify all expected endpoint paths are documented
    assert "/api/v1/analyze" in paths
    assert "/api/v1/explain" in paths
    assert "/api/v1/topics" in paths
    assert "/api/v1/topics/{id}/headlines" in paths
    assert "/api/v1/topics/{id}/summary" in paths
    assert "/api/v1/topics/{id}/trend" in paths
    assert "/api/v1/models" in paths
    assert "/api/v1/health" in paths


def test_analyze_single_and_batch_headlines(client: TestClient) -> None:
    """Verify POST /api/v1/analyze classifies single and batch headlines with probabilities."""
    # 1. Single headline with default model
    payload = {
        "texts": ["Operating profit rose significantly in quarterly earnings"],
        "models": ["vader"],
    }
    resp = client.post("/api/v1/analyze", json=payload)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["texts_count"] == 1
    assert "vader" in data["models"]
    res1 = data["results"][0]
    assert res1["text"] == payload["texts"][0]
    vader_pred = res1["predictions"]["vader"]
    assert vader_pred["label"] in ("positive", "neutral", "negative")
    assert -1.0 <= vader_pred["score"] <= 1.0
    probs = vader_pred["probabilities"]
    assert round(sum(probs.values()), 2) == 1.0

    # 2. Batch headlines
    batch_payload = {
        "texts": [
            "Tech stocks rally as market confidence improves",
            "Severe losses announced following regulatory sanctions",
            "Routine annual shareholder meeting held as scheduled",
        ],
        "models": ["vader"],
    }
    resp_batch = client.post("/api/v1/analyze", json=batch_payload)
    assert resp_batch.status_code == status.HTTP_200_OK
    batch_data = resp_batch.json()
    assert batch_data["texts_count"] == 3
    assert len(batch_data["results"]) == 3


def test_analyze_validation_errors(client: TestClient) -> None:
    """Verify input validation errors and consistent error envelopes on /analyze."""
    # Empty texts array
    resp = client.post("/api/v1/analyze", json={"texts": []})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert "validation failed" in err["message"].lower()

    # Empty string inside texts array
    resp = client.post("/api/v1/analyze", json={"texts": [""]})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Text exceeding 1000 characters
    long_text = "A" * 1001
    resp = client.post("/api/v1/analyze", json={"texts": [long_text]})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Batch size exceeding 50 items
    many_texts = [f"Headline {i}" for i in range(51)]
    resp = client.post("/api/v1/analyze", json={"texts": many_texts})
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Unknown model name
    resp = client.post(
        "/api/v1/analyze",
        json={"texts": ["Valid text"], "models": ["invalid_model_xyz"]},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    err = resp.json()["error"]
    assert err["code"] == "BAD_REQUEST"
    assert "Unknown model" in err["message"]


def test_explain_methods(client: TestClient) -> None:
    """Verify POST /api/v1/explain returns token attributions across methods."""
    text = "Operating profit rose to EUR 13 mn with excellent growth"

    for method in ["occlusion", "integrated_gradients", "shap"]:
        payload = {
            "text": text,
            "model": "vader",
            "method": method,
        }
        resp = client.post("/api/v1/explain", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["text"] == text
        assert data["model_name"] == "vader"
        assert data["method"] == method
        assert data["prediction_label"] in ("positive", "neutral", "negative")
        assert len(data["attributions"]) > 0
        for attr in data["attributions"]:
            assert "token" in attr
            assert isinstance(attr["weight"], float)


def test_explain_caching(client: TestClient, test_engine: Engine) -> None:
    """Verify in-memory and database explanation caching behavior."""
    # 1. In-memory caching: same text request returns identical output
    payload = {
        "text": "European markets advance on strong retail earnings",
        "model": "vader",
        "method": "occlusion",
    }
    resp1 = client.post("/api/v1/explain", json=payload)
    resp2 = client.post("/api/v1/explain", json=payload)
    assert resp1.status_code == status.HTTP_200_OK
    assert resp2.status_code == status.HTTP_200_OK
    assert resp1.json() == resp2.json()

    # 2. Database caching with article_id
    with Session(test_engine) as session:
        art = Article(
            title="Clean energy investments jump 40% globally",
            normalized_title="clean energy investments jump 40% globally",
            url="https://news.example.com/clean-energy-40",
            topic="climate",
            provider="rss",
        )
        session.add(art)
        session.commit()
        art_id = art.id

    db_payload = {
        "text": "Clean energy investments jump 40% globally",
        "model": "vader",
        "method": "occlusion",
        "article_id": art_id,
    }
    resp_db1 = client.post("/api/v1/explain", json=db_payload)
    assert resp_db1.status_code == status.HTTP_200_OK
    resp_db2 = client.post("/api/v1/explain", json=db_payload)
    assert resp_db2.status_code == status.HTTP_200_OK
    assert resp_db1.json() == resp_db2.json()


def test_explain_validation_errors(client: TestClient) -> None:
    """Verify validation and bad request errors for /explain."""
    # Invalid explanation method
    resp = client.post(
        "/api/v1/explain",
        json={"text": "Profits rose", "model": "vader", "method": "invalid_method"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["error"]["code"] == "BAD_REQUEST"

    # Invalid model
    resp = client.post(
        "/api/v1/explain",
        json={"text": "Profits rose", "model": "invalid_model", "method": "occlusion"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # Empty text string
    resp = client.post(
        "/api/v1/explain",
        json={"text": "", "model": "vader", "method": "occlusion"},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_topics_crud_and_listing(client: TestClient) -> None:
    """Verify GET /api/v1/topics and POST /api/v1/topics lifecycle."""
    # Initial list
    resp = client.get("/api/v1/topics")
    assert resp.status_code == status.HTTP_200_OK
    initial_total = resp.json()["total"]

    # Create new topic
    new_topic = {
        "name": "semiconductors",
        "query": "chips OR foundry OR TSMC OR Nvidia",
        "is_active": True,
    }
    create_resp = client.post("/api/v1/topics", json=new_topic)
    assert create_resp.status_code == status.HTTP_201_CREATED
    topic_data = create_resp.json()
    assert topic_data["name"] == "semiconductors"
    assert topic_data["query"] == new_topic["query"]
    assert topic_data["is_active"] is True
    assert topic_data["id"] is not None

    # List again, verify total increased
    list_resp = client.get("/api/v1/topics")
    assert list_resp.status_code == status.HTTP_200_OK
    assert list_resp.json()["total"] == initial_total + 1

    # Idempotent re-creation
    re_create = client.post("/api/v1/topics", json=new_topic)
    assert re_create.status_code == status.HTTP_201_CREATED

    # Validation error on empty name
    bad_resp = client.post("/api/v1/topics", json={"name": "", "query": "test"})
    assert bad_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_topic_headlines_pagination_and_filters(
    client: TestClient,
    test_engine: Engine,
) -> None:
    """Verify GET /api/v1/topics/{id}/headlines with pagination, dates, source, label, and model."""
    # 404 on nonexistent topic
    resp_404 = client.get("/api/v1/topics/99999/headlines")
    assert resp_404.status_code == status.HTTP_404_NOT_FOUND
    assert resp_404.json()["error"]["code"] == "NOT_FOUND"

    # Seed topic, articles, and predictions
    with Session(test_engine) as session:
        topic = Topic(name="crypto", query="bitcoin crypto ethereum", is_active=True)
        session.add(topic)
        session.flush()

        a1 = Article(
            title="Bitcoin surges past new record high",
            normalized_title="bitcoin surges past new record high",
            url="https://crypto.test/btc-rally",
            outlet="CoinDesk",
            topic="crypto",
            provider="rss",
            published_at=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        )
        a2 = Article(
            title="Regulatory crackdown triggers sharp crypto selloff",
            normalized_title="regulatory crackdown triggers sharp crypto selloff",
            url="https://crypto.test/btc-crash",
            outlet="Bloomberg",
            topic="crypto",
            provider="gdelt",
            published_at=datetime(2026, 10, 2, 12, 0, tzinfo=UTC),
        )
        session.add_all([a1, a2])
        session.flush()

        p1 = Prediction(
            article_id=a1.id,
            model_name="vader",
            model_version="3.3.2",
            label="positive",
            score=0.65,
            probabilities={"positive": 0.8, "neutral": 0.2, "negative": 0.0},
        )
        p2 = Prediction(
            article_id=a2.id,
            model_name="vader",
            model_version="3.3.2",
            label="negative",
            score=-0.70,
            probabilities={"positive": 0.0, "neutral": 0.2, "negative": 0.8},
        )
        session.add_all([p1, p2])
        session.commit()
        t_id = topic.id

    # 1. Fetch all headlines
    res = client.get(f"/api/v1/topics/{t_id}/headlines")
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # 2. Filter by source
    res_src = client.get(f"/api/v1/topics/{t_id}/headlines?source=CoinDesk")
    assert res_src.status_code == status.HTTP_200_OK
    assert res_src.json()["total"] == 1
    assert res_src.json()["items"][0]["outlet"] == "CoinDesk"

    # 3. Filter by label
    res_label = client.get(f"/api/v1/topics/{t_id}/headlines?label=positive")
    assert res_label.status_code == status.HTTP_200_OK
    assert res_label.json()["total"] == 1
    assert res_label.json()["items"][0]["title"] == "Bitcoin surges past new record high"

    # 4. Filter by model
    res_model = client.get(f"/api/v1/topics/{t_id}/headlines?model=vader")
    assert res_model.status_code == status.HTTP_200_OK
    assert res_model.json()["total"] == 2

    # 5. Invalid pagination parameters
    res_bad = client.get(f"/api/v1/topics/{t_id}/headlines?page=0")
    assert res_bad.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_topic_summary(client: TestClient, test_engine: Engine) -> None:
    """Verify GET /api/v1/topics/{id}/summary calculates distribution and average score."""
    # 404 for missing topic
    assert client.get("/api/v1/topics/99999/summary").status_code == status.HTTP_404_NOT_FOUND

    with Session(test_engine) as session:
        topic = Topic(name="macro", query="macro inflation", is_active=True)
        session.add(topic)
        session.flush()

        a1 = Article(
            title="Inflation cools significantly",
            normalized_title="inflation cools significantly",
            url="https://news.test/macro-pos",
            topic="macro",
            provider="rss",
            published_at=datetime(2026, 10, 5, 8, 0, tzinfo=UTC),
        )
        session.add(a1)
        session.flush()

        p1 = Prediction(
            article_id=a1.id,
            model_name="vader",
            model_version="3.3.2",
            label="positive",
            score=0.50,
            probabilities={"positive": 0.7, "neutral": 0.3, "negative": 0.0},
        )
        session.add(p1)
        session.commit()
        t_id = topic.id

    resp = client.get(f"/api/v1/topics/{t_id}/summary?model=vader")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["topic_id"] == t_id
    assert data["total_headlines"] == 1
    assert data["sentiment_distribution"]["positive"] == 1
    assert data["sentiment_percentages"]["positive"] == 100.0
    assert data["average_score"] == 0.50


def test_topic_trend(client: TestClient, test_engine: Engine) -> None:
    """Verify GET /api/v1/topics/{id}/trend returns daily time-series."""
    # 404 for missing topic
    assert client.get("/api/v1/topics/99999/trend").status_code == status.HTTP_404_NOT_FOUND

    with Session(test_engine) as session:
        topic = Topic(name="defense", query="defense military", is_active=True)
        session.add(topic)
        session.flush()

        art = Article(
            title="Defense spending bill signed",
            normalized_title="defense spending bill signed",
            url="https://news.test/defense-bill",
            topic="defense",
            provider="rss",
            published_at=datetime(2026, 10, 6, 9, 0, tzinfo=UTC),
        )
        session.add(art)
        session.flush()

        p = Prediction(
            article_id=art.id,
            model_name="vader",
            model_version="3.3.2",
            label="neutral",
            score=0.0,
            probabilities={"positive": 0.1, "neutral": 0.8, "negative": 0.1},
        )
        session.add(p)
        session.commit()
        t_id = topic.id

    resp = client.get(f"/api/v1/topics/{t_id}/trend?model=vader")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["topic_id"] == t_id
    assert len(data["time_series"]) == 1
    day = data["time_series"][0]
    assert day["date"] == "2026-10-06"
    assert day["headline_volume"] == 1
    assert day["neutral_count"] == 1


def test_models_registry_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/models returns registered models, domains, and metrics."""
    resp = client.get("/api/v1/models")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] >= 1
    model_names = [m["name"] for m in data["models"]]
    assert "vader" in model_names

    vader_meta = next(m for m in data["models"] if m["name"] == "vader")
    assert vader_meta["version"] is not None
    assert "vader" in vader_meta["domain"].lower()
    assert vader_meta["is_contaminated"] is False


def test_rate_limiter_exceeded() -> None:
    """Verify rate limiter blocks requests exceeding the requests_per_minute limit."""
    limiter = SimpleRateLimiter(requests_per_minute=2, enabled=True)
    settings = Settings(environment="testing", api_rate_limit_per_minute=2)
    app = create_app(settings=settings)
    app.dependency_overrides[get_rate_limiter] = lambda: limiter

    with TestClient(app) as test_client:
        # Request 1 & 2 succeed
        r1 = test_client.get("/api/v1/models")
        r2 = test_client.get("/api/v1/models")
        assert r1.status_code == status.HTTP_200_OK
        assert r2.status_code == status.HTTP_200_OK

        # Request 3 exceeds limit
        r3 = test_client.get("/api/v1/models")
        assert r3.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = r3.json()
        assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in r3.headers

    limiter.reset()


def test_consistent_error_envelope_on_404(client: TestClient) -> None:
    """Verify undefined routes return the standard ErrorResponse envelope."""
    resp = client.get("/api/v1/nonexistent_path")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]
