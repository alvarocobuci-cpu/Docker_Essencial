from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    id: int
    name: str = Field(min_length=1, max_length=150)
    quantity: int = Field(ge=0)
    minimum_quantity: int = Field(ge=0)


class InventoryResponse(BaseModel):
    item: InventoryItem
    available: bool