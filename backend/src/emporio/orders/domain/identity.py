from emporio.orders.domain.order import Customer


def normalize_phone(raw: str) -> str:
    digits = "".join(c for c in raw if c.isascii() and c.isdigit())
    if len(digits) in (12, 13) and digits.startswith("55"):
        return digits[2:]
    return digits


def _email(raw: str) -> str:
    return raw.strip().casefold()


def matches_identity(customer: Customer, email_or_phone: str) -> bool:
    if "@" in email_or_phone:
        return _email(customer.email) == _email(email_or_phone)
    # No suffix matching: a number without DDD never matches (no partial auth).
    wanted = normalize_phone(email_or_phone)
    return wanted != "" and wanted == normalize_phone(customer.phone)
