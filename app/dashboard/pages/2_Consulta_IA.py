import os

import pandas as pd
import streamlit as st

from app.dashboard.ask_sql_client import (
    AskSQLAuthError,
    AskSQLClientError,
    ask_sql,
    obtain_token,
    refresh_access_token,
)


st.set_page_config(
    page_title="Consulta IA",
    layout="wide",
)

st.title("Consulta em linguagem natural")
st.caption(
    "Pergunte em portugues; a IA gera uma consulta SQL somente leitura "
    "e exibe o resultado."
)

EXAMPLE_QUESTIONS = [
    "Quais os 5 ultimos usuarios cadastrados?",
    "Qual foi o total vendido?",
    "Quais pedidos estao pendentes de entrega?",
    "Quais os 5 produtos mais vendidos?",
]

ENV_TOKEN = os.getenv("ASK_SQL_API_TOKEN", "").strip()
ENV_TOKEN_IGNORED_KEY = "ask_sql_env_token_ignored"
ACCESS_TOKEN_KEY = "ask_sql_access_token"
REFRESH_TOKEN_KEY = "ask_sql_refresh_token"
USERNAME_KEY = "ask_sql_username"
RESULT_KEY = "ask_sql_result"
FLASH_KEY = "ask_sql_flash"


def _env_token():
    if st.session_state.get(ENV_TOKEN_IGNORED_KEY):
        return ""

    return ENV_TOKEN


def _clear_session():
    for key in (
        ACCESS_TOKEN_KEY,
        REFRESH_TOKEN_KEY,
        USERNAME_KEY,
        RESULT_KEY,
    ):
        st.session_state.pop(key, None)


def _current_access_token():
    return (
        st.session_state.get(ACCESS_TOKEN_KEY)
        or _env_token()
    )


def _flash(message, kind="error"):
    st.session_state[FLASH_KEY] = (kind, message)


def _authenticate(username, password):
    tokens = obtain_token(username, password)
    st.session_state[ACCESS_TOKEN_KEY] = tokens["access"]
    st.session_state[REFRESH_TOKEN_KEY] = tokens["refresh"]
    st.session_state[USERNAME_KEY] = username


def _refresh_token():
    refresh = st.session_state.get(REFRESH_TOKEN_KEY)

    if not refresh:
        return False

    try:
        access = refresh_access_token(refresh)
    except AskSQLClientError:
        return False

    st.session_state[ACCESS_TOKEN_KEY] = access
    return True


def _run_query(question):
    token = _current_access_token()

    if not token:
        st.error("Faca login para consultar.")
        return

    try:
        result = ask_sql(question, token)
    except AskSQLAuthError:
        if _refresh_token():
            try:
                result = ask_sql(
                    question,
                    _current_access_token(),
                )
            except AskSQLAuthError:
                _clear_session()
                _flash(
                    "Sessao expirada. Faca login novamente.",
                )
                st.rerun()
                return
            except AskSQLClientError as exc:
                st.error(str(exc))
                return
        else:
            if _env_token():
                st.session_state[ENV_TOKEN_IGNORED_KEY] = True
                _flash(
                    "Token do ambiente expirado. Faca login novamente.",
                )
                st.rerun()
                return

            _clear_session()
            _flash("Sessao expirada. Faca login novamente.")
            st.rerun()
            return
    except AskSQLClientError as exc:
        st.error(str(exc))
        return

    st.session_state[RESULT_KEY] = result


flash = st.session_state.pop(FLASH_KEY, None)

if flash:
    kind, message = flash
    getattr(st, kind)(message)


with st.sidebar:
    st.header("Acesso a API")

    if _env_token():
        st.success("Autenticado via ASK_SQL_API_TOKEN.")

        if st.button(
            "Usar login manual",
            use_container_width=True,
        ):
            st.session_state[ENV_TOKEN_IGNORED_KEY] = True
            st.rerun()
    elif st.session_state.get(ACCESS_TOKEN_KEY):
        username = st.session_state.get(
            USERNAME_KEY,
            "usuario",
        )
        st.success(f"Autenticado como {username}.")

        if st.button("Sair", use_container_width=True):
            _clear_session()
            st.rerun()
    else:
        with st.form("ask_sql_login"):
            username = st.text_input("Usuario")
            password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")

        if submitted:
            if not username.strip() or not password:
                st.warning("Informe usuario e senha.")
            else:
                try:
                    _authenticate(username.strip(), password)
                    st.rerun()
                except AskSQLClientError as exc:
                    st.error(str(exc))

        if ENV_TOKEN and st.session_state.get(
            ENV_TOKEN_IGNORED_KEY
        ):
            if st.button(
                "Usar token do ambiente",
                use_container_width=True,
            ):
                st.session_state.pop(
                    ENV_TOKEN_IGNORED_KEY,
                    None,
                )
                st.rerun()

    st.divider()
    st.caption(
        "A consulta e executada em transacao somente leitura, "
        "com limite de linhas e tempo."
    )


with st.expander("Exemplos de perguntas"):
    for example in EXAMPLE_QUESTIONS:
        st.markdown(f"- {example}")


with st.form("ask_sql_form"):
    question = st.text_area(
        "Pergunta",
        placeholder="Ex.: Quais os 5 ultimos usuarios cadastrados?",
        height=100,
    )
    submitted = st.form_submit_button("Consultar")

if submitted:
    if not question.strip():
        st.warning("Digite uma pergunta.")
    elif not _current_access_token():
        st.error("Faca login para consultar.")
    else:
        with st.spinner("Gerando e executando a consulta..."):
            _run_query(question.strip())


result = st.session_state.get(RESULT_KEY)

if result:
    st.subheader("SQL gerado")
    st.code(result.get("sql", ""), language="sql")

    columns = result.get("columns", [])
    rows = result.get("rows", [])

    st.subheader("Resultado")

    if rows:
        dataframe = pd.DataFrame(rows, columns=columns)
        st.dataframe(
            dataframe,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("A consulta nao retornou linhas.")

    first, second, third = st.columns(3)
    first.metric("Linhas", result.get("row_count", 0))
    second.metric(
        "Truncado",
        "Sim" if result.get("truncated") else "Nao",
    )
    meta = result.get("meta", {})
    third.metric(
        "Latencia da IA",
        f"{float(meta.get('latency_ms', 0.0)):.0f} ms",
    )

    with st.expander("Metadados da chamada"):
        st.json(meta)
