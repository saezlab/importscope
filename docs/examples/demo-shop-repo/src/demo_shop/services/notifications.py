"""Notification service with a lazy infrastructure import."""

from __future__ import annotations

from demo_shop.domain.models import Order


def send_order_confirmation(order: Order) -> None:
    # Lazy import: keeps email infrastructure out of import time.
    from demo_shop.infra.email import EmailClient

    EmailClient(sender='sales@example.com').send(
        to=order.customer_email,
        subject=f'Order {order.order_id} received',
        body=f'Total: {order.total.amount:.2f} {order.total.currency}',
    )
