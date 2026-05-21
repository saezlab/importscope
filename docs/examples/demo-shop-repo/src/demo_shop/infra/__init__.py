"""Infrastructure adapters."""

from demo_shop.infra.email import EmailClient
from demo_shop.infra.payment import PaymentGateway

__all__ = ['EmailClient', 'PaymentGateway']
