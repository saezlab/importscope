"""Optional discount plugin.

This file is intentionally not imported by the main application path. It gives
importscope a leaf module to report.
"""

from decimal import Decimal

from demo_shop.domain.models import Money, Order


def apply_loyalty_discount(order: Order) -> Money:
    return Money(order.total.amount * Decimal('0.90'), order.total.currency)
