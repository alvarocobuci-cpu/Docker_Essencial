from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PedidoCriado(BaseModel):
    event_id: UUID

    event_type: Literal["PedidoCriado"] = "PedidoCriado"

    occurred_at: datetime

    idempotency_key: str = Field(
        min_length=1,
        max_length=255,
    )

    pedido_id: UUID

    item_id: int = Field(gt=0)

    quantidade: int = Field(gt=0)

    preco_unitario: Decimal = Field(ge=0)

    valor_total: Decimal = Field(ge=0)