from datetime import date

from emporio.orders.domain.order import Customer, Order, OrderItem, OrderStatus
from emporio.shared.money import Money


def cust(
    *,
    id: int = 1,
    name: str = "Pedro Oliveira",
    phone: str = "(67) 98432-1098",
    email: str = "pedro.oliveira@jmail.com",
    city: str = "Campo Grande",
) -> Customer:
    return Customer(id, name, phone, email, city)


def order(
    *,
    id: int = 1,
    customer_id: int = 1,
    order_date: date = date(2026, 2, 1),
    status: OrderStatus = OrderStatus.DELIVERED,
    total: str = "1000",
    payment_method: str = "pix",
    tracking_code: str | None = None,
    estimated_delivery: date | None = date(2026, 2, 10),
    notes: str | None = None,
    items: tuple[OrderItem, ...] = (OrderItem(1, 1),),
) -> Order:
    return Order(
        id,
        customer_id,
        order_date,
        status,
        Money.from_str(total),
        payment_method,
        tracking_code,
        estimated_delivery,
        notes,
        items,
    )
