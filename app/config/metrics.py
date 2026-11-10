"""Registro de métricas operacionais do SynapseShop no Redis."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from functools import lru_cache
from typing import Any

from redis import Redis

logger = logging.getLogger(__name__)

RETENTION_SECONDS = int(
    os.getenv("API_METRICS_RETENTION_SECONDS", "604800")
)

REQUEST_METRICS_KEY = os.getenv(
    "API_METRICS_REDIS_KEY",
    "synapseshop:observability:requests",
)

CACHE_METRICS_KEY = os.getenv(
    "API_CACHE_METRICS_REDIS_KEY",
    "synapseshop:observability:cache",
)

MESSAGING_METRICS_KEY = os.getenv(
    "API_MESSAGING_METRICS_REDIS_KEY",
    "synapseshop:observability:messaging",
)


@lru_cache(maxsize=1)
def _get_redis() -> Redis:
    """Cria um cliente Redis reutilizável com timeouts curtos."""
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

    return Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=0.5,
        socket_timeout=0.5,
        health_check_interval=30,
    )


def _store_event(key: str, event: dict[str, Any]) -> bool:
    """Armazena evento no Redis e aplica a política de retenção."""
    try:
        timestamp = float(event["timestamp"])

        member = json.dumps(
            event,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        client = _get_redis()

        with client.pipeline(transaction=False) as pipeline:
            pipeline.zadd(key, {member: timestamp})
            pipeline.expire(key, RETENTION_SECONDS)
            pipeline.zremrangebyscore(
                key,
                "-inf",
                timestamp - RETENTION_SECONDS,
            )
            pipeline.execute()

        return True

    except Exception:
        # A indisponibilidade do Redis não deve derrubar a API.
        logger.warning(
            "Não foi possível registrar uma métrica no Redis.",
            exc_info=True,
        )
        return False


def build_request_event(
    *,
    method: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    cache_status: str = "not_instrumented",
    timestamp: float | None = None,
) -> dict[str, Any]:
    """Monta um evento HTTP sem armazenar dados sensíveis."""
    occurred_at = time.time() if timestamp is None else float(timestamp)
    code = int(status_code)

    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": occurred_at,
        "method": str(method).upper(),
        "endpoint": str(endpoint)[:200],
        "status_code": code,
        "status_group": f"{code // 100}xx",
        "duration_ms": round(max(0.0, float(duration_ms)), 3),
        "cache_status": str(
            cache_status or "not_instrumented"
        ).strip()[:40].lower(),
    }


def record_request_metric(**kwargs: Any) -> bool:
    """Registra uma requisição HTTP."""
    event = build_request_event(**kwargs)
    return _store_event(REQUEST_METRICS_KEY, event)


def record_cache_metric(
    *,
    cache_name: str,
    operation: str,
    outcome: str,
    timestamp: float | None = None,
) -> bool:
    """Registra evento de cache: hit, miss ou error."""
    event = {
        "event_id": str(uuid.uuid4()),
        "timestamp": time.time() if timestamp is None else float(timestamp),
        "cache_name": str(cache_name)[:100],
        "operation": str(operation)[:40].lower(),
        "outcome": str(outcome)[:40].lower(),
    }

    return _store_event(CACHE_METRICS_KEY, event)


def record_messaging_metric(
    *,
    topic: str,
    direction: str,
    outcome: str,
    duration_ms: float | None = None,
    timestamp: float | None = None,
) -> bool:
    """Registra publicação ou consumo de eventos Kafka."""
    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "timestamp": time.time() if timestamp is None else float(timestamp),
        "topic": str(topic)[:200],
        "direction": str(direction)[:30].lower(),
        "outcome": str(outcome)[:40].lower(),
    }

    if duration_ms is not None:
        event["duration_ms"] = round(
            max(0.0, float(duration_ms)),
            3,
        )

    return _store_event(MESSAGING_METRICS_KEY, event)