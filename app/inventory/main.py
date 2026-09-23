from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .schemas import (
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryResponse,
)
from .services import InventoryService


app = FastAPI(
    title="SynapseShop Inventory API",
    description="Microsserviço de estoque da Aula 6.",
    version="2.0.0",
)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": "inventory",
        "status": "online",
    }


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "healthy",
    }


@app.get(
    "/inventory",
    response_model=list[InventoryItemResponse],
    tags=["Inventory"],
)
def list_inventory(db: Session = Depends(get_db)):
    service = InventoryService(db)
    return service.list_items()


@app.get(
    "/inventory/{item_id}",
    response_model=InventoryResponse,
    tags=["Inventory"],
)
def get_inventory(
    item_id: int,
    db: Session = Depends(get_db),
):
    service = InventoryService(db)

    item = service.get_item(item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item não encontrado.",
        )

    return InventoryResponse(
        item=item,
        available=item.quantity > 0,
    )


@app.post(
    "/inventory",
    response_model=InventoryItemResponse,
    status_code=201,
    tags=["Inventory"],
)
def create_inventory(
    item_data: InventoryItemCreate,
    db: Session = Depends(get_db),
):
    service = InventoryService(db)

    return service.create_item(
        name=item_data.name,
        quantity=item_data.quantity,
        minimum_quantity=item_data.minimum_quantity,
    )


@app.put(
    "/inventory/{item_id}/quantity",
    response_model=InventoryItemResponse,
    tags=["Inventory"],
)
def update_inventory_quantity(
    item_id: int,
    quantity: int,
    db: Session = Depends(get_db),
):
    if quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="A quantidade não pode ser negativa.",
        )

    service = InventoryService(db)

    item = service.update_quantity(
        item_id=item_id,
        quantity=quantity,
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item não encontrado.",
        )

    return item


@app.delete(
    "/inventory/{item_id}",
    status_code=204,
    tags=["Inventory"],
)
def delete_inventory(
    item_id: int,
    db: Session = Depends(get_db),
):
    service = InventoryService(db)

    deleted = service.delete_item(item_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Item não encontrado.",
        )

    return None