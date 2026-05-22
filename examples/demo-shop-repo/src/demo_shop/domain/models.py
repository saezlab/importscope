"""Domain objects.

The `load_previous_orders` method contains an intentional lazy boundary
violation: domain code reaches into persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from demo_shop.domain.errors import InvalidOrder

if TYPE_CHECKING:
    from demo_shop.services.pricing import PriceBook


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = 'EUR'

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise InvalidOrder('cannot add money in different currencies')
        return Money(self.amount + other.amount, self.currency)


@dataclass(frozen=True)
class LineItem:
    sku: str
    quantity: int
    unit_price: Money

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise InvalidOrder('quantity must be positive')

    @property
    def subtotal(self) -> Money:
        return Money(
            self.unit_price.amount * self.quantity, self.unit_price.currency
        )


@dataclass
class Order:
    customer_email: str
    items: list[LineItem]
    order_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = 'created'

    @property
    def total(self) -> Money:
        current = Money(Decimal('0.00'))
        for item in self.items:
            current = current + item.subtotal
        return current

    def load_previous_orders(self) -> list[Order]:
        # Intentional lazy import to demonstrate importscope's direct/lazy edge handling.
        from demo_shop.persistence.repository import OrderRepository

        return OrderRepository().find_by_customer(self.customer_email)

    @classmethod
    def from_sku(
        cls,
        customer_email: str,
        sku: str,
        quantity: int,
        price_book: PriceBook,
    ) -> Order:
        price = price_book.price_for(sku)
        return cls(
            customer_email=customer_email,
            items=[LineItem(sku=sku, quantity=quantity, unit_price=price)],
        )
