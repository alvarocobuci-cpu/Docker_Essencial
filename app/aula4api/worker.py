import hashlib
import json
import logging
import os
import sys
import time
from decimal import Decimal

import redis
from django.db import transaction
from kafka import KafkaConsumer, KafkaProducer
from kafka.structs import OffsetAndMetadata, TopicPartition

# Permite que o worker encontre config.settings e aula4api.
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from aula4api.event_contracts import PedidoCriado
from aula4api.models import Item, Pedido


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

logger = logging.getLogger("synapseshop.worker")

KAFKA_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092",
)

MAIN_TOPIC = "pedidos.criado"
DLQ_TOPIC = "pedidos.criado.dlq"
CONSUMER_GROUP = "pedidos-worker-v1"

MAX_ATTEMPTS = int(
    os.getenv("PEDIDOS_MAX_ATTEMPTS", "3")
)

RETRY_BASE_SECONDS = float(
    os.getenv("PEDIDOS_RETRY_BASE_SECONDS", "1")
)

IDEMPOTENCY_TTL = int(
    os.getenv("PEDIDO_IDEMPOTENCY_TTL_SECONDS", "86400")
)

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def log_event(event_name, **details):
    logger.info(
        json.dumps(
            {
                "event": event_name,
                **details,
            },
            ensure_ascii=False,
            default=str,
        )
    )


def event_request_hash(event):
    payload = {
        "item_id": event.item_id,
        "quantidade": event.quantidade,
        "preco_unitario": str(event.preco_unitario),
        "valor_total": str(event.valor_total),
    }

    normalized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def processed_key(idempotency_key):
    key_hash = hashlib.sha256(
        idempotency_key.encode("utf-8")
    ).hexdigest()

    return f"pedidos:processed:{key_hash}"


def check_existing_order(pedido, event):
    same_payload = (
        pedido.item_id == event.item_id
        and pedido.quantidade == event.quantidade
        and pedido.preco_unitario == event.preco_unitario
        and pedido.valor_total == event.valor_total
    )

    if not same_payload:
        raise ValueError(
            "A chave de idempotência já existe com dados diferentes."
        )


def persist_pedido(event):
    request_hash = event_request_hash(event)
    redis_key = processed_key(event.idempotency_key)

    # O Redis acelera a detecção de duplicatas; o PostgreSQL
    # continua sendo a proteção durável.
    try:
        cached_hash = redis_client.get(redis_key)
    except redis.RedisError:
        cached_hash = None
        log_event("worker_redis_unavailable")

    if cached_hash is not None:
        if cached_hash != request_hash:
            raise ValueError(
                "Chave de idempotência reutilizada com outro conteúdo."
            )

        return "duplicate"

    with transaction.atomic():
        existing = Pedido.objects.filter(
            idempotency_key=event.idempotency_key
        ).first()

        if existing is not None:
            check_existing_order(existing, event)
            result = "duplicate"
        else:
            item = Item.objects.get(pk=event.item_id)

            Pedido.objects.create(
                id=event.pedido_id,
                item=item,
                quantidade=event.quantidade,
                preco_unitario=event.preco_unitario,
                valor_total=event.valor_total,
                idempotency_key=event.idempotency_key,
                status=Pedido.Status.CRIADO,
            )

            result = "created"

    # Só marca como processado depois do commit no PostgreSQL.
    try:
        redis_client.set(
            redis_key,
            request_hash,
            ex=IDEMPOTENCY_TTL,
        )
    except redis.RedisError:
        log_event("worker_processed_key_write_failed")

    return result


def message_attempt(headers):
    for name, value in headers or []:
        if name == "x-attempt" and value:
            try:
                return int(value.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return 1

    return 1


def make_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        key_serializer=lambda key: (
            key if isinstance(key, bytes)
            else str(key).encode("utf-8")
        ),
        value_serializer=lambda value: json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8"),
        acks="all",
        retries=5,
        max_in_flight_requests_per_connection=1,
    )


def commit_message(consumer, record):
    topic_partition = TopicPartition(
        record.topic,
        record.partition,
    )

    consumer.commit(
        offsets={
            topic_partition: OffsetAndMetadata(
                record.offset + 1,
                "",
            )
        }
    )


def send_retry_or_dlq(producer, record, error):
    attempt = message_attempt(record.headers)

    safe_error = str(error)[:500]
    key = record.key
    value = record.value

    if attempt < MAX_ATTEMPTS:
        next_attempt = attempt + 1
        delay = RETRY_BASE_SECONDS * (2 ** (attempt - 1))

        log_event(
            "worker_retry",
            pedido_key=key,
            attempt=attempt,
            next_attempt=next_attempt,
            backoff_seconds=delay,
            error=safe_error,
        )

        time.sleep(delay)

        future = producer.send(
            MAIN_TOPIC,
            key=key,
            value=value,
            headers=[
                ("x-attempt", str(next_attempt).encode("utf-8")),
                ("x-last-error", safe_error.encode("utf-8")),
            ],
        )

        metadata = future.get(timeout=15)

        log_event(
            "worker_retry_published",
            topic=metadata.topic,
            partition=metadata.partition,
            offset=metadata.offset,
        )

        return

    log_event(
        "worker_dlq",
        pedido_key=key,
        attempts=attempt,
        error=safe_error,
    )

    future = producer.send(
        DLQ_TOPIC,
        key=key,
        value=value,
        headers=[
            ("x-attempts", str(attempt).encode("utf-8")),
            ("x-final-error", safe_error.encode("utf-8")),
        ],
    )

    metadata = future.get(timeout=15)

    log_event(
        "worker_dlq_published",
        topic=metadata.topic,
        partition=metadata.partition,
        offset=metadata.offset,
    )


def main():
    consumer = KafkaConsumer(
        MAIN_TOPIC,
        bootstrap_servers=KAFKA_SERVERS,
        group_id=CONSUMER_GROUP,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        max_poll_records=1,
        key_deserializer=lambda key: (
            key.decode("utf-8") if key else None
        ),
        value_deserializer=lambda value: json.loads(
            value.decode("utf-8")
        ),
    )

    producer = make_producer()

    log_event(
        "worker_started",
        topic=MAIN_TOPIC,
        group=CONSUMER_GROUP,
        max_attempts=MAX_ATTEMPTS,
    )

    try:
        while True:
            batches = consumer.poll(
                timeout_ms=1000,
                max_records=1,
            )

            for topic_partition, records in batches.items():
                for record in records:
                    started = time.perf_counter()

                    try:
                        event = PedidoCriado.model_validate(
                            record.value
                        )

                        outcome = persist_pedido(event)

                        duration_ms = round(
                            (time.perf_counter() - started) * 1000,
                            2,
                        )

                        log_event(
                            "worker_pedido_processed",
                            pedido_id=str(event.pedido_id),
                            outcome=outcome,
                            duration_ms=duration_ms,
                        )

                        commit_message(consumer, record)

                    except Exception as exc:
                        log_event(
                            "worker_processing_error",
                            offset=record.offset,
                            attempt=message_attempt(record.headers),
                            error=str(exc),
                        )

                        try:
                            send_retry_or_dlq(
                                producer,
                                record,
                                exc,
                            )

                            commit_message(consumer, record)

                        except Exception:
                            logger.exception(
                                "Falha ao encaminhar mensagem; "
                                "o offset não será confirmado."
                            )

                            consumer.seek(
                                topic_partition,
                                record.offset,
                            )

                            time.sleep(1)

    finally:
        consumer.close()
        producer.close()


if __name__ == "__main__":
    main()