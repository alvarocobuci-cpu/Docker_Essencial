import pytest

from app.dashboard.db import (
    ORDER_BY_OPTIONS,
    build_inventory_statement,
    build_orders_statement,
)


pytestmark = pytest.mark.unit


def test_order_search_uses_bind_parameters():
    attack = "abc' OR '1'='1"

    statement, params = build_orders_statement(
        start_date="2026-01-01",
        end_date_exclusive="2026-01-02",
        item_search=attack,
    )

    sql = str(statement)

    # O texto recebido não deve ser inserido na instrução SQL.
    assert attack not in sql
    assert ":item_search" in sql

    # O conteúdo malicioso fica somente no valor do parâmetro.
    assert params["item_search"] == f"%{attack}%"


def test_inventory_search_uses_bind_parameters():
    attack = "abc' OR '1'='1"

    statement, params = build_inventory_statement(search=attack)

    assert attack not in str(statement)
    assert ":search_pattern" in str(statement)
    assert params["search_pattern"] == f"%{attack}%"


def test_order_by_uses_only_allow_list():
    for option, fragment in ORDER_BY_OPTIONS.items():
        statement, _ = build_orders_statement(
            start_date="2026-01-01",
            end_date_exclusive="2026-01-02",
            order_by=option,
        )

        assert fragment in str(statement)

    with pytest.raises(ValueError, match="Ordenacao"):
        build_orders_statement(
            start_date="2026-01-01",
            end_date_exclusive="2026-01-02",
            order_by="created_desc; DROP TABLE inventory_items",
        )


def test_status_filter_rejects_unrecognized_values():
    with pytest.raises(ValueError, match="status"):
        build_orders_statement(
            start_date="2026-01-01",
            end_date_exclusive="2026-01-02",
            statuses=["CRIADO' OR '1'='1"],
        )


def test_order_query_has_date_range_and_limit_parameters():
    statement, params = build_orders_statement(
        start_date="2026-01-01",
        end_date_exclusive="2026-02-01",
        statuses=["CRIADO", "PAGO"],
        limit=100,
    )

    sql = str(statement)

    assert ":start_date" in sql
    assert ":end_date_exclusive" in sql
    assert ":statuses" in sql
    assert ":limit" in sql

    assert params["statuses"] == ["CRIADO", "PAGO"]
    assert params["limit"] == 100


def test_order_query_rejects_invalid_date_range():
    with pytest.raises(ValueError, match="data inicial"):
        build_orders_statement(
            start_date="2026-02-01",
            end_date_exclusive="2026-01-01",
        )