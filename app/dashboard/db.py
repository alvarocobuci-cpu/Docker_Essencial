from datetime import date, datetime
from typing import Sequence

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import Text

from app.inventory.database import engine


VALID_STATUSES = {"CRIADO", "PAGO", "NOTIFICADO"}

# Somente estes fragmentos fixos podem ser usados no ORDER BY.
# Nunca inserir diretamente nesse ponto texto recebido do usuário.
ORDER_BY_OPTIONS = {
    "created_desc": "p.created_at DESC, p.id DESC",
    "created_asc": "p.created_at ASC, p.id ASC",
    "total_desc": "p.valor_total DESC, p.created_at DESC",
    "total_asc": "p.valor_total ASC, p.created_at DESC",
}


def build_orders_statement(
    start_date: date | datetime,
    end_date_exclusive: date | datetime,
    statuses: Sequence[str] | None = None,
    item_search: str = "",
    order_by: str = "created_desc",
    limit: int = 500,
):
    """Monta consulta de pedidos com bind parameters e ORDER BY permitido."""

    if start_date >= end_date_exclusive:
        raise ValueError("A data inicial precisa ser anterior à data final.")

    if order_by not in ORDER_BY_OPTIONS:
        raise ValueError("Ordenacao nao permitida.")

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("O limite precisa estar entre 1 e 1000.")

    selected_statuses = list(statuses or [])

    if not set(selected_statuses).issubset(VALID_STATUSES):
        raise ValueError("Um ou mais status nao sao permitidos.")

    query = """
        SELECT
            p.id::text AS pedido_id,
            p.created_at,
            p.status,
            i.name AS item_name,
            p.quantidade,
            p.valor_total
        FROM aula4api_pedido AS p
        INNER JOIN aula4api_item AS i ON i.id = p.item_id
        WHERE p.created_at >= :start_date
          AND p.created_at < :end_date_exclusive
    """

    params = {
        "start_date": start_date,
        "end_date_exclusive": end_date_exclusive,
        "limit": limit,
    }

    if selected_statuses:
        query += "\n AND p.status = ANY(:statuses)"
        params["statuses"] = selected_statuses

    if item_search and item_search.strip():
        query += "\n AND i.name ILIKE :item_search"
        params["item_search"] = f"%{item_search.strip()}%"

    # O fragmento é escolhido exclusivamente no dicionário constante acima.
    query += "\n ORDER BY " + ORDER_BY_OPTIONS[order_by]
    query += "\n LIMIT :limit"

    statement = text(query)

    if selected_statuses:
        statement = statement.bindparams(
            bindparam("statuses", type_=ARRAY(Text()))
        )

    return statement, params


def fetch_orders(
    start_date: date | datetime,
    end_date_exclusive: date | datetime,
    statuses: Sequence[str] | None = None,
    item_search: str = "",
    order_by: str = "created_desc",
    limit: int = 500,
) -> list[dict]:
    """Busca pedidos usando exclusivamente parâmetros vinculados."""

    statement, params = build_orders_statement(
        start_date=start_date,
        end_date_exclusive=end_date_exclusive,
        statuses=statuses,
        item_search=item_search,
        order_by=order_by,
        limit=limit,
    )

    with engine.connect() as connection:
        result = connection.execute(statement, params)
        return [dict(row) for row in result.mappings().all()]


def build_inventory_statement(
    search: str = "",
    low_stock_only: bool = False,
    limit: int = 500,
):
    """Monta consulta de estoque sem interpolar valores na instrução SQL."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError("O limite precisa estar entre 1 e 1000.")

    statement = text("""
        SELECT
            id,
            name,
            quantity,
            minimum_quantity,
            CASE
                WHEN quantity <= minimum_quantity THEN TRUE
                ELSE FALSE
            END AS low_stock
        FROM inventory_items
        WHERE (:search = '' OR name ILIKE :search_pattern)
          AND (
              :low_stock_only = FALSE
              OR quantity <= minimum_quantity
          )
        ORDER BY name ASC, id ASC
        LIMIT :limit
    """)

    clean_search = (search or "").strip()

    params = {
        "search": clean_search,
        "search_pattern": f"%{clean_search}%",
        "low_stock_only": bool(low_stock_only),
        "limit": limit,
    }

    return statement, params


def fetch_inventory(
    search: str = "",
    low_stock_only: bool = False,
    limit: int = 500,
) -> list[dict]:
    """Busca itens de estoque com valores passados como parâmetros."""

    statement, params = build_inventory_statement(
        search=search,
        low_stock_only=low_stock_only,
        limit=limit,
    )

    with engine.connect() as connection:
        result = connection.execute(statement, params)
        return [dict(row) for row in result.mappings().all()]