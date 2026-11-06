from dataclasses import dataclass
from datetime import date

from emporio.shared.clock import DEFAULT_STORE_TODAY


@dataclass(frozen=True)
class TurnContext:
    """Server-side facts of the turn; never visible to the model as tool arguments.

    `customer_name` and `today` only feed the dynamic tail of the system prompt.
    """

    customer_id: int | None
    customer_name: str | None = None
    today: date = DEFAULT_STORE_TODAY
