from unittest.mock import Mock

import pytest

import inventory.services as services


@pytest.mark.unit
def test_get_item_delegates_to_repository(monkeypatch):
    item = object()
    repository = Mock()
    repository.get_by_id.return_value = item
    monkeypatch.setattr(
        services,
        "InventoryRepository",
        lambda db: repository,
    )

    result = services.InventoryService(Mock()).get_item(7)

    assert result is item
    repository.get_by_id.assert_called_once_with(7)


@pytest.mark.unit
def test_list_items_delegates_to_repository(monkeypatch):
    expected = [object(), object()]
    repository = Mock()
    repository.list_all.return_value = expected
    monkeypatch.setattr(
        services,
        "InventoryRepository",
        lambda db: repository,
    )

    result = services.InventoryService(Mock()).list_items()

    assert result == expected
    repository.list_all.assert_called_once_with()


@pytest.mark.unit
def test_create_item_commits_and_refreshes(monkeypatch):
    item = object()
    repository = Mock()
    repository.create.return_value = item
    monkeypatch.setattr(
        services,
        "InventoryRepository",
        lambda db: repository,
    )
    db = Mock()

    result = services.InventoryService(db).create_item(
        name="Notebook",
        quantity=10,
        minimum_quantity=2,
    )

    assert result is item
    repository.create.assert_called_once_with(
        name="Notebook",
        quantity=10,
        minimum_quantity=2,
    )
    db.commit.assert_called_once_with()
    db.refresh.assert_called_once_with(item)


@pytest.mark.unit
@pytest.mark.parametrize("found", [True, False])
def test_update_quantity_commits_only_when_item_exists(monkeypatch, found):
    item = object() if found else None
    repository = Mock()
    repository.update_quantity.return_value = item
    monkeypatch.setattr(
        services,
        "InventoryRepository",
        lambda db: repository,
    )
    db = Mock()

    result = services.InventoryService(db).update_quantity(5, 8)

    assert result is item
    repository.update_quantity.assert_called_once_with(
        item_id=5,
        quantity=8,
    )

    if found:
        db.commit.assert_called_once_with()
        db.refresh.assert_called_once_with(item)
    else:
        db.commit.assert_not_called()
        db.refresh.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("deleted", "expected"),
    [(True, True), (False, False)],
)
def test_delete_item_commits_only_after_deletion(
    monkeypatch,
    deleted,
    expected,
):
    repository = Mock()
    repository.delete.return_value = deleted
    monkeypatch.setattr(
        services,
        "InventoryRepository",
        lambda db: repository,
    )
    db = Mock()

    result = services.InventoryService(db).delete_item(4)

    assert result is expected
    repository.delete.assert_called_once_with(4)

    if deleted:
        db.commit.assert_called_once_with()
    else:
        db.commit.assert_not_called()
