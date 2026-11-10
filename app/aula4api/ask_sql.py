import base64
import datetime as dt
import decimal
import logging
import os
import re
import uuid

import sqlparse
from django.db import DatabaseError, OperationalError, connection, transaction

from .llm_service import llm_service


logger = logging.getLogger(__name__)


def _env_int(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)

    return min(maximum, max(minimum, value))


MAX_ROWS = _env_int("ASK_SQL_MAX_ROWS", 200, 1, 1000)
STATEMENT_TIMEOUT_MS = _env_int(
    "ASK_SQL_STATEMENT_TIMEOUT_MS",
    5000,
    100,
    30000,
)


SCHEMA_CONTEXT = """TABELAS DISPONIVEIS (PostgreSQL):
- aula4api_category(id BIGINT PK, name VARCHAR(100) UNIQUE NOT NULL)
- aula4api_item(id BIGINT PK, name VARCHAR(150) NOT NULL, description TEXT, price NUMERIC(10,2) NOT NULL, quantity INTEGER NOT NULL, category_id BIGINT FK -> aula4api_category.id)
- aula4api_pedido(id UUID PK, item_id BIGINT FK -> aula4api_item.id, quantidade INTEGER NOT NULL, preco_unitario NUMERIC(10,2) NOT NULL, valor_total NUMERIC(12,2) NOT NULL, status VARCHAR(20) NOT NULL, created_at TIMESTAMPTZ NOT NULL)
- aula4api_pagamento(id UUID PK, pedido_id UUID UNIQUE FK -> aula4api_pedido.id, valor NUMERIC(12,2) NOT NULL, status VARCHAR(20) NOT NULL, referencia_simulada VARCHAR(64) NOT NULL, created_at TIMESTAMPTZ NOT NULL)
- aula4api_notificacao(id UUID PK, pedido_id UUID UNIQUE FK -> aula4api_pedido.id, canal VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL, created_at TIMESTAMPTZ NOT NULL)
- auth_user(id INTEGER PK, username VARCHAR(150) UNIQUE NOT NULL, date_joined TIMESTAMPTZ NOT NULL, is_active BOOLEAN NOT NULL)

REGRAS DE NEGOCIO:
- aula4api_pedido.status: CRIADO (pedido criado), PAGO (pagamento aprovado), NOTIFICADO (cliente notificado; entrega concluida).
- "pedidos pendentes de entrega" = status diferente de 'NOTIFICADO'.
- aula4api_pagamento.status: APROVADO ou RECUSADO.
- aula4api_pedido.valor_total = quantidade * preco_unitario.
- auth_user.date_joined e a data de cadastro do usuario.
- Nao existe tabela de enderecos de entrega; use o status do pedido para situacao de entrega.
- Nao existem colunas de email, nome, senha ou chaves de idempotencia disponiveis para consulta."""


ALLOWED_SCHEMAS = frozenset({"public"})
ALLOWED_TABLES = frozenset(
    {
        "aula4api_category",
        "aula4api_item",
        "aula4api_pedido",
        "aula4api_pagamento",
        "aula4api_notificacao",
        "auth_user",
    }
)

FORBIDDEN_KEYWORDS = frozenset(
    {
        "ABORT",
        "ALTER",
        "ANALYZE",
        "BEGIN",
        "CALL",
        "CHECKPOINT",
        "CLOSE",
        "CLUSTER",
        "COMMENT",
        "COMMIT",
        "COPY",
        "CREATE",
        "DATABASE",
        "DEALLOCATE",
        "DECLARE",
        "DELETE",
        "DISCARD",
        "DO",
        "DROP",
        "EXECUTE",
        "EXPLAIN",
        "EXTENSION",
        "FETCH",
        "FOREIGN",
        "FUNCTION",
        "GRANT",
        "IMPORT",
        "INSERT",
        "INTO",
        "LISTEN",
        "LOAD",
        "LOCK",
        "MERGE",
        "MOVE",
        "NOTIFY",
        "OWNER",
        "POLICY",
        "PREPARE",
        "PROCEDURE",
        "PUBLICATION",
        "REASSIGN",
        "REFRESH",
        "REINDEX",
        "RELEASE",
        "RESET",
        "REVOKE",
        "ROLE",
        "ROLLBACK",
        "RULE",
        "SAVEPOINT",
        "SCHEMA",
        "SECURITY",
        "SERVER",
        "SET",
        "SHOW",
        "START",
        "SUBSCRIPTION",
        "TABLESPACE",
        "TEMP",
        "TEMPORARY",
        "TRIGGER",
        "TRUNCATE",
        "UNLISTEN",
        "UNLOGGED",
        "UPDATE",
        "USER",
        "VACUUM",
    }
)

FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "access_token",
        "alembic_version",
        "api_key",
        "apikey",
        "authtoken_token",
        "client_secret",
        "django_admin_log",
        "django_migrations",
        "django_session",
        "email",
        "first_name",
        "idempotency_key",
        "information_schema",
        "last_name",
        "mensagem",
        "password",
        "pg_authid",
        "pg_shadow",
        "private_key",
        "refresh_token",
        "secret",
        "session_data",
        "session_key",
        "token",
    }
)

_FENCE_RE = re.compile(
    r"```(?:sql)?\s*(.*?)```",
    re.IGNORECASE | re.DOTALL,
)
_LABEL_RE = re.compile(
    r"^(?:sql|query|consulta)\s*:\s*",
    re.IGNORECASE,
)
_SELECT_START_RE = re.compile(
    r"\b(select|with)\b",
    re.IGNORECASE,
)
_STAR_SELECT_RE = re.compile(
    r"(?is)\bselect\s+(?:(?:distinct|all)\s+)?\*",
)
_STAR_QUALIFIED_RE = re.compile(
    r"(?is)\b\w+\.\*",
)
_STAR_COMMA_RE = re.compile(
    r"(?is),\s*\*",
)
_TABLE_REF_RE = re.compile(
    r"(?i)\b(?:from|join)\s+"
    r"(?:\"([a-z_][a-z0-9_]*)\"\.)?"
    r"\"?([a-z_][a-z0-9_]*)\"?",
)
_CTE_RE = re.compile(
    r"(?is)(?:\bwith\b|,)\s*(?:recursive\s+)?"
    r"([a-z_][a-z0-9_]*)\s*(?:\([^)]*\))?\s+as\s+"
    r"(?:materialized\s+|not\s+materialized\s+)?\(",
)


class SQLValidationError(ValueError):
    def __init__(self, message, sql=None):
        super().__init__(message)
        self.sql = sql


class SQLExecutionError(Exception):
    def __init__(self, message, sql=None, retryable=False):
        super().__init__(message)
        self.sql = sql
        self.retryable = retryable


def extract_sql(raw_answer):
    if not isinstance(raw_answer, str) or not raw_answer.strip():
        raise SQLValidationError(
            "A LLM nao retornou uma consulta SQL.",
            sql=raw_answer if isinstance(raw_answer, str) else None,
        )

    text = raw_answer.strip()
    fenced = _FENCE_RE.search(text)

    if fenced:
        text = fenced.group(1).strip()

    text = _LABEL_RE.sub("", text).strip()
    start = _SELECT_START_RE.search(text)

    if start:
        text = text[start.start():].strip()

    if text.endswith(";"):
        text = text[:-1].strip()

    if not text:
        raise SQLValidationError(
            "A LLM nao retornou uma consulta SQL.",
            sql=raw_answer,
        )

    return text


def _first_keyword(statement):
    for token in statement.flatten():
        if token.is_whitespace:
            continue

        if token.ttype in sqlparse.tokens.Comment:
            continue

        if (
            token.ttype in sqlparse.tokens.Punctuation
            and token.value == "("
        ):
            continue

        if token.ttype in sqlparse.tokens.Keyword:
            return token.normalized.upper()

        return None

    return None


def _sanitize_for_checks(statement):
    parts = []

    for token in statement.flatten():
        if token.ttype in sqlparse.tokens.Comment:
            continue

        if (
            token.ttype in sqlparse.tokens.Literal.String
            and token.ttype not in sqlparse.tokens.Literal.String.Symbol
        ):
            parts.append(" '' ")
            continue

        parts.append(token.value)

    return "".join(parts)


def _extract_cte_names(sql):
    return {
        match.group(1).lower()
        for match in _CTE_RE.finditer(sql)
    }


def validate_sql(sql):
    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError(
            "A consulta SQL esta vazia.",
            sql=sql,
        )

    statements = [
        statement
        for statement in sqlparse.split(sql)
        if statement.strip()
    ]

    if len(statements) != 1:
        raise SQLValidationError(
            "Apenas uma instrucao SQL e permitida.",
            sql=sql,
        )

    statement = sqlparse.parse(statements[0])[0]

    if _first_keyword(statement) not in {"SELECT", "WITH"}:
        raise SQLValidationError(
            "Apenas consultas SELECT sao permitidas.",
            sql=sql,
        )

    for token in statement.flatten():
        if token.ttype in sqlparse.tokens.Comment:
            raise SQLValidationError(
                "Comentarios nao sao permitidos.",
                sql=sql,
            )

        if (
            token.ttype in sqlparse.tokens.Literal.String
            and token.ttype not in sqlparse.tokens.Literal.String.Symbol
        ):
            continue

        if token.ttype in sqlparse.tokens.Keyword:
            keyword = token.normalized.upper()

            if keyword in FORBIDDEN_KEYWORDS:
                raise SQLValidationError(
                    f"O comando {keyword} nao e permitido.",
                    sql=sql,
                )

        if (
            token.ttype in sqlparse.tokens.Name
            or token.ttype in sqlparse.tokens.Literal.String.Symbol
        ):
            identifier = token.value.strip('"').lower()

            if (
                identifier in FORBIDDEN_IDENTIFIERS
                or identifier.startswith("pg_")
            ):
                raise SQLValidationError(
                    f"A coluna ou tabela {identifier} nao esta disponivel.",
                    sql=sql,
                )

    sanitized = _sanitize_for_checks(statement)

    if (
        _STAR_SELECT_RE.search(sanitized)
        or _STAR_QUALIFIED_RE.search(sanitized)
        or _STAR_COMMA_RE.search(sanitized)
    ):
        raise SQLValidationError(
            "Use colunas explicitas em vez de SELECT *.",
            sql=sql,
        )

    allowed_tables = ALLOWED_TABLES | _extract_cte_names(sanitized)

    for match in _TABLE_REF_RE.finditer(sanitized):
        schema_name = (match.group(1) or "").lower()
        table_name = (match.group(2) or "").lower()

        if schema_name and schema_name not in ALLOWED_SCHEMAS:
            raise SQLValidationError(
                f"O schema {schema_name} nao esta disponivel.",
                sql=sql,
            )

        if table_name not in allowed_tables:
            raise SQLValidationError(
                f"A tabela {table_name} nao esta disponivel.",
                sql=sql,
            )

    return statements[0].strip().rstrip(";").strip()


def serialize_value(value):
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float, str)):
        return value

    if isinstance(value, decimal.Decimal):
        return float(value)

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()

    if isinstance(value, dt.timedelta):
        return value.total_seconds()

    if isinstance(value, (bytes, bytearray, memoryview)):
        return base64.b64encode(bytes(value)).decode("ascii")

    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): serialize_value(item)
            for key, item in value.items()
        }

    return str(value)


def _unique_columns(columns):
    seen = {}
    unique = []

    for column in columns:
        base = str(column)
        count = seen.get(base, 0) + 1
        seen[base] = count
        unique.append(base if count == 1 else f"{base}_{count}")

    return unique


def _fetch_rows(cursor, sql, max_rows):
    cursor.execute(sql)

    if cursor.description is None:
        return [], [], False

    columns = _unique_columns(
        [column[0] for column in cursor.description]
    )
    raw_rows = cursor.fetchmany(max_rows + 1)
    truncated = len(raw_rows) > max_rows
    rows = [
        {
            column: serialize_value(value)
            for column, value in zip(columns, row)
        }
        for row in raw_rows[:max_rows]
    ]

    return columns, rows, truncated


def execute_readonly_query(sql, max_rows=None):
    row_limit = MAX_ROWS if max_rows is None else max(
        1,
        min(int(max_rows), MAX_ROWS),
    )

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(
                    "SET LOCAL statement_timeout = "
                    f"{int(STATEMENT_TIMEOUT_MS)}"
                )
                columns, rows, truncated = _fetch_rows(
                    cursor,
                    sql,
                    row_limit,
                )
    except OperationalError as exc:
        logger.warning(
            "ask_sql_execution_failed error_type=%s",
            type(exc).__name__,
        )
        raise SQLExecutionError(
            "O banco de dados esta indisponivel ou a consulta "
            "excedeu o tempo limite.",
            sql=sql,
            retryable=True,
        ) from exc
    except DatabaseError as exc:
        logger.warning(
            "ask_sql_execution_failed error_type=%s",
            type(exc).__name__,
        )
        raise SQLExecutionError(
            "Nao foi possivel executar a consulta gerada.",
            sql=sql,
            retryable=False,
        ) from exc

    return columns, rows, truncated


def answer(question):
    llm_result = llm_service.generate_sql(
        question,
        SCHEMA_CONTEXT,
    )
    sql = validate_sql(extract_sql(llm_result["answer"]))
    columns, rows, truncated = execute_readonly_query(sql)

    return {
        "question": question,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
        "meta": llm_result.get("meta", {}),
    }
