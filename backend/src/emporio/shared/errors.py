class DomainError(Exception):
    """Base class for every business-rule error raised by the domains."""


class StoreUnavailable(Exception):
    """The database behind the catalog or a search index cannot be reached (unexpected)."""
