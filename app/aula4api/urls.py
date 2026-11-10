from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ItemViewSet,
    ask_docs,
    ask_sql,
    assist,
    create_pedido,
)


router = DefaultRouter()

router.register(
    r"categories",
    CategoryViewSet,
    basename="category",
)

router.register(
    r"items",
    ItemViewSet,
    basename="item",
)


urlpatterns = [
    path("assist", assist, name="assist"),
    path("ask_sql", ask_sql, name="ask-sql"),
    path("ask_docs", ask_docs, name="ask-docs"),
    path(
        "pedidos/",
        create_pedido,
        name="pedido-create",
    ),
    path("", include(router.urls)),
]
