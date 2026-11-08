from enum import StrEnum


class CatalogErrorCode(StrEnum):
    """Expected catalog failures. The values are wire codes: change none of them."""

    PRODUCT_NOT_FOUND = "product_not_found"
    UNKNOWN_CATEGORY = "unknown_category"
    # Missing, seed or another login's product; callers cannot tell them apart.
    PRODUCT_NOT_OWNED = "not_found"
    CATALOG_FULL = "catalog_full"
    # A demo product may not reuse a store product's name (case and accents ignored).
    NAME_TAKEN_BY_STORE = "name_taken_by_store"
    # Name or description claims a discount; only promotion rows carry one.
    PROMO_CLAIM = "promo_claim"
    INSTALLMENTS_NOT_ALLOWED = "installments_not_allowed"
    # Produced only by the admin service, when the store's database is unreachable.
    CATALOG_UNAVAILABLE = "catalog_unavailable"
