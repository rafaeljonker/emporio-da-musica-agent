from dataclasses import dataclass


@dataclass(frozen=True)
class TurnContext:
    """Server-side identity of the turn; never visible to the model."""

    customer_id: int | None
