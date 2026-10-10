from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PedidoCriado(BaseModel):
    event_id: UUID
    event_type: Literal["PedidoCriado"] = "PedidoCriado"
    occurred_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=255)
    pedido_id: UUID
    item_id: int = Field(gt=0)
    quantidade: int = Field(gt=0)
    preco_unitario: Decimal = Field(ge=0)
    valor_total: Decimal = Field(ge=0)


class PagamentoProcessado(BaseModel):
    event_id: UUID
    event_type: Literal["PagamentoProcessado"] = "PagamentoProcessado"
    occurred_at: datetime
    pedido_id: UUID
    pagamento_id: UUID
    valor: Decimal = Field(ge=0)
    status: Literal["APROVADO", "RECUSADO"]
    referencia_simulada: str = Field(min_length=1, max_length=64)


class NotificacaoEnviada(BaseModel):
    event_id: UUID
    event_type: Literal["NotificacaoEnviada"] = "NotificacaoEnviada"
    occurred_at: datetime
    pedido_id: UUID
    pagamento_status: Literal["APROVADO", "RECUSADO"]
    canal: Literal["INTERNO"] = "INTERNO"
    mensagem: str = Field(min_length=1, max_length=2000)


class PagamentoSolicitado(BaseModel):
    event_id: UUID
    event_type: Literal["PagamentoSolicitado"] = "PagamentoSolicitado"
    occurred_at: datetime
    pedido_id: UUID
    valor: Decimal = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=255)
