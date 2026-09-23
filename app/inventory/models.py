from sqlalchemy import CheckConstraint, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="ck_inventory_quantity_non_negative",
        ),
        CheckConstraint(
            "minimum_quantity >= 0",
            name="ck_inventory_minimum_quantity_non_negative",
        ),
        Index(
            "ix_inventory_items_name",
            "name",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    minimum_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )