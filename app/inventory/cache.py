import json
import logging
import os

import redis
from redis.exceptions import RedisError


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger("synapseshop.cache")
logger.setLevel(logging.INFO)

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

LIST_CACHE_KEY = "inventory:list"
LIST_CACHE_TTL = 60

DETAIL_CACHE_TTL = 300


def log_cache_event(event, endpoint, key, **details):
    logger.info(
        json.dumps(
            {
                "event": event,
                "endpoint": endpoint,
                "key": key,
                **details,
            },
            ensure_ascii=False,
        )
    )


def get_cached_json(key, endpoint):
    try:
        value = redis_client.get(key)

        redis_client.incr(
            f"cache:metrics:{endpoint}:lookups"
        )

        if value is None:
            log_cache_event(
                "cache_miss",
                endpoint,
                key,
            )
            return None

        redis_client.incr(
            f"cache:metrics:{endpoint}:hits"
        )

        log_cache_event(
            "cache_hit",
            endpoint,
            key,
        )

        return json.loads(value)

    except json.JSONDecodeError:
        log_cache_event(
            "cache_invalid_json",
            endpoint,
            key,
        )

        try:
            redis_client.delete(key)
        except RedisError:
            pass

        return None

    except RedisError as exc:
        log_cache_event(
            "cache_unavailable",
            endpoint,
            key,
            error=str(exc),
        )

        return None


def set_cached_json(key, value, ttl, endpoint):
    try:
        redis_client.set(
            key,
            json.dumps(value, ensure_ascii=False),
            ex=ttl,
        )

        log_cache_event(
            "cache_fill",
            endpoint,
            key,
            ttl_seconds=ttl,
        )

    except RedisError as exc:
        log_cache_event(
            "cache_write_error",
            endpoint,
            key,
            error=str(exc),
        )


def invalidate_inventory_cache(
    item_id=None,
    event="InventoryUpdated",
):
    keys = [LIST_CACHE_KEY]

    if item_id is not None:
        keys.append(f"inventory:{item_id}")

    try:
        deleted = redis_client.delete(*keys)

        log_cache_event(
            "cache_invalidation",
            "inventory",
            ",".join(keys),
            domain_event=event,
            deleted_keys=deleted,
        )

    except RedisError as exc:
        log_cache_event(
            "cache_invalidation_error",
            "inventory",
            ",".join(keys),
            domain_event=event,
            error=str(exc),
        )


def get_cache_metrics():
    endpoints = [
        "inventory_list",
        "inventory_detail",
    ]

    result = {}

    try:
        for endpoint in endpoints:
            lookups, hits = redis_client.mget(
                [
                    f"cache:metrics:{endpoint}:lookups",
                    f"cache:metrics:{endpoint}:hits",
                ]
            )

            total_lookups = int(lookups or 0)
            total_hits = int(hits or 0)

            result[endpoint] = {
                "total_lookups": total_lookups,
                "total_hits": total_hits,
                "total_misses": total_lookups - total_hits,
                "hit_rate": (
                    round(total_hits / total_lookups, 4)
                    if total_lookups
                    else 0
                ),
            }

        return {
            "status": "ok",
            "endpoints": result,
        }

    except RedisError as exc:
        return {
            "status": "unavailable",
            "error": str(exc),
            "endpoints": result,
        }