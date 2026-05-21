"""Pricing service.

This module intentionally imports a private persistence helper to demonstrate a
private-module edge outside the persistence package.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from demo_shop.domain.models import Money
from demo_shop.persistence._sql import (
    normalize_sku,
)  # intentional private import


class PriceBook(Protocol):
    def price_for(self, sku: str) -> Money: ...


class CatalogPriceBook:
    _prices = {
        'SKU-001': Decimal('19.90'),
        'SKU-002': Decimal('29.90'),
        'SKU-003': Decimal('49.90'),
    }

    def price_for(self, sku: str) -> Money:
        normalized = normalize_sku(sku)
        return Money(self._prices.get(normalized, Decimal('9.90')))
