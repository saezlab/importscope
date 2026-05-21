"""Private SQL-ish helpers.

The leading underscore is intentional: imports from this module are useful for
private-import demos.
"""


def normalize_sku(sku: str) -> str:
    return sku.strip().upper()


def quote_identifier(identifier: str) -> str:
    if not identifier.replace('_', '').isalnum():
        raise ValueError(f'unsafe SQL identifier: {identifier!r}')
    return f'"{identifier}"'
