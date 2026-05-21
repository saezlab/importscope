"""Toy route handlers.

This module intentionally imports a private persistence helper so importscope has
something policy-oriented to report.
"""

from __future__ import annotations

from demo_shop.api.schemas import CreateOrderRequest, OrderResponse
from demo_shop.persistence._sql import (
    quote_identifier,
)  # intentional private import
from demo_shop.services.orders import place_order


def create_order_endpoint(request: CreateOrderRequest) -> OrderResponse:
    # Useless in a real handler, useful for demonstrating a private import edge.
    quote_identifier('orders')

    order = place_order(
        customer_email=request.customer_email,
        sku=request.sku,
        quantity=request.quantity,
    )
    return OrderResponse.from_domain(order)
