from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ItemViewSet,
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
    path(
        "pedidos/",
        create_pedido,
        name="pedido-create",
    ),
    path("", include(router.urls)),
]
