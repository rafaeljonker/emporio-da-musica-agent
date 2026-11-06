import threading
from decimal import Decimal

from emporio.support.application.ports import DemoCustomer, Reply, TurnMetrics
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope


def turn_metrics(
    tools: tuple[str, ...] = (),
    cost_brl: Decimal | None = None,
    failed: bool = False,
    provider: str = "gemma",
) -> TurnMetrics:
    return TurnMetrics(
        "web:anon:s", provider, "m", Scope.LOJA, 120, 30, 0, 1, tools, 900, 40, 700, 100, cost_brl,
        "trace-fake", failed,
    )  # fmt: skip


class FakeAgent:
    """A ChatAgent that records its calls; satisfies the port without a model or database.

    `reply` overrides the echo, `error` is raised by `handle`, and `block` (when set) holds
    `handle` until the test sets it, after setting `entered`.
    """

    def __init__(self, known_customers: tuple[int, ...] = (14, 5)) -> None:
        self.known_customers = known_customers
        self.calls: list[tuple[ChannelIdentity, str]] = []
        self.closed = False
        self.reply: Reply | None = None
        self.error: Exception | None = None
        self.block: threading.Event | None = None
        self.entered = threading.Event()
        self.demo_customers = tuple(
            DemoCustomer(i, f"Cliente {i}", "Fortaleza") for i in known_customers
        )

    def handle(self, identity: ChannelIdentity, text: str) -> Reply:
        self.calls.append((identity, text))
        self.entered.set()
        if self.block is not None:
            self.block.wait(timeout=5)
        if self.error is not None:
            raise self.error
        if self.reply is not None:
            return self.reply
        return Reply(
            bubbles=(f"eco: {text}",),
            scope=Scope.LOJA,
            trace_id="trace-fake",
            tells=(),
            metrics=turn_metrics(),
        )

    def customer_exists(self, customer_id: int) -> bool:
        return customer_id in self.known_customers

    def close(self) -> None:
        self.closed = True
