import pytest

from aula4api.rag_embeddings import (
    EmbeddingConfigurationError,
    EmbeddingInvalidPayloadError,
    EmbeddingProviderError,
    EmbeddingService,
)


pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def configure(monkeypatch, **overrides):
    values = {
        "EMBEDDING_API_URL": "https://embeddings.invalid/v1/embeddings",
        "EMBEDDING_API_KEY": "embedding-key",
        "EMBEDDING_MODEL": "embedding-model",
        "EMBEDDING_TIMEOUT_SECONDS": "5",
        "EMBEDDING_MAX_RETRIES": "3",
        "EMBEDDING_RETRY_BASE_SECONDS": "0",
        "EMBEDDING_BATCH_SIZE": "32",
    }
    values.update(overrides)

    for name, value in values.items():
        monkeypatch.setenv(name, value)


def embedding_payload(count, dimension=2):
    return {
        "data": [
            {
                "index": index,
                "embedding": [
                    float(index + 1),
                    float(dimension - index),
                ],
            }
            for index in range(count)
        ]
    }


def test_embed_orders_batches_and_returns_vectors(monkeypatch):
    configure(monkeypatch)
    calls = []

    def post(url, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse(200, embedding_payload(2))

    service = EmbeddingService(post=post)
    result = service.embed(["primeiro", "segundo"])

    assert result == [[1.0, 2.0], [2.0, 1.0]]
    assert len(calls) == 1
    assert calls[0]["json"]["input"] == ["primeiro", "segundo"]
    assert calls[0]["headers"]["Authorization"] == "Bearer embedding-key"


def test_embedding_key_falls_back_to_llm_key(monkeypatch):
    configure(monkeypatch, EMBEDDING_API_KEY="")
    monkeypatch.setenv("LLM_API_KEY", "llm-key")

    service = EmbeddingService(post=lambda *args, **kwargs: None)

    assert service.api_key == "llm-key"


def test_missing_embedding_configuration_does_not_call_provider(
    monkeypatch,
):
    configure(monkeypatch, EMBEDDING_API_KEY="")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    called = False

    def post(*args, **kwargs):
        nonlocal called
        called = True

    service = EmbeddingService(post=post)

    with pytest.raises(EmbeddingConfigurationError):
        service.embed(["texto"])

    assert not called


def test_embedding_retries_429_then_succeeds(monkeypatch):
    configure(monkeypatch)
    responses = [
        FakeResponse(429, {"error": "rate limit"}),
        FakeResponse(200, embedding_payload(1)),
    ]
    sleeps = []

    def post(*args, **kwargs):
        return responses.pop(0)

    service = EmbeddingService(
        post=post,
        sleeper=sleeps.append,
        uniform=lambda low, high: 0,
    )

    assert service.embed(["texto"]) == [[1.0, 2.0]]
    assert len(sleeps) == 1


def test_embedding_raises_after_provider_failures(monkeypatch):
    configure(monkeypatch, EMBEDDING_MAX_RETRIES="2")
    sleeps = []

    def post(*args, **kwargs):
        return FakeResponse(500, {"error": "provider"})

    service = EmbeddingService(
        post=post,
        sleeper=sleeps.append,
        uniform=lambda low, high: 0,
    )

    with pytest.raises(EmbeddingProviderError):
        service.embed(["texto"])

    assert len(sleeps) == 1


def test_embedding_rejects_invalid_payload(monkeypatch):
    configure(monkeypatch)

    def post(*args, **kwargs):
        return FakeResponse(200, {"data": []})

    service = EmbeddingService(post=post)

    with pytest.raises(EmbeddingInvalidPayloadError):
        service.embed(["texto"])


def test_embedding_uses_configured_batch_size(monkeypatch):
    configure(monkeypatch, EMBEDDING_BATCH_SIZE="1")
    calls = []

    def post(url, headers, json, timeout):
        calls.append(json["input"])
        return FakeResponse(200, embedding_payload(1))

    service = EmbeddingService(post=post)
    result = service.embed(["primeiro", "segundo"])

    assert len(calls) == 2
    assert len(result) == 2


def test_embedding_rejects_blank_text(monkeypatch):
    configure(monkeypatch)
    service = EmbeddingService(post=lambda *args, **kwargs: None)

    with pytest.raises(ValueError):
        service.embed([" "])
