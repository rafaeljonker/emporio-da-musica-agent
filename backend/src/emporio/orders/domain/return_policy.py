from dataclasses import dataclass
from datetime import date, timedelta

from emporio.orders.domain.order import Order, OrderStatus

REGRET_DAYS = 7
DEFECT_DAYS = 30


@dataclass(frozen=True)
class ReturnEligibility:
    regret_eligible: bool
    defect_eligible: bool
    delivered_on: date | None
    regret_deadline: date | None
    defect_deadline: date | None
    reason: str


def check_return(order: Order, today: date) -> ReturnEligibility:
    """Return and exchange eligibility for an order on `today`.

    Only delivered orders qualify. The data has no actual delivery date, so
    `estimated_delivery` stands in for it (documented assumption). Deadlines
    are inclusive.

    Reason codes:
      cancelled              order was cancelled
      not_delivered          pending, confirmed or shipped
      no_delivery_date       delivered but no delivery date: regret window unknown
      within_regret_window   regret (7 days after delivery) still open
      within_defect_window   regret closed, defect (30 days after purchase) open
      regret_window_closed   both windows closed
    """
    if order.status is OrderStatus.CANCELLED:
        return ReturnEligibility(False, False, None, None, None, "cancelled")
    if order.status is not OrderStatus.DELIVERED:
        return ReturnEligibility(False, False, None, None, None, "not_delivered")

    delivered_on = order.estimated_delivery
    regret_deadline = None if delivered_on is None else delivered_on + timedelta(days=REGRET_DAYS)
    defect_deadline = order.order_date + timedelta(days=DEFECT_DAYS)
    regret = regret_deadline is not None and today <= regret_deadline
    defect = today <= defect_deadline
    if delivered_on is None:
        reason = "no_delivery_date"
    elif regret:
        reason = "within_regret_window"
    elif defect:
        reason = "within_defect_window"
    else:
        reason = "regret_window_closed"
    return ReturnEligibility(regret, defect, delivered_on, regret_deadline, defect_deadline, reason)
