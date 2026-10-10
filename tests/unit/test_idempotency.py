import hashlib
import json
from unittest.mock import Mock

import pytest
from redis.exceptions import RedisError

from aula4api import idempotency


def payload():
    return {
        "item_id": 2,
        "quantidade": 2,
        "preco_unitario": "10.00",
        "valor_total": "20.00",
    }


def request_hash(data):
    normalized = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@pytest.mark.unit
def test_reserve_new_idempotency_key(monkeypatch):
    client = Mock()
    client.set.return_value = True
    monkeypatch.setattr(idempotency, "redis_client", client)

    result = idempotency.reserve_pedido_key(
        "request-1",
        payload(),
        "pedido-1",
    )

    assert result["is_new"] is True
    assert result["pedido_id"] == "pedido-1"
    assert result["reservation_id"]
    assert result["redis_key"].startswith("idempotency:pedido:")

    stored = json.loads(client.set.call_args.args[1])
    assert stored["request_hash"] == request_hash(payload())
    assert stored["status"] == "publishing"
    assert client.set.call_args.kwargs["nx"] is True


@pytest.mark.unit
def test_reserve_returns_existing_matching_key(monkeypatch):
    client = Mock()
    client.set.return_value = False
    client.get.return_value = json.dumps({
        "request_hash": request_hash(payload()),
        "reservation_id": "reservation-existing",
        "pedido_id": "pedido-existing",
        "status": "published",
    })
    monkeypatch.setattr(idempotency, "redis_client", client)

    result = idempotency.reserve_pedido_key(
        "request-1",
        payload(),
        "pedido-new",
    )

    assert result["is_new"] is False
    assert result["pedido_id"] == "pedido-existing"
    assert result["status"] == "published"


@pytest.mark.unit
def test_reserve_rejects_same_key_with_different_payload(monkeypatch):
    client = Mock()
    client.set.return_value = False
    client.get.return_value = json.dumps({
        "request_hash": "different-hash",
        "reservation_id": "reservation-existing",
        "pedido_id": "pedido-existing",
        "status": "published",
    })
    monkeypatch.setattr(idempotency, "redis_client", client)

    with pytest.raises(idempotency.IdempotencyConflict):
        idempotency.reserve_pedido_key(
            "request-1",
            payload(),
            "pedido-new",
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "stored_value",
    [
        None,
        "not-json",
    ],
    ids=["expired-reservation", "malformed-json"],
)
def test_reserve_handles_missing_or_malformed_entry(
    monkeypatch,
    stored_value,
):
    client = Mock()
    client.set.return_value = False
    client.get.return_value = stored_value
    monkeypatch.setattr(idempotency, "redis_client", client)

    with pytest.raises(idempotency.IdempotencyUnavailable):
        idempotency.reserve_pedido_key(
            "request-1",
            payload(),
            "pedido-new",
        )


@pytest.mark.unit
def test_reserve_handles_redis_error(monkeypatch):
    client = Mock()
    client.set.side_effect = RedisError("Redis indisponivel")
    monkeypatch.setattr(idempotency, "redis_client", client)

    with pytest.raises(idempotency.IdempotencyUnavailable):
        idempotency.reserve_pedido_key(
            "request-1",
            payload(),
            "pedido-new",
        )


@pytest.mark.unit
def test_release_reservation(monkeypatch):
    client = Mock()
    client.eval.return_value = 1
    monkeypatch.setattr(idempotency, "redis_client", client)

    result = idempotency.release_pedido_key(
        "idempotency-key",
        "reservation-1",
    )

    assert result == 1
    client.eval.assert_called_once()


@pytest.mark.unit
def test_release_handles_redis_error(monkeypatch):
    client = Mock()
    client.eval.side_effect = RedisError("Redis indisponivel")
    monkeypatch.setattr(idempotency, "redis_client", client)

    with pytest.raises(idempotency.IdempotencyUnavailable):
        idempotency.release_pedido_key(
            "idempotency-key",
            "reservation-1",
        )


@pytest.mark.unit
def test_mark_published(monkeypatch):
    client = Mock()
    client.eval.return_value = 1
    monkeypatch.setattr(idempotency, "redis_client", client)

    result = idempotency.mark_pedido_published(
        "idempotency-key",
        "reservation-1",
        {
            "topic": "pedidos.criado",
            "partition": 1,
            "offset": 7,
        },
    )

    assert result is True
    client.eval.assert_called_once()


@pytest.mark.unit
def test_mark_published_returns_false_if_reservation_missing(monkeypatch):
    client = Mock()
    client.eval.return_value = 0
    monkeypatch.setattr(idempotency, "redis_client", client)

    assert idempotency.mark_pedido_published(
        "idempotency-key",
        "reservation-1",
        {"topic": "pedidos.criado", "partition": 0, "offset": 0},
    ) is False


@pytest.mark.unit
def test_mark_published_handles_redis_error(monkeypatch):
    client = Mock()
    client.eval.side_effect = RedisError("Redis indisponivel")
    monkeypatch.setattr(idempotency, "redis_client", client)

    with pytest.raises(idempotency.IdempotencyUnavailable):
        idempotency.mark_pedido_published(
            "idempotency-key",
            "reservation-1",
            {"topic": "pedidos.criado", "partition": 0, "offset": 0},
        )
