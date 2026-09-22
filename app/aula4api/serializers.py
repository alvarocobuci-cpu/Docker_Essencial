from rest_framework import serializers

from .models import Category, Item


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                'O nome da categoria não pode ficar vazio.'
            )

        return value


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            'id',
            'name',
            'description',
            'price',
            'quantity',
            'category',
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                'O nome do item não pode ficar vazio.'
            )

        return value

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'O preço não pode ser negativo.'
            )

        return value

    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'A quantidade não pode ser negativa.'
            )

        return value