"""Payment adapter stub."""

from __future__ import annotations

from demo_shop.domain.models import Money


class PaymentGateway:
    def authorize(self, amount: Money) -> str:
        return f'auth:{amount.amount}:{amount.currency}'
