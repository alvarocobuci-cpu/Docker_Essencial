from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from aula4api.views import CategoryViewSet, ItemViewSet


router = DefaultRouter()

router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'items', ItemViewSet, basename='item')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
]