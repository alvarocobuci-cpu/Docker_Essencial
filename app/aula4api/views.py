from rest_framework import viewsets

from .models import Category, Item
from .serializers import CategorySerializer, ItemSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('id')
    serializer_class = CategorySerializer


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by('id')
    serializer_class = ItemSerializer