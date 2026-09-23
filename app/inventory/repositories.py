from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import InventoryItem


class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, item_id: int):
        return self.db.get(InventoryItem, item_id)

    def list_all(self):
        statement = select(InventoryItem).order_by(InventoryItem.id)
        return list(self.db.scalars(statement).all())

    def create(
        self,
        name: str,
        quantity: int,
        minimum_quantity: int,
    ):
        item = InventoryItem(
            name=name,
            quantity=quantity,
            minimum_quantity=minimum_quantity,
        )

        self.db.add(item)
        self.db.flush()

        return item

    def update_quantity(
        self,
        item_id: int,
        quantity: int,
    ):
        item = self.get_by_id(item_id)

        if item is None:
            return None

        item.quantity = quantity
        self.db.flush()

        return item

    def delete(self, item_id: int):
        item = self.get_by_id(item_id)

        if item is None:
            return False

        self.db.delete(item)
        self.db.flush()

        return True