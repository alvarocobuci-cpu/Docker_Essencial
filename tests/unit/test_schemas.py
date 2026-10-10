import pytest
from pydantic import ValidationError

from inventory.schemas import InventoryItemCreate, InventoryItemResponse


@pytest.mark.unit
@pytest.mark.parametrize(
    ("payload", "expected_quantity"),
    [
        ({"name": "Notebook", "quantity": 0, "minimum_quantity": 0}, 0),
        ({"name": "Mouse", "quantity": 12, "minimum_quantity": 3}, 12),
    ],
)
def test_inventory_item_create_accepts_valid_data(payload, expected_quantity):
    item = InventoryItemCreate.model_validate(payload)

    assert item.quantity == expected_quantity
    assert item.name == payload["name"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "quantity": 1, "minimum_quantity": 0},
        {"name": "Mouse", "quantity": -1, "minimum_quantity": 0},
        {"name": "Mouse", "quantity": 1, "minimum_quantity": -1},
    ],
    ids=["empty-name", "negative-quantity", "negative-minimum"],
)
def test_inventory_item_create_rejects_invalid_data(payload):
    with pytest.raises(ValidationError):
        InventoryItemCreate.model_validate(payload)


@pytest.mark.unit
def test_inventory_item_response_accepts_model_fields():
    item = InventoryItemResponse(
        id=10,
        name="Teclado",
        quantity=5,
        minimum_quantity=1,
    )

    assert item.id == 10
    assert item.quantity == 5
