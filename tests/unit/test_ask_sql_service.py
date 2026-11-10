import datetime as dt
import decimal
import uuid

import pytest

from aula4api.ask_sql import (
    SCHEMA_CONTEXT,
    SQLValidationError,
    _unique_columns,
    extract_sql,
    serialize_value,
    validate_sql,
)


pytestmark = pytest.mark.unit


def test_schema_context_lists_tables_without_sensitive_columns():
    assert "aula4api_pedido" in SCHEMA_CONTEXT
    assert "aula4api_pagamento" in SCHEMA_CONTEXT
    assert "auth_user" in SCHEMA_CONTEXT
    assert "password" not in SCHEMA_CONTEXT.lower()
    assert "idempotency_key" not in SCHEMA_CONTEXT.lower()
    assert "mensagem" not in SCHEMA_CONTEXT.lower()


def test_extract_sql_removes_fences_and_trailing_semicolon():
    raw = "```sql\nSELECT id FROM aula4api_item LIMIT 5;\n```"

    assert extract_sql(raw) == (
        "SELECT id FROM aula4api_item LIMIT 5"
    )


def test_extract_sql_removes_plain_fences():
    raw = "```\nSELECT id FROM aula4api_item LIMIT 5\n```"

    assert extract_sql(raw) == (
        "SELECT id FROM aula4api_item LIMIT 5"
    )


def test_extract_sql_handles_prose_prefix():
    raw = (
        "Aqui esta a consulta: "
        "SELECT id FROM aula4api_item LIMIT 5"
    )

    assert extract_sql(raw) == (
        "SELECT id FROM aula4api_item LIMIT 5"
    )


def test_extract_sql_rejects_empty_answer():
    with pytest.raises(SQLValidationError):
        extract_sql("   ")


def test_validate_sql_accepts_select_and_cte():
    assert validate_sql(
        "SELECT id, name FROM aula4api_item LIMIT 10"
    ).startswith("SELECT")

    cte = (
        "WITH totals AS ("
        "SELECT item_id, SUM(valor_total) AS total "
        "FROM aula4api_pedido GROUP BY item_id"
        ") "
        "SELECT item_id, total FROM totals "
        "ORDER BY total DESC LIMIT 5"
    )

    assert validate_sql(cte).startswith("WITH")


def test_validate_sql_accepts_count_star():
    assert validate_sql(
        "SELECT COUNT(*) AS total FROM aula4api_pedido"
    )


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO aula4api_item (name) VALUES ('x')",
        "UPDATE aula4api_item SET name = 'x'",
        "DELETE FROM aula4api_item",
        "DROP TABLE aula4api_item",
        "ALTER TABLE aula4api_item ADD COLUMN x TEXT",
        "TRUNCATE aula4api_item",
        "CREATE TABLE x (id INT)",
        "SELECT 1; DROP TABLE aula4api_item",
        "SELECT * FROM aula4api_item",
        "SELECT DISTINCT * FROM aula4api_item",
        "SELECT ALL * FROM aula4api_item",
        "SELECT item.* FROM aula4api_item item",
        "SELECT password FROM auth_user",
        "SELECT email FROM auth_user",
        "SELECT idempotency_key FROM aula4api_pedido",
        "SELECT mensagem FROM aula4api_notificacao",
        "SELECT table_name FROM pg_catalog.pg_tables",
        "SELECT table_name FROM information_schema.tables",
        "SELECT id FROM aula4api_item -- comentario",
        "SELECT id INTO nova_tabela FROM aula4api_item",
        "SELECT id FROM aula4api_item FOR UPDATE",
    ],
)
def test_validate_sql_rejects_unsafe_queries(sql):
    with pytest.raises(SQLValidationError):
        validate_sql(sql)


def test_validate_sql_rejects_unknown_table():
    with pytest.raises(SQLValidationError):
        validate_sql(
            "SELECT id FROM tabela_desconhecida"
        )


def test_serialize_value_handles_common_types():
    identifier = uuid.uuid4()

    assert serialize_value(None) is None
    assert serialize_value(decimal.Decimal("10.50")) == 10.5
    assert serialize_value(identifier) == str(identifier)
    assert serialize_value(dt.date(2026, 1, 2)) == "2026-01-02"
    assert serialize_value(
        dt.datetime(2026, 1, 2, 3, 4, 5)
    ) == "2026-01-02T03:04:05"
    assert serialize_value(
        [decimal.Decimal("1.5")]
    ) == [1.5]


def test_unique_columns_handles_duplicates():
    assert _unique_columns(["id", "id", "name"]) == [
        "id",
        "id_2",
        "name",
    ]
