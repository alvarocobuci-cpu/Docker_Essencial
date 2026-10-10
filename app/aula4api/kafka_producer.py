import json
import os

from kafka import KafkaProducer


TOPIC_PEDIDO_CRIADO = "pedidos.criado"

_producer = None


def get_kafka_producer():
    global _producer

    if _producer is None:
        bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            "localhost:9092",
        )

        _producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            key_serializer=lambda key: key.encode("utf-8"),
            value_serializer=lambda value: json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8"),
            acks="all",
            retries=5,
            max_in_flight_requests_per_connection=1,
        )

    return _producer


def publish_pedido_criado(event: dict):
    producer = get_kafka_producer()

    future = producer.send(
        TOPIC_PEDIDO_CRIADO,
        key=str(event["pedido_id"]),
        value=event,
    )

    metadata = future.get(timeout=10)

    return {
        "topic": metadata.topic,
        "partition": metadata.partition,
        "offset": metadata.offset,
    }