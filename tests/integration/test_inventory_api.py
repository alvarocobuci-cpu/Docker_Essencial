import pytest

from inventory.models import InventoryItem


@pytest.mark.integration
def test_inventory_resource_lifecycle(client, db_session):
    # POST: cria o item pela API.
    response = client.post(
        "/inventory",
        json={
            "name": "Mouse Gamer",
            "quantity": 5,
            "minimum_quantity": 1,
        },
    )

    assert response.status_code == 201
    created = response.json()
    item_id = created["id"]

    # Confirma que a alteracao foi persistida no banco efemero.
    item = db_session.get(InventoryItem, item_id)
    assert item is not None
    assert item.name == "Mouse Gamer"
    assert item.quantity == 5

    # GET: consulta o item criado.
    response = client.get(f"/inventory/{item_id}")

    assert response.status_code == 200
    assert response.json()["item"]["id"] == item_id
    assert response.json()["available"] is True

    # PUT: atualiza a quantidade para zero.
    response = client.put(
        f"/inventory/{item_id}/quantity",
        params={"quantity": 0},
    )

    assert response.status_code == 200
    assert response.json()["quantity"] == 0

    # A disponibilidade deve refletir a quantidade atualizada.
    response = client.get(f"/inventory/{item_id}")

    assert response.status_code == 200
    assert response.json()["available"] is False

    # DELETE: remove o item.
    response = client.delete(f"/inventory/{item_id}")

    assert response.status_code == 204
    assert db_session.get(InventoryItem, item_id) is None

    # GET depois da exclusao deve retornar 404.
    response = client.get(f"/inventory/{item_id}")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.parametrize(
    ("method", "path", "kwargs", "expected_status"),
    [
        ("get", "/inventory/99999", {}, 404),
        (
            "put",
            "/inventory/99999/quantity",
            {"params": {"quantity": 10}},
            404,
        ),
        ("delete", "/inventory/99999", {}, 404),
        (
            "put",
            "/inventory/99999/quantity",
            {"params": {"quantity": -1}},
            400,
        ),
    ],
)
def test_inventory_error_responses(
    client,
    method,
    path,
    kwargs,
    expected_status,
):
    response = getattr(client, method)(path, **kwargs)

    assert response.status_code == expected_status


@pytest.mark.integration
def test_list_inventory_returns_created_records(client, db_session):
    db_session.add_all(
        [
            InventoryItem(
                name="Teclado",
                quantity=3,
                minimum_quantity=1,
            ),
            InventoryItem(
                name="Headset",
                quantity=0,
                minimum_quantity=2,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/inventory")

    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == [
        "Teclado",
        "Headset",
    ]

@pytest.mark.integration
def test_health_endpoints_and_cache_metrics(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json() == {"service": "inventory", "status": "online"}

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "healthy"}

    metrics = client.get("/cache/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["status"] == "ok"


@pytest.mark.integration
def test_inventory_list_and_detail_cache_hits(client, fake_redis):
    import json
    from inventory import cache

    list_payload = [
        {
            "id": 91,
            "name": "Item em cache",
            "quantity": 4,
            "minimum_quantity": 1,
        }
    ]

    detail_payload = {
        "item": list_payload[0],
        "available": True,
    }

    fake_redis.set(
        cache.LIST_CACHE_KEY,
        json.dumps(list_payload),
        ex=cache.LIST_CACHE_TTL,
    )
    fake_redis.set(
        "inventory:91",
        json.dumps(detail_payload),
        ex=cache.DETAIL_CACHE_TTL,
    )

    response_list = client.get("/inventory")
    assert response_list.status_code == 200
    assert response_list.json() == list_payload

    response_detail = client.get("/inventory/91")
    assert response_detail.status_code == 200
    assert response_detail.json() == detail_payload
