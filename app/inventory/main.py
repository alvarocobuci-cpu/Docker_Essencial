from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from .cache import (
    DETAIL_CACHE_TTL,
    LIST_CACHE_KEY,
    LIST_CACHE_TTL,
    get_cached_json,
    get_cache_metrics,
    invalidate_inventory_cache,
    set_cached_json,
)
from .database import get_db
from .schemas import (
    InventoryItemCreate,
    InventoryItemResponse,
    InventoryResponse,
)
from .services import InventoryService


app = FastAPI(
    title="SynapseShop Inventory API",
    description="Microsserviço de estoque com cache-aside.",
    version="3.0.0",
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


@app.get("/cache/metrics", tags=["Cache"])
def cache_metrics():
    return get_cache_metrics()


@app.get(
    "/inventory",
    response_model=list[InventoryItemResponse],
    tags=["Inventory"],
)
def list_inventory(db: Session = Depends(get_db)):
    cached_items = get_cached_json(
        LIST_CACHE_KEY,
        "inventory_list",
    )

    if cached_items is not None:
        return cached_items

    service = InventoryService(db)
    items = service.list_items()

    result = [
        InventoryItemResponse.model_validate(item).model_dump(
            mode="json"
        )
        for item in items
    ]

    set_cached_json(
        LIST_CACHE_KEY,
        result,
        LIST_CACHE_TTL,
        "inventory_list",
    )

    return result


@app.get(
    "/inventory/{item_id}",
    response_model=InventoryResponse,
    tags=["Inventory"],
)
def get_inventory(
    item_id: int,
    db: Session = Depends(get_db),
):
    cache_key = f"inventory:{item_id}"

    cached_item = get_cached_json(
        cache_key,
        "inventory_detail",
    )

    if cached_item is not None:
        return cached_item

    service = InventoryService(db)
    item = service.get_item(item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item não encontrado.",
        )

    response = InventoryResponse(
        item=item,
        available=item.quantity > 0,
    )

    result = response.model_dump(mode="json")

    set_cached_json(
        cache_key,
        result,
        DETAIL_CACHE_TTL,
        "inventory_detail",
    )

    return result


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

    item = service.create_item(
        name=item_data.name,
        quantity=item_data.quantity,
        minimum_quantity=item_data.minimum_quantity,
    )

    invalidate_inventory_cache(
        event="InventoryCreated",
    )

    return item


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

    invalidate_inventory_cache(
        item_id=item_id,
        event="InventoryUpdated",
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

    invalidate_inventory_cache(
        item_id=item_id,
        event="InventoryDeleted",
    )

    return None