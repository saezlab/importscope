"""Domain exceptions."""


class DomainError(Exception):
    """Base class for domain failures."""


class InvalidOrder(DomainError):
    """Raised when an order cannot be created."""
