import json
import logging
import time
import uuid
from datetime import datetime, timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .event_contracts import PedidoCriado
from .idempotency import (
    IdempotencyConflict,
    IdempotencyUnavailable,
    mark_pedido_published,
    release_pedido_key,
    reserve_pedido_key,
)
from .kafka_producer import publish_pedido_criado
from .models import Category, Item
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    PedidoCreateSerializer,
)
from .permissions import IsAdminRole

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("id")
    serializer_class = CategorySerializer
    permission_classes = [IsAdminRole]


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by("id")
    serializer_class = ItemSerializer
    permission_classes = [IsAdminRole]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["category"]
    search_fields = ["name", "description"]
    ordering_fields = ["id", "name", "price", "quantity"]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_pedido(request):
    started_at = time.perf_counter()

    idempotency_key = request.headers.get(
        "Idempotency-Key",
        "",
    ).strip()

    if not idempotency_key:
        return Response(
            {"detail": "O cabeçalho Idempotency-Key é obrigatório."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = PedidoCreateSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )

    item = serializer.validated_data["item"]
    quantidade = serializer.validated_data["quantidade"]

    preco_unitario = item.price
    valor_total = preco_unitario * quantidade

    business_payload = {
        "item_id": item.pk,
        "quantidade": quantidade,
        "preco_unitario": str(preco_unitario),
        "valor_total": str(valor_total),
    }

    pedido_id = uuid.uuid4()

    try:
        reservation = reserve_pedido_key(
            idempotency_key=idempotency_key,
            payload=business_payload,
            pedido_id=pedido_id,
        )
    except IdempotencyConflict as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_409_CONFLICT,
        )
    except IdempotencyUnavailable as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if not reservation["is_new"]:
        return Response(
            {
                "pedido_id": reservation["pedido_id"],
                "status": reservation.get("status", "publishing"),
                "duplicate": True,
                "detail": "Esta chave de idempotência já foi registrada.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    event = PedidoCriado(
        event_id=uuid.uuid4(),
        occurred_at=datetime.now(timezone.utc),
        idempotency_key=idempotency_key,
        pedido_id=reservation["pedido_id"],
        item_id=item.pk,
        quantidade=quantidade,
        preco_unitario=preco_unitario,
        valor_total=valor_total,
    )

    try:
        metadata = publish_pedido_criado(
            event.model_dump(mode="json")
        )
    except Exception:
        logger.exception(
            "Falha ao publicar PedidoCriado no Kafka."
        )

        try:
            release_pedido_key(
                reservation["redis_key"],
                reservation["reservation_id"],
            )
        except IdempotencyUnavailable:
            logger.exception(
                "Não foi possível liberar a reserva de idempotência."
            )

        return Response(
            {"detail": "Não foi possível publicar o pedido."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        mark_pedido_published(
            reservation["redis_key"],
            reservation["reservation_id"],
            metadata,
        )
    except IdempotencyUnavailable:
        logger.exception(
            "Evento publicado, mas não foi possível atualizar "
            "o estado da chave de idempotência."
        )

    duration_ms = round(
        (time.perf_counter() - started_at) * 1000,
        2,
    )

    logger.info(
        json.dumps(
            {
                "event": "pedido_event_published",
                "pedido_id": str(reservation["pedido_id"]),
                "topic": metadata["topic"],
                "partition": metadata["partition"],
                "offset": metadata["offset"],
                "duration_ms": duration_ms,
            },
            ensure_ascii=False,
        )
    )

    return Response(
        {
            "pedido_id": reservation["pedido_id"],
            "status": "ENFILEIRADO",
            "event": "PedidoCriado",
            "topic": metadata["topic"],
            "partition": metadata["partition"],
            "offset": metadata["offset"],
            "duplicate": False,
        },
        status=status.HTTP_202_ACCEPTED,
    )