"""Transformacao e leitura das metricas do painel de desempenho."""

from __future__ import annotations

import json
import math
import os
from collections import Counter, defaultdict
from typing import Any, Iterable

DEFAULT_REQUEST_KEY = "synapseshop:observability:requests"
DEFAULT_CACHE_KEY = "synapseshop:observability:cache"
DEFAULT_MESSAGING_KEY = "synapseshop:observability:messaging"

CACHE_ENDPOINTS = ("inventory_list", "inventory_detail")


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _decode_json(raw: Any) -> dict[str, Any] | None:
    try:
        event = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None

    return event if isinstance(event, dict) else None


def _normalize_request_event(event: dict[str, Any]) -> dict[str, Any] | None:
    timestamp = _to_float(event.get("timestamp"))
    duration_ms = _to_float(event.get("duration_ms"))
    status_code = _to_int(event.get("status_code"))

    if timestamp is None or duration_ms is None or status_code is None:
        return None

    return {
        "event_id": event.get("event_id"),
        "timestamp": timestamp,
        "method": str(event.get("method", "")).upper(),
        "endpoint": str(event.get("endpoint", "")),
        "status_code": status_code,
        "status_group": f"{status_code // 100}xx",
        "duration_ms": max(0.0, duration_ms),
        "cache_status": str(
            event.get("cache_status") or "not_instrumented"
        ).lower(),
    }


def parse_request_events(
    events: Iterable[Any],
) -> list[dict[str, Any]]:
    """Converte os eventos JSON do Redis em registros normalizados."""
    records: list[dict[str, Any]] = []

    for raw in events:
        event = _decode_json(raw)

        if event is None:
            continue

        record = _normalize_request_event(event)

        if record is not None:
            records.append(record)

    records.sort(key=lambda record: record["timestamp"])

    return records


def parse_messaging_events(
    events: Iterable[Any],
) -> list[dict[str, Any]]:
    """Converte os eventos de mensageria em registros normalizados."""
    records: list[dict[str, Any]] = []

    for raw in events:
        event = _decode_json(raw)

        if event is None:
            continue

        timestamp = _to_float(event.get("timestamp"))

        if timestamp is None:
            continue

        records.append(
            {
                "timestamp": timestamp,
                "topic": str(event.get("topic", "")),
                "direction": str(event.get("direction", "")).lower(),
                "outcome": str(event.get("outcome", "")).lower(),
                "duration_ms": _to_float(event.get("duration_ms")),
            }
        )

    records.sort(key=lambda record: record["timestamp"])

    return records


def filter_by_period(
    records: list[dict[str, Any]],
    *,
    now: float,
    hours: int | None,
) -> list[dict[str, Any]]:
    if hours is None:
        return list(records)

    cutoff = now - (hours * 3600)

    return [
        record
        for record in records
        if record["timestamp"] >= cutoff
    ]


def filter_by_endpoints(
    records: list[dict[str, Any]],
    endpoints: Iterable[str],
) -> list[dict[str, Any]]:
    allowed = set(endpoints)

    return [
        record
        for record in records
        if record["endpoint"] in allowed
    ]


def filter_by_status_groups(
    records: list[dict[str, Any]],
    status_groups: Iterable[str],
) -> list[dict[str, Any]]:
    allowed = set(status_groups)

    return [
        record
        for record in records
        if record["status_group"] in allowed
    ]


def _percentile(
    sorted_values: list[float],
    quantile: float,
) -> float:
    """Percentil com interpolacao linear, equivalente ao pandas."""
    if not sorted_values:
        return 0.0

    if len(sorted_values) == 1:
        return float(sorted_values[0])

    position = (len(sorted_values) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return float(sorted_values[lower])

    fraction = position - lower

    return float(
        sorted_values[lower]
        + (sorted_values[upper] - sorted_values[lower]) * fraction
    )


def compute_kpis(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)

    if total == 0:
        return {
            "total_requests": 0,
            "average_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "error_count": 0,
            "error_rate_percent": 0.0,
        }

    durations = sorted(record["duration_ms"] for record in records)
    error_count = sum(
        1 for record in records if record["status_code"] >= 400
    )

    return {
        "total_requests": total,
        "average_latency_ms": sum(durations) / total,
        "p95_latency_ms": _percentile(durations, 0.95),
        "error_count": error_count,
        "error_rate_percent": (error_count / total) * 100,
    }


def aggregate_latency_by_minute(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    buckets: dict[int, list[float]] = defaultdict(list)

    for record in records:
        minute = int(record["timestamp"] // 60) * 60
        buckets[minute].append(record["duration_ms"])

    return [
        {
            "minute": minute,
            "average_latency_ms": sum(values) / len(values),
        }
        for minute, values in sorted(buckets.items())
    ]


def aggregate_throughput_by_minute(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counters = Counter(
        int(record["timestamp"] // 60) * 60 for record in records
    )

    return [
        {"minute": minute, "requests": count}
        for minute, count in sorted(counters.items())
    ]


def aggregate_status_distribution(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counters = Counter(record["status_group"] for record in records)

    return [
        {"status_group": status_group, "count": count}
        for status_group, count in sorted(counters.items())
    ]


def aggregate_messaging(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counters = Counter(
        (record["direction"], record["outcome"]) for record in records
    )

    return [
        {"direction": direction, "outcome": outcome, "count": count}
        for (direction, outcome), count in sorted(counters.items())
    ]


def build_cache_metrics(
    hits_by_endpoint: dict[str, int],
    lookups_by_endpoint: dict[str, int],
) -> list[dict[str, Any]]:
    endpoints = sorted(
        set(hits_by_endpoint) | set(lookups_by_endpoint)
    )

    rows: list[dict[str, Any]] = []

    for endpoint in endpoints:
        hits = max(0, int(hits_by_endpoint.get(endpoint, 0)))
        lookups = max(0, int(lookups_by_endpoint.get(endpoint, 0)))
        misses = max(0, lookups - hits)

        rows.append(
            {
                "endpoint": endpoint,
                "hits": hits,
                "misses": misses,
                "lookups": lookups,
                "hit_rate_percent": (
                    round((hits / lookups) * 100, 2)
                    if lookups
                    else 0.0
                ),
            }
        )

    return rows


def _redis_client():
    import redis

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

    return redis.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def load_request_events() -> list[str]:
    key = os.getenv("API_METRICS_REDIS_KEY", DEFAULT_REQUEST_KEY)
    client = _redis_client()

    try:
        return client.zrange(key, 0, -1)
    finally:
        client.close()


def load_cache_metrics() -> list[dict[str, Any]]:
    client = _redis_client()

    try:
        keys: list[str] = []

        for endpoint in CACHE_ENDPOINTS:
            keys.append(f"cache:metrics:{endpoint}:hits")
            keys.append(f"cache:metrics:{endpoint}:lookups")

        values = client.mget(keys)
    finally:
        client.close()

    hits_by_endpoint: dict[str, int] = {}
    lookups_by_endpoint: dict[str, int] = {}

    for index, endpoint in enumerate(CACHE_ENDPOINTS):
        hits_by_endpoint[endpoint] = int(
            (values[index * 2] if values else 0) or 0
        )
        lookups_by_endpoint[endpoint] = int(
            (values[index * 2 + 1] if values else 0) or 0
        )

    return build_cache_metrics(
        hits_by_endpoint,
        lookups_by_endpoint,
    )


def load_messaging_events() -> list[str]:
    key = os.getenv(
        "API_MESSAGING_METRICS_REDIS_KEY",
        DEFAULT_MESSAGING_KEY,
    )
    client = _redis_client()

    try:
        return client.zrange(key, 0, -1)
    finally:
        client.close()
