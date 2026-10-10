import json
import logging
import os
import sys
import time

import redis
from django.db import transaction
from kafka import KafkaConsumer, KafkaProducer
from kafka.structs import OffsetAndMetadata, TopicPartition

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from aula4api.event_contracts import PagamentoProcessado, NotificacaoEnviada
from aula4api.models import Notificacao, Pagamento, Pedido

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("synapseshop.notification_worker")

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
INPUT_TOPIC = "pagamentos.processados"
OUTPUT_TOPIC = "notificacoes.enviadas"
DLQ_TOPIC = "pagamentos.processados.dlq"
CONSUMER_GROUP = "notificacoes-worker-v1"
MAX_ATTEMPTS = int(os.getenv("PEDIDOS_MAX_ATTEMPTS", "3"))
RETRY_BASE_SECONDS = float(os.getenv("PEDIDOS_RETRY_BASE_SECONDS", "1"))
CACHE_TTL = int(os.getenv("PEDIDO_IDEMPOTENCY_TTL_SECONDS", "86400"))

redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def log_event(name, **details):
    logger.info(json.dumps(
        {"event": name, **details},
        ensure_ascii=False,
        default=str,
    ))


def make_producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        key_serializer=lambda key: (
            key if isinstance(key, bytes) else str(key).encode("utf-8")
        ),
        value_serializer=lambda value: json.dumps(
            value, ensure_ascii=False, default=str
        ).encode("utf-8"),
        acks="all",
        retries=5,
        max_in_flight_requests_per_connection=1,
    )


def commit_message(consumer, record):
    tp = TopicPartition(record.topic, record.partition)
    consumer.commit(
        offsets={tp: OffsetAndMetadata(record.offset + 1, "")}
    )


def persist_notification(event):
    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=event.pedido_id)
        pagamento = Pagamento.objects.get(pedido=pedido)

        if (
            pagamento.id != event.pagamento_id
            or pagamento.valor != event.valor
            or pagamento.status != event.status
            or pagamento.referencia_simulada != event.referencia_simulada
        ):
            raise ValueError("O evento de pagamento diverge do registro persistido.")

        if event.status == Pagamento.Status.APROVADO:
            mensagem = f"Pagamento aprovado para o pedido {pedido.id}."
        else:
            mensagem = f"Pagamento recusado para o pedido {pedido.id}."

        notification, created = Notificacao.objects.get_or_create(
            pedido=pedido,
            defaults={
                "canal": "INTERNO",
                "status": Notificacao.Status.ENVIADA,
                "mensagem": mensagem,
            },
        )

        if notification.mensagem != mensagem:
            raise ValueError("Ja existe uma notificacao diferente para este pedido.")

        if pedido.status != Pedido.Status.NOTIFICADO:
            pedido.status = Pedido.Status.NOTIFICADO
            pedido.save(update_fields=["status"])

        result = NotificacaoEnviada(
            event_id=notification.id,
            occurred_at=notification.created_at,
            pedido_id=pedido.id,
            pagamento_status=event.status,
            canal="INTERNO",
            mensagem=notification.mensagem,
        )

    try:
        redis_client.set(
            f"synapseshop:notificacao:{event.pedido_id}",
            result.model_dump_json(),
            ex=CACHE_TTL,
        )
    except redis.RedisError:
        log_event("notification_redis_cache_update_failed")

    return result.model_dump(mode="json"), created


def attempt_number(headers):
    for name, value in headers or []:
        if name == "x-attempt" and value:
            try:
                return int(value.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return 1
    return 1


def retry_or_dlq(producer, record, error):
    attempt = attempt_number(record.headers)
    safe_error = str(error)[:500]

    if attempt < MAX_ATTEMPTS:
        next_attempt = attempt + 1
        delay = RETRY_BASE_SECONDS * (2 ** (attempt - 1))
        log_event(
            "notification_retry",
            attempt=attempt,
            next_attempt=next_attempt,
            backoff_seconds=delay,
            error=safe_error,
        )
        time.sleep(delay)
        metadata = producer.send(
            INPUT_TOPIC,
            key=record.key,
            value=record.value,
            headers=[("x-attempt", str(next_attempt).encode("utf-8"))],
        ).get(timeout=15)
        log_event(
            "notification_retry_published",
            topic=metadata.topic,
            partition=metadata.partition,
            offset=metadata.offset,
        )
        return

    metadata = producer.send(
        DLQ_TOPIC,
        key=record.key,
        value=record.value,
        headers=[
            ("x-attempts", str(attempt).encode("utf-8")),
            ("x-final-error", safe_error.encode("utf-8")),
        ],
    ).get(timeout=15)
    log_event(
        "notification_dlq_published",
        topic=metadata.topic,
        partition=metadata.partition,
        offset=metadata.offset,
    )


def main():
    consumer = KafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=KAFKA_SERVERS,
        group_id=CONSUMER_GROUP,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        max_poll_records=1,
        key_deserializer=lambda key: key.decode("utf-8") if key else None,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    producer = make_producer()
    log_event(
        "notification_worker_started",
        topic=INPUT_TOPIC,
        group=CONSUMER_GROUP,
        max_attempts=MAX_ATTEMPTS,
    )

    try:
        while True:
            batches = consumer.poll(timeout_ms=1000, max_records=1)
            for tp, records in batches.items():
                for record in records:
                    try:
                        event = PagamentoProcessado.model_validate(record.value)
                        payload, created = persist_notification(event)
                        metadata = producer.send(
                            OUTPUT_TOPIC,
                            key=str(event.pedido_id),
                            value=payload,
                        ).get(timeout=15)
                        log_event(
                            "notification_processed",
                            pedido_id=str(event.pedido_id),
                            outcome="created" if created else "existing",
                            topic=metadata.topic,
                            partition=metadata.partition,
                            offset=metadata.offset,
                        )
                        commit_message(consumer, record)
                    except Exception as exc:
                        log_event(
                            "notification_processing_error",
                            offset=record.offset,
                            attempt=attempt_number(record.headers),
                            error=str(exc),
                        )
                        try:
                            retry_or_dlq(producer, record, exc)
                            commit_message(consumer, record)
                        except Exception:
                            logger.exception(
                                "Falha ao encaminhar notificacao; offset nao confirmado."
                            )
                            consumer.seek(tp, record.offset)
                            time.sleep(1)
    finally:
        consumer.close()
        producer.close()


if __name__ == "__main__":
    main()
