import uuid

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=0)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="items",
    )

    def __str__(self):
        return self.name


class Pedido(models.Model):
    class Status(models.TextChoices):
        CRIADO = "CRIADO", "Criado"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )

    quantidade = models.PositiveIntegerField()

    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CRIADO,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido {self.id} - {self.status}"