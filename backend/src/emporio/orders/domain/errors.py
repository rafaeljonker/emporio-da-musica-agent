from enum import StrEnum


class OrdersErrorCode(StrEnum):
    """Expected order failures."""

    # Unknown order, another customer's order and a wrong e-mail or phone all look the same:
    # one code, so no answer tells an order id exists (anti-enumeration).
    ORDER_NOT_FOUND = "order_not_found"
