import time

from .database import SessionLocal
from .repositories import InventoryRepository


def main():
    db = SessionLocal()
    repository = InventoryRepository(db)

    try:
        start = time.perf_counter()

        item = repository.create(
            name="Teste de Performance",
            quantity=20,
            minimum_quantity=5,
        )

        db.commit()

        create_time = time.perf_counter() - start

        start = time.perf_counter()

        found_item = repository.get_by_id(item.id)

        read_time = time.perf_counter() - start

        start = time.perf_counter()

        repository.update_quantity(
            item_id=item.id,
            quantity=15,
        )

        db.commit()

        update_time = time.perf_counter() - start

        print(f"CREATE: {create_time * 1000:.2f} ms")
        print(f"READ:   {read_time * 1000:.2f} ms")
        print(f"UPDATE: {update_time * 1000:.2f} ms")
        print(f"Item consultado: {found_item.name}")

        repository.delete(item.id)
        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    main()