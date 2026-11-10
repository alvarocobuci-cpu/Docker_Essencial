import os
from types import SimpleNamespace
from unittest.mock import patch

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.urls import resolve
from rest_framework.test import APIRequestFactory, force_authenticate

from aula4api.ask_sql import SQLExecutionError, SQLValidationError
from aula4api.llm_service import (
    CircuitOpenError,
    LLMConfigurationError,
    LLMInvalidPayloadError,
    LLMProviderError,
    LLMRateLimitError,
    LLMServiceError,
)
from aula4api.views import ask_sql


pytestmark = pytest.mark.unit


@pytest.fixture
def post_ask_sql():
    factory = APIRequestFactory()

    def make_request(payload, authenticated=True):
        request = factory.post(
            "/api/v1/ask_sql",
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

        return ask_sql(request)

    return make_request


def test_ask_sql_route_exists():
    assert resolve("/api/v1/ask_sql").url_name == "ask-sql"


def test_ask_sql_valid_payload_returns_result(post_ask_sql):
    expected = {
        "question": "Qual o total vendido?",
        "sql": (
            "SELECT SUM(valor_total) AS total "
            "FROM aula4api_pedido"
        ),
        "columns": ["total"],
        "rows": [{"total": 100.0}],
        "row_count": 1,
        "truncated": False,
        "meta": {"latency_ms": 10.0},
    }

    with patch(
        "aula4api.ask_sql.answer",
        return_value=expected,
    ) as answer:
        response = post_ask_sql({
            "question": "Qual o total vendido?",
        })

    assert response.status_code == 200
    assert response.data == expected
    answer.assert_called_once_with("Qual o total vendido?")


def test_ask_sql_requires_authentication(post_ask_sql):
    response = post_ask_sql(
        {"question": "Qual o total vendido?"},
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
    ],
)
def test_ask_sql_invalid_payload_returns_400(
    post_ask_sql,
    payload,
):
    with patch("aula4api.ask_sql.answer") as answer:
        response = post_ask_sql(payload)

    assert response.status_code == 400
    answer.assert_not_called()


def test_ask_sql_validation_error_returns_400(post_ask_sql):
    with patch(
        "aula4api.ask_sql.answer",
        side_effect=SQLValidationError(
            "Apenas consultas SELECT sao permitidas.",
            sql="DELETE FROM aula4api_item",
        ),
    ):
        response = post_ask_sql({
            "question": "Apague os itens",
        })

    assert response.status_code == 400
    assert response.data["sql"] == "DELETE FROM aula4api_item"
    assert "detail" in response.data


def test_ask_sql_execution_error_returns_422(post_ask_sql):
    with patch(
        "aula4api.ask_sql.answer",
        side_effect=SQLExecutionError(
            "Nao foi possivel executar a consulta gerada.",
            sql="SELECT id FROM aula4api_item",
        ),
    ):
        response = post_ask_sql({
            "question": "Liste os itens",
        })

    assert response.status_code == 422
    assert response.data["sql"] == "SELECT id FROM aula4api_item"


def test_ask_sql_retryable_execution_error_returns_503(
    post_ask_sql,
):
    with patch(
        "aula4api.ask_sql.answer",
        side_effect=SQLExecutionError(
            "Banco indisponivel.",
            sql="SELECT id FROM aula4api_item",
            retryable=True,
        ),
    ):
        response = post_ask_sql({
            "question": "Liste os itens",
        })

    assert response.status_code == 503


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
def test_ask_sql_maps_llm_errors(
    post_ask_sql,
    error_type,
    expected_status,
):
    with patch(
        "aula4api.ask_sql.answer",
        side_effect=error_type("falha simulada"),
    ):
        response = post_ask_sql({
            "question": "Liste os itens",
        })

    assert response.status_code == expected_status
    assert "detail" in response.data


def test_ask_sql_value_error_returns_400(post_ask_sql):
    with patch(
        "aula4api.ask_sql.answer",
        side_effect=ValueError("entrada invalida"),
    ):
        response = post_ask_sql({
            "question": "Liste os itens",
        })

    assert response.status_code == 400
