"""Wiring for repositories and infrastructure clients."""

from demo_shop.infra.email import EmailClient
from demo_shop.infra.payment import PaymentGateway
from demo_shop.persistence.repository import OrderRepository


def build_container() -> dict[str, object]:
    return {
        'orders': OrderRepository(),
        'payments': PaymentGateway(),
        'email': EmailClient(sender='sales@example.com'),
    }
