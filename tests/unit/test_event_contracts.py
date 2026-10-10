from copy import deepcopy

import pytest
from pydantic import ValidationError

from aula4api.event_contracts import (
    NotificacaoEnviada,
    PagamentoProcessado,
    PagamentoSolicitado,
    PedidoCriado,
)


def order_event():
    return {
        "event_id": "11111111-1111-4111-8111-111111111111",
        "occurred_at": "2025-01-15T12:00:00Z",
        "idempotency_key": "test-key",
        "pedido_id": "22222222-2222-4222-8222-222222222222",
        "item_id": 2,
        "quantidade": 1,
        "preco_unitario": "10.00",
        "valor_total": "10.00",
    }


@pytest.mark.unit
def test_pedido_criado_contract_accepts_valid_event():
    event = PedidoCriado.model_validate(order_event())

    assert event.event_type == "PedidoCriado"
    assert event.item_id == 2
    assert str(event.valor_total) == "10.00"


@pytest.mark.unit
def test_pagamento_solicitado_contract_accepts_valid_event():
    event = PagamentoSolicitado.model_validate({
        "event_id": "11111111-1111-4111-8111-111111111111",
        "occurred_at": "2025-01-15T12:00:00Z",
        "pedido_id": "22222222-2222-4222-8222-222222222222",
        "valor": "10.00",
        "idempotency_key": "test-key",
    })

    assert event.event_type == "PagamentoSolicitado"
    assert str(event.valor) == "10.00"


@pytest.mark.unit
def test_pagamento_processado_contract_accepts_valid_event():
    event = PagamentoProcessado.model_validate({
        "event_id": "11111111-1111-4111-8111-111111111111",
        "occurred_at": "2025-01-15T12:00:00Z",
        "pedido_id": "22222222-2222-4222-8222-222222222222",
        "pagamento_id": "33333333-3333-4333-8333-333333333333",
        "valor": "10.00",
        "status": "APROVADO",
        "referencia_simulada": "SIM-pedido-1",
    })

    assert event.status == "APROVADO"
    assert event.event_type == "PagamentoProcessado"


@pytest.mark.unit
def test_notificacao_enviada_contract_accepts_valid_event():
    event = NotificacaoEnviada.model_validate({
        "event_id": "11111111-1111-4111-8111-111111111111",
        "occurred_at": "2025-01-15T12:00:00Z",
        "pedido_id": "22222222-2222-4222-8222-222222222222",
        "pagamento_status": "APROVADO",
        "canal": "INTERNO",
        "mensagem": "Pagamento aprovado.",
    })

    assert event.canal == "INTERNO"
    assert event.event_type == "NotificacaoEnviada"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("model", "base", "override"),
    [
        (
            PedidoCriado,
            order_event(),
            {"item_id": 0},
        ),
        (
            PedidoCriado,
            order_event(),
            {"quantidade": 0},
        ),
        (
            PedidoCriado,
            order_event(),
            {"event_type": "EventoDesconhecido"},
        ),
        (
            PagamentoSolicitado,
            {
                "event_id": "11111111-1111-4111-8111-111111111111",
                "occurred_at": "2025-01-15T12:00:00Z",
                "pedido_id": "22222222-2222-4222-8222-222222222222",
                "valor": "10.00",
                "idempotency_key": "test-key",
            },
            {"valor": "-1.00"},
        ),
        (
            PagamentoProcessado,
            {
                "event_id": "11111111-1111-4111-8111-111111111111",
                "occurred_at": "2025-01-15T12:00:00Z",
                "pedido_id": "22222222-2222-4222-8222-222222222222",
                "pagamento_id": "33333333-3333-4333-8333-333333333333",
                "valor": "10.00",
                "status": "APROVADO",
                "referencia_simulada": "SIM-pedido-1",
            },
            {"status": "PENDENTE"},
        ),
        (
            NotificacaoEnviada,
            {
                "event_id": "11111111-1111-4111-8111-111111111111",
                "occurred_at": "2025-01-15T12:00:00Z",
                "pedido_id": "22222222-2222-4222-8222-222222222222",
                "pagamento_status": "APROVADO",
                "canal": "INTERNO",
                "mensagem": "Pagamento aprovado.",
            },
            {"canal": "EMAIL"},
        ),
    ],
    ids=[
        "order-item-id-positive",
        "order-quantity-positive",
        "order-event-type-literal",
        "payment-request-nonnegative",
        "payment-status-literal",
        "notification-channel-literal",
    ],
)
def test_event_contracts_reject_invalid_values(model, base, override):
    payload = deepcopy(base)
    payload.update(override)

    with pytest.raises(ValidationError):
        model.model_validate(payload)
