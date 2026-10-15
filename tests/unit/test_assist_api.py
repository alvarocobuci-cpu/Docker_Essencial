import os
from types import SimpleNamespace
from unittest.mock import patch

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.urls import resolve
from rest_framework.test import APIRequestFactory, force_authenticate

from aula4api.llm_service import (
    CircuitOpenError,
    LLMConfigurationError,
    LLMInvalidPayloadError,
    LLMProviderError,
    LLMRateLimitError,
    LLMServiceError,
    llm_service,
)
from aula4api.views import assist


pytestmark = pytest.mark.unit


@pytest.fixture
def post_assist():
    factory = APIRequestFactory()

    def make_request(payload):
        request = factory.post(
            "/api/v1/assist",
            payload,
            format="json",
        )
        force_authenticate(
    request,
    user=SimpleNamespace(
        is_authenticated=True,
        pk=1,
    ),
)
        return assist(request)

    return make_request


def test_assist_route_exists():
    assert resolve("/api/v1/assist").url_name == "assist"


def test_assist_valid_payload_returns_answer(post_assist):
    expected = {
        "answer": "Resumo de teste.",
        "meta": {
            "tokens_prompt": 20,
            "tokens_output": 10,
            "latency_ms": 12.0,
            "estimated_cost_usd": 0.001,
        },
    }

    with patch.object(
        llm_service,
        "generate",
        return_value=expected,
    ) as generate:
        response = post_assist({
            "mode": "summarize",
            "logs": "Erro de teste",
        })

    assert response.status_code == 200
    assert response.data == expected
    generate.assert_called_once_with(
        mode="summarize",
        logs="Erro de teste",
        temperature=0.2,
        max_tokens=256,
    )


def test_assist_invalid_mode_returns_400(post_assist):
    with patch.object(llm_service, "generate") as generate:
        response = post_assist({
            "mode": "invalid",
            "logs": "Erro de teste",
        })

    assert response.status_code == 400
    generate.assert_not_called()


def test_assist_invalid_temperature_returns_400(post_assist):
    response = post_assist({
        "mode": "summarize",
        "logs": "Erro de teste",
        "temperature": 1.5,
    })

    assert response.status_code == 400


def test_assist_value_error_returns_400(post_assist):
    with patch.object(
        llm_service,
        "generate",
        side_effect=ValueError("entrada muito grande"),
    ):
        response = post_assist({
            "mode": "summarize",
            "logs": "Erro de teste",
        })

    assert response.status_code == 400


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
def test_assist_maps_service_errors(
    post_assist,
    error_type,
    expected_status,
):
    with patch.object(
        llm_service,
        "generate",
        side_effect=error_type("falha simulada"),
    ):
        response = post_assist({
            "mode": "explain",
            "logs": ["Falha simulada"],
        })

    assert response.status_code == expected_status
    assert "detail" in response.data