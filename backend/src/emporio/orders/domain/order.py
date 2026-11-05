from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from emporio.shared.money import Money


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Customer:
    id: int
    name: str
    phone: str
    email: str
    city: str


@dataclass(frozen=True, slots=True)
class OrderItem:
    product_id: int
    quantity: int


@dataclass(frozen=True, slots=True)
class Order:
    id: int
    customer_id: int
    order_date: date
    status: OrderStatus
    total: Money
    payment_method: str
    tracking_code: str | None
    estimated_delivery: date | None
    notes: str | None
    items: tuple[OrderItem, ...]
