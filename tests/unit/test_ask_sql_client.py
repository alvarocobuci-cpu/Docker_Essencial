import json

import httpx
import pytest

from dashboard.ask_sql_client import (
    AskSQLAuthError,
    AskSQLClientError,
    ask_sql,
    obtain_token,
    refresh_access_token,
)


pytestmark = pytest.mark.unit


def _client(handler):
    return httpx.Client(
        base_url="http://testserver",
        transport=httpx.MockTransport(handler),
    )


def test_obtain_token_returns_tokens():
    def handler(request):
        assert request.url.path == "/api/token/"
        payload = json.loads(request.content)
        assert payload == {
            "username": "ana",
            "password": "secret",
        }
        return httpx.Response(
            200,
            json={"access": "a", "refresh": "r"},
        )

    with _client(handler) as client:
        tokens = obtain_token("ana", "secret", client=client)

    assert tokens == {"access": "a", "refresh": "r"}


def test_obtain_token_invalid_credentials_raises_auth_error():
    def handler(request):
        return httpx.Response(
            401,
            json={"detail": "No active account found"},
        )

    with _client(handler) as client:
        with pytest.raises(AskSQLAuthError):
            obtain_token("ana", "wrong", client=client)


def test_obtain_token_missing_tokens_raises_client_error():
    def handler(request):
        return httpx.Response(200, json={"access": "a"})

    with _client(handler) as client:
        with pytest.raises(AskSQLClientError):
            obtain_token("ana", "secret", client=client)


def test_refresh_access_token_returns_access():
    def handler(request):
        assert request.url.path == "/api/token/refresh/"
        payload = json.loads(request.content)
        assert payload == {"refresh": "r"}
        return httpx.Response(200, json={"access": "new"})

    with _client(handler) as client:
        access = refresh_access_token("r", client=client)

    assert access == "new"


def test_refresh_access_token_invalid_raises_auth_error():
    def handler(request):
        return httpx.Response(
            401,
            json={"detail": "Token is invalid or expired"},
        )

    with _client(handler) as client:
        with pytest.raises(AskSQLAuthError):
            refresh_access_token("r", client=client)


def test_ask_sql_sends_bearer_token_and_returns_payload():
    body = {
        "question": "Qual o total vendido?",
        "sql": "SELECT 1",
        "columns": ["total"],
        "rows": [{"total": 1}],
        "row_count": 1,
        "truncated": False,
        "meta": {},
    }

    def handler(request):
        assert request.url.path == "/api/v1/ask_sql"
        assert request.headers["Authorization"] == "Bearer token"
        payload = json.loads(request.content)
        assert payload == {
            "question": "Qual o total vendido?",
        }
        return httpx.Response(200, json=body)

    with _client(handler) as client:
        result = ask_sql(
            "Qual o total vendido?",
            "token",
            client=client,
        )

    assert result == body


def test_ask_sql_unauthorized_raises_auth_error():
    def handler(request):
        return httpx.Response(
            401,
            json={"detail": "Unauthorized"},
        )

    with _client(handler) as client:
        with pytest.raises(AskSQLAuthError):
            ask_sql("q", "token", client=client)


def test_ask_sql_validation_error_exposes_detail():
    def handler(request):
        return httpx.Response(
            400,
            json={
                "detail": (
                    "Apenas consultas SELECT sao permitidas."
                ),
                "sql": "DELETE FROM aula4api_item",
            },
        )

    with _client(handler) as client:
        with pytest.raises(AskSQLClientError) as excinfo:
            ask_sql("q", "token", client=client)

    assert "Apenas consultas SELECT" in str(excinfo.value)


def test_ask_sql_question_error_exposes_detail():
    def handler(request):
        return httpx.Response(
            400,
            json={
                "question": [
                    "Este campo nao pode ser vazio.",
                ],
            },
        )

    with _client(handler) as client:
        with pytest.raises(AskSQLClientError) as excinfo:
            ask_sql("q", "token", client=client)

    assert "Este campo nao pode ser vazio." in str(
        excinfo.value
    )


def test_ask_sql_connection_error_raises_client_error():
    def handler(request):
        raise httpx.ConnectError(
            "boom",
            request=request,
        )

    with _client(handler) as client:
        with pytest.raises(AskSQLClientError):
            ask_sql("q", "token", client=client)
