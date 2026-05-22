"""In-memory repository used by the demo."""

from __future__ import annotations

from demo_shop.domain.models import Order
from demo_shop.persistence._sql import quote_identifier


class OrderRepository:
    _orders: list[Order] = []

    def save(self, order: Order) -> None:
        quote_identifier('orders')
        self._orders.append(order)

    def find_by_customer(self, customer_email: str) -> list[Order]:
        return [
            order
            for order in self._orders
            if order.customer_email == customer_email
        ]
