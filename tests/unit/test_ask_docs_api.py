import os
from types import SimpleNamespace
from unittest.mock import patch

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.cache import cache
from django.urls import resolve
from rest_framework.test import APIRequestFactory, force_authenticate

from aula4api.llm_service import (
    CircuitOpenError,
    LLMConfigurationError,
    LLMInvalidPayloadError,
    LLMProviderError,
    LLMRateLimitError,
    LLMServiceError,
)
from aula4api.rag_index import RAGIndexEmptyError, RAGIndexError
from aula4api.views import ask_docs


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def post_ask_docs():
    factory = APIRequestFactory()

    def make_request(payload, authenticated=True):
        request = factory.post(
            "/api/v1/ask_docs",
            payload,
            format="json",
        )

        if authenticated:
            force_authenticate(
                request,
                user=SimpleNamespace(
                    is_authenticated=True,
                    pk=1,
                ),
            )

        return ask_docs(request)

    return make_request


def test_ask_docs_route_exists():
    assert resolve("/api/v1/ask_docs").url_name == "ask-docs"


def test_ask_docs_valid_payload_returns_result(post_ask_docs):
    expected = {
        "question": "Como subir?",
        "answer": "Use Docker Compose. [README.md#0-10]",
        "sources": [
            {
                "path": "README.md",
                "title": "Docker Essencial",
                "range": "0-10",
                "score": 0.9,
            }
        ],
        "meta": {
            "top_k": 3,
            "min_score": 0.25,
            "retrieved": 1,
            "llm": {},
        },
    }

    with patch(
        "aula4api.rag.answer",
        return_value=expected,
    ) as answer:
        response = post_ask_docs({"question": "Como subir?"})

    assert response.status_code == 200
    assert response.data == expected
    answer.assert_called_once_with(
        question="Como subir?",
        top_k=3,
        min_score=0.25,
    )


def test_ask_docs_requires_authentication(post_ask_docs):
    response = post_ask_docs(
        {"question": "Como subir?"},
        authenticated=False,
    )

    assert response.status_code in (401, 403)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"question": ""},
        {"question": "   "},
        {"question": "x" * 501},
        {"question": "Como subir?", "top_k": 0},
        {"question": "Como subir?", "top_k": 6},
        {"question": "Como subir?", "min_score": -0.1},
        {"question": "Como subir?", "min_score": 1.1},
    ],
)
def test_ask_docs_invalid_payload_returns_400(
    post_ask_docs,
    payload,
):
    with patch("aula4api.rag.answer") as answer:
        response = post_ask_docs(payload)

    assert response.status_code == 400
    answer.assert_not_called()


def test_ask_docs_empty_index_returns_503(post_ask_docs):
    with patch(
        "aula4api.rag.answer",
        side_effect=RAGIndexEmptyError(
            "O indice RAG esta vazio. Execute ingest_docs."
        ),
    ):
        response = post_ask_docs({"question": "Como subir?"})

    assert response.status_code == 503
    assert "ingest_docs" in response.data["detail"]


def test_ask_docs_index_error_returns_503(post_ask_docs):
    with patch(
        "aula4api.rag.answer",
        side_effect=RAGIndexError("indice indisponivel"),
    ):
        response = post_ask_docs({"question": "Como subir?"})

    assert response.status_code == 503
    assert "indice RAG" in response.data["detail"]


@pytest.mark.parametrize(
    "error_type,expected_status",
    [
        (LLMRateLimitError, 429),
        (CircuitOpenError, 503),
        (LLMConfigurationError, 503),
        (LLMProviderError, 502),
        (LLMInvalidPayloadError, 502),
        (LLMServiceError, 502),
    ],
)
def test_ask_docs_maps_llm_errors(
    post_ask_docs,
    error_type,
    expected_status,
):
    with patch(
        "aula4api.rag.answer",
        side_effect=error_type("falha simulada"),
    ):
        response = post_ask_docs({"question": "Como subir?"})

    assert response.status_code == expected_status
    assert "detail" in response.data


def test_ask_docs_value_error_returns_400(post_ask_docs):
    with patch(
        "aula4api.rag.answer",
        side_effect=ValueError("entrada invalida"),
    ):
        response = post_ask_docs({"question": "Como subir?"})

    assert response.status_code == 400
