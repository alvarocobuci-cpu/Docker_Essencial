from sqlalchemy.orm import Session

from .repositories import InventoryRepository


class InventoryService:
    def __init__(self, db: Session):
        self.repository = InventoryRepository(db)
        self.db = db

    def get_item(self, item_id: int):
        return self.repository.get_by_id(item_id)

    def list_items(self):
        return self.repository.list_all()

    def create_item(
        self,
        name: str,
        quantity: int,
        minimum_quantity: int,
    ):
        item = self.repository.create(
            name=name,
            quantity=quantity,
            minimum_quantity=minimum_quantity,
        )

        self.db.commit()
        self.db.refresh(item)

        return item

    def update_quantity(
        self,
        item_id: int,
        quantity: int,
    ):
        item = self.repository.update_quantity(
            item_id=item_id,
            quantity=quantity,
        )

        if item is None:
            return None

        self.db.commit()
        self.db.refresh(item)

        return item

    def delete_item(self, item_id: int):
        deleted = self.repository.delete(item_id)

        if not deleted:
            return False

        self.db.commit()

        return True