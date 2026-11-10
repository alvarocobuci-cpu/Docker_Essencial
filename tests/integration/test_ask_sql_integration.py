import pytest

from aula4api.ask_sql import (
    SQLExecutionError,
    execute_readonly_query,
    validate_sql,
)


pytestmark = pytest.mark.integration


def test_execute_readonly_query_against_postgres():
    sql = validate_sql(
        "SELECT COUNT(*) AS total FROM aula4api_pedido"
    )

    columns, rows, truncated = execute_readonly_query(sql)

    assert columns == ["total"]
    assert len(rows) == 1
    assert isinstance(rows[0]["total"], int)
    assert truncated is False


def test_execute_readonly_query_blocks_writes():
    with pytest.raises(SQLExecutionError):
        execute_readonly_query("DELETE FROM aula4api_item")
