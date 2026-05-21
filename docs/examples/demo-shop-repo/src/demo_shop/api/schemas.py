"""DTOs for the API layer."""

from __future__ import annotations

from dataclasses import dataclass

from demo_shop.domain.models import Order


@dataclass(frozen=True)
class CreateOrderRequest:
    customer_email: str
    sku: str
    quantity: int


@dataclass(frozen=True)
class OrderResponse:
    order_id: str
    total: str
    status: str

    @classmethod
    def from_domain(cls, order: Order) -> OrderResponse:
        return cls(
            order_id=order.order_id,
            total=f'{order.total.amount:.2f} {order.total.currency}',
            status=order.status,
        )
