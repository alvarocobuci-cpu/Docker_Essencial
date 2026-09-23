from pydantic import BaseModel, Field


class InventoryItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    quantity: int = Field(ge=0)
    minimum_quantity: int = Field(ge=0)


class InventoryItemCreate(InventoryItemBase):
    pass


class InventoryItemResponse(InventoryItemBase):
    id: int

    model_config = {
        "from_attributes": True
    }


class InventoryResponse(BaseModel):
    item: InventoryItemResponse
    available: bool