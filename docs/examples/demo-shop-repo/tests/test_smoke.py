from demo_shop.services.orders import place_order


def test_place_order() -> None:
    order = place_order('alice@example.com', 'SKU-001', 2)

    assert order.customer_email == 'alice@example.com'
    assert order.total.amount > 0
