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


class PedidoCreateSerializer(serializers.Serializer):
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(),
        source="item",
    )

    quantidade = serializers.IntegerField(
        min_value=1,
    )
class AssistRequestSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(
        choices=("summarize", "explain")
    )
    logs = serializers.JSONField()
    temperature = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        required=False,
        default=0.2,
    )
    max_tokens = serializers.IntegerField(
        min_value=1,
        max_value=256,
        required=False,
        default=256,
    )

    def validate_logs(self, value):
        if isinstance(value, str):
            if not value.strip():
                raise serializers.ValidationError(
                    "Informe o conteudo dos logs."
                )
            return value

        if isinstance(value, list):
            if not value:
                raise serializers.ValidationError(
                    "A lista de logs nao pode estar vazia."
                )
            if any(
                not isinstance(item, str) or not item.strip()
                for item in value
            ):
                raise serializers.ValidationError(
                    "A lista deve conter somente textos nao vazios."
                )
            return value

        raise serializers.ValidationError(
            "Informe logs como texto ou lista de textos."
        )
