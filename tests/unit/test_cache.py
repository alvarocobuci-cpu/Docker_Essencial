from redis.exceptions import RedisError

import pytest

from inventory import cache


@pytest.mark.unit
def test_cache_miss_then_hit_and_metrics(fake_redis, monkeypatch):
    monkeypatch.setattr(cache, "redis_client", fake_redis)

    assert cache.get_cached_json("sample", "inventory_list") is None

    cache.set_cached_json(
        "sample",
        {"name": "Notebook"},
        60,
        "inventory_list",
    )

    assert cache.get_cached_json("sample", "inventory_list") == {
        "name": "Notebook"
    }

    metrics = cache.get_cache_metrics()
    endpoint = metrics["endpoints"]["inventory_list"]

    assert endpoint["total_lookups"] == 2
    assert endpoint["total_hits"] == 1
    assert endpoint["total_misses"] == 1
    assert endpoint["hit_rate"] == 0.5


@pytest.mark.unit
def test_invalid_json_is_removed(fake_redis, monkeypatch):
    monkeypatch.setattr(cache, "redis_client", fake_redis)
    fake_redis.set("broken", "{invalid-json")

    assert cache.get_cached_json("broken", "inventory_list") is None
    assert fake_redis.get("broken") is None


@pytest.mark.unit
def test_cache_read_handles_redis_unavailable(
    fake_redis,
    monkeypatch,
):
    monkeypatch.setattr(cache, "redis_client", fake_redis)

    def raise_redis_error(*args, **kwargs):
        raise RedisError("Redis indisponivel")

    monkeypatch.setattr(fake_redis, "get", raise_redis_error)

    assert cache.get_cached_json("sample", "inventory_list") is None


@pytest.mark.unit
def test_cache_write_handles_redis_unavailable(
    fake_redis,
    monkeypatch,
):
    monkeypatch.setattr(cache, "redis_client", fake_redis)

    def raise_redis_error(*args, **kwargs):
        raise RedisError("Redis indisponivel")

    monkeypatch.setattr(fake_redis, "set", raise_redis_error)

    cache.set_cached_json("sample", {"value": 1}, 30, "inventory_list")


@pytest.mark.unit
def test_invalidation_deletes_list_and_detail_keys(
    fake_redis,
    monkeypatch,
):
    monkeypatch.setattr(cache, "redis_client", fake_redis)
    fake_redis.set(cache.LIST_CACHE_KEY, "[]")
    fake_redis.set("inventory:8", "{}")
    fake_redis.set("unrelated", "keep")

    cache.invalidate_inventory_cache(
        item_id=8,
        event="InventoryUpdated",
    )

    assert fake_redis.get(cache.LIST_CACHE_KEY) is None
    assert fake_redis.get("inventory:8") is None
    assert fake_redis.get("unrelated") == "keep"


@pytest.mark.unit
def test_metrics_returns_unavailable_when_redis_fails(
    fake_redis,
    monkeypatch,
):
    monkeypatch.setattr(cache, "redis_client", fake_redis)

    def raise_redis_error(*args, **kwargs):
        raise RedisError("Redis indisponivel")

    monkeypatch.setattr(fake_redis, "mget", raise_redis_error)

    result = cache.get_cache_metrics()

    assert result["status"] == "unavailable"
    assert "error" in result

@pytest.mark.unit
def test_invalidation_handles_redis_unavailable(fake_redis, monkeypatch):
    monkeypatch.setattr(cache, "redis_client", fake_redis)

    def raise_redis_error(*args, **kwargs):
        raise RedisError("Redis indisponivel")

    monkeypatch.setattr(fake_redis, "delete", raise_redis_error)

    # A indisponibilidade do cache nao deve derrubar a operacao.
    cache.invalidate_inventory_cache(item_id=8)

@pytest.mark.unit
def test_invalid_json_is_ignored_when_cache_delete_fails(
    fake_redis,
    monkeypatch,
):
    monkeypatch.setattr(cache, "redis_client", fake_redis)
    fake_redis.set("broken", "{invalid-json")

    def raise_redis_error(*args, **kwargs):
        raise RedisError("Redis indisponivel durante a limpeza")

    monkeypatch.setattr(fake_redis, "delete", raise_redis_error)

    assert cache.get_cached_json("broken", "inventory_list") is None
