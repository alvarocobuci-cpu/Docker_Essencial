import os

import httpx


DEFAULT_API_BASE_URL = "http://api:8000"
DEFAULT_TIMEOUT_SECONDS = 30.0


class AskSQLClientError(Exception):
    pass


class AskSQLAuthError(AskSQLClientError):
    pass


def _base_url():
    return os.getenv(
        "API_BASE_URL",
        DEFAULT_API_BASE_URL,
    ).rstrip("/")


def _request(method, path, client=None, **kwargs):
    if client is not None:
        return client.request(method, path, **kwargs)

    with httpx.Client(
        base_url=_base_url(),
        timeout=DEFAULT_TIMEOUT_SECONDS,
    ) as http:
        return http.request(method, path, **kwargs)


def _detail(response):
    try:
        payload = response.json()
    except ValueError:
        return "A API retornou uma resposta invalida."

    if not isinstance(payload, dict):
        return "A API retornou uma resposta invalida."

    detail = payload.get("detail")

    if isinstance(detail, str) and detail.strip():
        return detail.strip()

    if isinstance(detail, list) and detail:
        return str(detail[0])

    errors = payload.get("question")

    if isinstance(errors, list) and errors:
        return str(errors[0])

    if isinstance(errors, str) and errors.strip():
        return errors.strip()

    return "A API retornou uma resposta invalida."


def obtain_token(username, password, client=None):
    try:
        response = _request(
            "POST",
            "/api/token/",
            client=client,
            json={"username": username, "password": password},
        )
    except httpx.HTTPError as exc:
        raise AskSQLClientError(
            "Nao foi possivel conectar a API."
        ) from exc

    if response.status_code == 401:
        raise AskSQLAuthError("Usuario ou senha invalidos.")

    if response.status_code >= 400:
        raise AskSQLClientError(_detail(response))

    payload = response.json()
    access = payload.get("access")
    refresh = payload.get("refresh")

    if not access or not refresh:
        raise AskSQLClientError(
            "A API nao retornou os tokens esperados."
        )

    return {"access": access, "refresh": refresh}


def refresh_access_token(refresh_token, client=None):
    try:
        response = _request(
            "POST",
            "/api/token/refresh/",
            client=client,
            json={"refresh": refresh_token},
        )
    except httpx.HTTPError as exc:
        raise AskSQLClientError(
            "Nao foi possivel conectar a API."
        ) from exc

    if response.status_code >= 400:
        raise AskSQLAuthError(
            "Sessao expirada. Faca login novamente."
        )

    payload = response.json()
    access = payload.get("access")

    if not access:
        raise AskSQLClientError(
            "A API nao retornou o token de acesso."
        )

    return access


def ask_sql(question, access_token, client=None):
    try:
        response = _request(
            "POST",
            "/api/v1/ask_sql",
            client=client,
            json={"question": question},
            headers={"Authorization": f"Bearer {access_token}"},
        )
    except httpx.HTTPError as exc:
        raise AskSQLClientError(
            "Nao foi possivel conectar a API."
        ) from exc

    if response.status_code == 401:
        raise AskSQLAuthError(
            "Sessao expirada. Faca login novamente."
        )

    if response.status_code >= 400:
        raise AskSQLClientError(_detail(response))

    return response.json()
