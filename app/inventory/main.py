from fastapi import FastAPI, HTTPException

from .schemas import InventoryItem, InventoryResponse


app = FastAPI(
    title="SynapseShop Inventory API",
    description="Microsserviço complementar de estoque da Aula 5.",
    version="1.0.0",
)


items = {
    1: InventoryItem(
        id=1,
        name="Notebook Gamer",
        quantity=8,
        minimum_quantity=3,
    ),
    2: InventoryItem(
        id=2,
        name="Notebook",
        quantity=10,
        minimum_quantity=3,
    ),
}


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
    "/inventory/{item_id}",
    response_model=InventoryResponse,
    tags=["Inventory"],
)
def get_inventory(item_id: int):
    item = items.get(item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Item não encontrado.",
        )

    return InventoryResponse(
        item=item,
        available=item.quantity > 0,
    )