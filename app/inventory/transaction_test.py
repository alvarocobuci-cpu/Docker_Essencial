from .database import SessionLocal
from .repositories import InventoryRepository


def main():
    db = SessionLocal()

    try:
        repository = InventoryRepository(db)

        item = repository.create(
            name="Teste de Rollback",
            quantity=10,
            minimum_quantity=2,
        )

        print(f"Item criado na transação: {item.name}")
        print(f"ID temporário: {item.id}")

        db.rollback()

        print("Rollback executado com sucesso.")

        item_after_rollback = repository.get_by_id(item.id)

        if item_after_rollback is None:
            print("OK: o item não foi persistido no banco.")
        else:
            print("ERRO: o item ainda existe no banco.")

    finally:
        db.close()


if __name__ == "__main__":
    main()