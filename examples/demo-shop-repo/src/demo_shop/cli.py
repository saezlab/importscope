"""Command-line facade for exercising the demo package."""

from __future__ import annotations

import argparse

from demo_shop.api.routes import create_order_endpoint
from demo_shop.api.schemas import CreateOrderRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='demo-shop')
    subcommands = parser.add_subparsers(dest='command', required=True)

    create = subcommands.add_parser('create-order')
    create.add_argument('email')
    create.add_argument('sku')
    create.add_argument('quantity', type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == 'create-order':
        request = CreateOrderRequest(
            customer_email=args.email,
            sku=args.sku,
            quantity=args.quantity,
        )
        response = create_order_endpoint(request)
        print(response)
        return 0

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
