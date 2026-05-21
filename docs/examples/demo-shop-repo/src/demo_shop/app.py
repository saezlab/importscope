"""Application assembly for the demo shop."""

from demo_shop.api.routes import create_order_endpoint
from demo_shop.container import build_container


def create_app() -> dict[str, object]:
    """Return a tiny app dictionary instead of depending on a web framework."""
    container = build_container()
    return {
        'routes': {
            'POST /orders': create_order_endpoint,
        },
        'container': container,
    }
