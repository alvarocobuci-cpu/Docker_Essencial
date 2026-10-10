import hashlib
import json
import os
import uuid

import redis
from redis.exceptions import RedisError


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0",
)

IDEMPOTENCY_TTL = int(
    os.getenv("PEDIDO_IDEMPOTENCY_TTL_SECONDS", "86400")
)

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


class IdempotencyConflict(Exception):
    """A mesma chave foi reutilizada com dados diferentes."""


class IdempotencyUnavailable(Exception):
    """Não foi possível consultar o Redis."""


def reserve_pedido_key(idempotency_key, payload, pedido_id):
    payload_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )

    request_hash = hashlib.sha256(
        payload_json.encode("utf-8")
    ).hexdigest()

    key_hash = hashlib.sha256(
        idempotency_key.encode("utf-8")
    ).hexdigest()

    redis_key = f"idempotency:pedido:{key_hash}"

    reservation_id = str(uuid.uuid4())

    entry = {
        "idempotency_key": idempotency_key,
        "request_hash": request_hash,
        "pedido_id": str(pedido_id),
        "reservation_id": reservation_id,
        "status": "publishing",
    }

    try:
        created = redis_client.set(
            redis_key,
            json.dumps(entry, separators=(",", ":")),
            nx=True,
            ex=IDEMPOTENCY_TTL,
        )

        if created:
            return {
                "is_new": True,
                "redis_key": redis_key,
                "reservation_id": reservation_id,
                "pedido_id": str(pedido_id),
            }

        existing_raw = redis_client.get(redis_key)

        if existing_raw is None:
            raise IdempotencyUnavailable(
                "A reserva expirou durante a operação. Tente novamente."
            )

        existing = json.loads(existing_raw)

        if existing["request_hash"] != request_hash:
            raise IdempotencyConflict(
                "Esta chave de idempotência já foi utilizada "
                "com dados diferentes."
            )

        return {
            "is_new": False,
            "redis_key": redis_key,
            "reservation_id": existing["reservation_id"],
            "pedido_id": existing["pedido_id"],
            "status": existing["status"],
        }

    except IdempotencyConflict:
        raise

    except (RedisError, ValueError, KeyError) as exc:
        raise IdempotencyUnavailable(
            "Não foi possível verificar a idempotência."
        ) from exc


def release_pedido_key(redis_key, reservation_id):
    script = """
    local raw = redis.call('GET', KEYS[1])
    if not raw then
        return 0
    end

    local entry = cjson.decode(raw)

    if entry['reservation_id'] == ARGV[1] then
        return redis.call('DEL', KEYS[1])
    end

    return 0
    """

    try:
        return redis_client.eval(
            script,
            1,
            redis_key,
            reservation_id,
        )

    except RedisError as exc:
        raise IdempotencyUnavailable(
            "Não foi possível liberar a reserva de idempotência."
        ) from exc


def mark_pedido_published(
    redis_key,
    reservation_id,
    metadata,
):
    script = """
    local raw = redis.call('GET', KEYS[1])
    if not raw then
        return 0
    end

    local entry = cjson.decode(raw)

    if entry['reservation_id'] ~= ARGV[1] then
        return 0
    end

    local ttl = redis.call('TTL', KEYS[1])

    if ttl <= 0 then
        return 0
    end

    entry['status'] = 'published'
    entry['topic'] = ARGV[2]
    entry['partition'] = tonumber(ARGV[3])
    entry['offset'] = tonumber(ARGV[4])

    redis.call(
        'SET',
        KEYS[1],
        cjson.encode(entry),
        'EX',
        ttl
    )

    return 1
    """

    try:
        return bool(
            redis_client.eval(
                script,
                1,
                redis_key,
                reservation_id,
                metadata["topic"],
                metadata["partition"],
                metadata["offset"],
            )
        )

    except RedisError as exc:
        raise IdempotencyUnavailable(
            "Não foi possível atualizar o estado da publicação."
        ) from exc