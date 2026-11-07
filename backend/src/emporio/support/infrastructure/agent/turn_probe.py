"""Per-turn timings, model calls and token usage, read from LangChain callbacks."""

from threading import Lock
from time import perf_counter
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import LLMResult


def to_ms(seconds: float) -> int:
    return round(seconds * 1000)


class TurnProbe(BaseCallbackHandler):
    """Per-turn timings, model calls, token usage and tool names, read from callbacks.

    Callbacks also see the guard's classifier call, which never reaches graph state.
    Tools of one message run in parallel, so `ms_tools` sums their durations. LLM time spent
    inside the guard counts only in `ms_guard`, so ms_guard + ms_llm + ms_tools is roughly
    at most ms_total (parallel tools can exceed it). Callbacks may fire from tool threads,
    so every update takes one lock.
    """

    def __init__(self) -> None:
        self._started: dict[UUID, float] = {}
        self.llm_calls = 0
        self.ms_llm = 0.0
        self.ms_tools = 0.0
        self.ms_guard = 0.0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cached_tokens = 0
        # Share of the totals above spent by the guard (priced at the guard model).
        self.guard_input_tokens = 0
        self.guard_output_tokens = 0
        self.guard_cached_tokens = 0
        self.tools: list[str] = []
        self._guard_runs: set[UUID] = set()
        self._parents: dict[UUID, UUID | None] = {}
        self._lock = Lock()

    def _in_guard(self, run_id: UUID | None) -> bool:
        while run_id is not None:
            if run_id in self._guard_runs:
                return True
            run_id = self._parents.get(run_id)
        return False

    def _start(self, run_id: UUID) -> None:
        self._started[run_id] = perf_counter()

    def _elapsed(self, run_id: UUID) -> float:
        return perf_counter() - self._started.pop(run_id, perf_counter())

    def on_chain_start(
        self,
        serialized: dict[str, object] | None,
        inputs: object,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        with self._lock:
            self._parents[run_id] = parent_run_id
            if kwargs.get("name") == "guard":
                self._guard_runs.add(run_id)
                self._start(run_id)

    def on_chain_end(
        self, outputs: object, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: object
    ) -> None:
        with self._lock:
            if run_id in self._guard_runs:
                self.ms_guard += self._elapsed(run_id)

    def on_chat_model_start(
        self,
        serialized: dict[str, object] | None,
        messages: object,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        with self._lock:
            self._parents[run_id] = parent_run_id
            self.llm_calls += 1
            self._start(run_id)

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        with self._lock:
            elapsed = self._elapsed(run_id)
            in_guard = self._in_guard(self._parents.get(run_id))
            if not in_guard:
                self.ms_llm += elapsed
            for generation in response.generations[0][:1]:
                message = getattr(generation, "message", None)
                usage = message.usage_metadata if isinstance(message, AIMessage) else None
                if usage:
                    cached = (usage.get("input_token_details") or {}).get("cache_read", 0)
                    self.input_tokens += usage["input_tokens"]
                    self.output_tokens += usage["output_tokens"]
                    self.cached_tokens += cached
                    if in_guard:
                        self.guard_input_tokens += usage["input_tokens"]
                        self.guard_output_tokens += usage["output_tokens"]
                        self.guard_cached_tokens += cached

    def on_tool_start(
        self,
        serialized: dict[str, object] | None,
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: object,
    ) -> None:
        with self._lock:
            self.tools.append(str(kwargs.get("name") or (serialized or {}).get("name")))
            self._start(run_id)

    def on_tool_end(
        self, output: object, *, run_id: UUID, parent_run_id: UUID | None = None, **kwargs: object
    ) -> None:
        with self._lock:
            self.ms_tools += self._elapsed(run_id)
