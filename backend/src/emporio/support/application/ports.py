from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol

from emporio.shared.errors import DomainError
from emporio.support.domain.ai_tells import Tell
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope


@dataclass(frozen=True)
class TurnMetrics:
    thread_id: str
    provider: str
    model: str
    scope: Scope
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    llm_calls: int
    tools: tuple[str, ...]
    ms_total: int
    ms_guard: int
    ms_llm: int
    ms_tools: int
    cost_brl: Decimal | None
    trace_id: str
    failed: bool = False  # the turn ended in the fixed error reply


@dataclass(frozen=True)
class Reply:
    bubbles: tuple[str, ...]
    scope: Scope
    trace_id: str
    tells: tuple[Tell, ...]
    metrics: TurnMetrics | None = None
    failed: bool = False


class AgentRunner(Protocol):
    def run(self, identity: ChannelIdentity, text: str) -> tuple[str, Scope, TurnMetrics]: ...


class MetricsStore(Protocol):
    def save(self, m: TurnMetrics) -> None: ...


@dataclass(frozen=True)
class DemoCustomer:
    id: int
    name: str
    city: str


class ChatAgent(Protocol):
    """What the web layer needs from the agent; `bootstrap.Agent` satisfies it."""

    @property
    def handle(self) -> Callable[[ChannelIdentity, str], Reply]: ...

    @property
    def customer_exists(self) -> Callable[[int], bool]: ...

    @property
    def demo_customers(self) -> tuple[DemoCustomer, ...]: ...

    @property
    def close(self) -> Callable[[], None]: ...


@dataclass(frozen=True)
class ProductInput:
    """One product as a demo user submits it (primitives only: no catalog types here)."""

    name: str
    category_id: int
    description: str
    price: Decimal
    stock: int
    status: str
    specs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ProductView:
    id: int
    name: str
    category_id: int
    category: str
    description: str
    price: Decimal
    stock: int
    status: str
    specs: tuple[tuple[str, str], ...]


RejectionCode = Literal["unknown_category", "not_found", "catalog_full", "catalog_unavailable"]


class CatalogWriteRejected(DomainError):
    def __init__(self, code: RejectionCode) -> None:
        super().__init__(code)
        self.code: RejectionCode = code


class CatalogAdmin(Protocol):
    """What the web layer may do to the catalog: demo users create and edit their own rows."""

    def categories(self) -> tuple[tuple[int, str], ...]: ...

    def create(self, owner: str, data: ProductInput) -> ProductView: ...

    def update(self, owner: str, product_id: int, data: ProductInput) -> ProductView: ...

    def mine(self, owner: str) -> tuple[ProductView, ...]:
        """Newest first."""
        ...
