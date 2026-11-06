from emporio.support.application.ports import DemoCustomer, Reply
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope


class FakeAgent:
    """A ChatAgent that records its calls; satisfies the port without a model or database."""

    def __init__(self, known_customers: tuple[int, ...] = (14, 5)) -> None:
        self.known_customers = known_customers
        self.calls: list[tuple[ChannelIdentity, str]] = []
        self.closed = False
        self.demo_customers = tuple(
            DemoCustomer(i, f"Cliente {i}", "Fortaleza") for i in known_customers
        )

    def handle(self, identity: ChannelIdentity, text: str) -> Reply:
        self.calls.append((identity, text))
        return Reply(bubbles=(f"eco: {text}",), scope=Scope.LOJA, trace_id="trace-fake", tells=())

    def customer_exists(self, customer_id: int) -> bool:
        return customer_id in self.known_customers

    def close(self) -> None:
        self.closed = True
