"""Order orchestration service."""

from __future__ import annotations

from demo_shop.domain.models import Order
from demo_shop.infra.payment import PaymentGateway
from demo_shop.persistence.repository import OrderRepository
from demo_shop.services.notifications import send_order_confirmation
from demo_shop.services.pricing import CatalogPriceBook, PriceBook


def place_order(
    customer_email: str,
    sku: str,
    quantity: int,
    *,
    price_book: PriceBook | None = None,
    repository: OrderRepository | None = None,
    payment_gateway: PaymentGateway | None = None,
) -> Order:
    price_book = price_book or CatalogPriceBook()
    repository = repository or OrderRepository()
    payment_gateway = payment_gateway or PaymentGateway()

    order = Order.from_sku(customer_email, sku, quantity, price_book)
    payment_gateway.authorize(order.total)
    repository.save(order)
    send_order_confirmation(order)
    return order
