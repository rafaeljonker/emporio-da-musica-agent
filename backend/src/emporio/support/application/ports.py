from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from emporio.support.domain.ai_tells import Tell
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope


@dataclass(frozen=True)
class Reply:
    bubbles: tuple[str, ...]
    scope: Scope
    trace_id: str
    tells: tuple[Tell, ...]


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


class AgentRunner(Protocol):
    def run(self, identity: ChannelIdentity, text: str) -> tuple[str, Scope, TurnMetrics]: ...


class MetricsStore(Protocol):
    def save(self, m: TurnMetrics) -> None: ...
