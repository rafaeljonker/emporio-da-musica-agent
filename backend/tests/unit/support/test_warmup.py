import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import httpx

from emporio.support.application.warmup import WarmMode, WarmStage
from emporio.support.infrastructure.warmup import ProbeWarmup, ReadyWarmup, vllm_health_probe

T0 = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


class StepClock:
    """A clock that only moves when the test says so."""

    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


def _warm(
    probe: Callable[[], bool], clock: StepClock, deadline_seconds: float = 600
) -> ProbeWarmup:
    return ProbeWarmup(
        probe,
        WarmMode.MODAL_GPU,
        180,
        lambda: 4.2,
        deadline_seconds=deadline_seconds,
        clock=clock,
        interval_seconds=0.001,
    )


def test_provider_api_is_ready_at_once():
    status = ReadyWarmup(WarmMode.PROVIDER_API, lambda: 3.0).start()
    assert (status.stage, status.expected_seconds, status.reply_p50_seconds) == (
        WarmStage.READY,
        0,
        3.0,
    )


def test_probe_treats_303_and_timeout_as_starting():
    calls: list[httpx.Request] = []
    outcomes = iter([303, httpx.ReadTimeout("slow"), 200])

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return httpx.Response(outcome)

    probe = vllm_health_probe(
        "https://vllm.example.test/v1", "k3y", transport=httpx.MockTransport(handler)
    )
    assert [probe(), probe(), probe()] == [False, False, True]
    assert {r.url.path for r in calls} == {"/health"}
    assert calls[0].headers["authorization"] == "Bearer k3y"


def test_probe_fails_after_deadline():
    clock = StepClock()

    def probe() -> bool:
        clock.advance(400)
        return False

    warm = _warm(probe, clock, deadline_seconds=600)
    warm.start()
    warm.join(5)
    assert warm.status().stage is WarmStage.FAILED


def test_retry_keeps_started_at():
    clock = StepClock()
    healthy = [False]

    def probe() -> bool:
        clock.advance(700)
        return healthy[0]

    warm = _warm(probe, clock, deadline_seconds=600)
    first = warm.start().started_at
    warm.join(5)
    assert warm.status().stage is WarmStage.FAILED
    healthy[0] = True
    assert warm.start().started_at == first
    warm.join(5)
    assert warm.status().stage is WarmStage.READY


def test_start_is_single_flight():
    release = threading.Event()
    probe_calls = 0

    def probe() -> bool:
        nonlocal probe_calls
        probe_calls += 1
        release.wait(5)
        return True

    warm = _warm(probe, StepClock())
    workers = [threading.Thread(target=warm.start) for _ in range(10)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    release.set()
    warm.join(5)
    assert probe_calls == 1


def test_status_starts_the_probe_when_it_never_ran():
    warm = _warm(lambda: True, StepClock())
    warm.status()
    warm.join(5)
    assert warm.status().stage is WarmStage.READY


def test_elapsed_is_server_computed_and_freezes_at_ready():
    clock = StepClock()
    ready = threading.Event()
    warm = _warm(lambda: ready.is_set(), clock)
    assert warm.start().stage is WarmStage.SERVER_STARTING
    clock.advance(42)
    assert warm.status().elapsed_seconds == 42
    ready.set()
    warm.join(5)
    clock.advance(1000)
    done = warm.status()
    assert (done.stage, done.elapsed_seconds, done.expected_seconds) == (WarmStage.READY, 42, 180)
    assert done.reply_p50_seconds == 4.2


def test_probe_exception_counts_as_false():
    clock = StepClock()
    state = {"n": 0}

    def probe() -> bool:
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("boom")
        return True

    warm = _warm(probe, clock)
    warm.start()
    warm.join(5)
    assert warm.status().stage is WarmStage.READY


def test_local_cpu_stage_is_model_loading():
    warm = ProbeWarmup(
        lambda: False,
        WarmMode.LOCAL_CPU,
        120,
        lambda: None,
        stage=WarmStage.MODEL_LOADING,
        clock=StepClock(),
        interval_seconds=60,
    )
    assert warm.start().stage is WarmStage.MODEL_LOADING


def test_retry_gets_a_fresh_deadline_window():
    clock = StepClock()
    calls = 0
    third = threading.Event()
    release = threading.Event()

    def probe() -> bool:
        nonlocal calls
        calls += 1
        if calls == 1:
            clock.advance(700)
        elif calls == 2:
            clock.advance(100)
        else:
            third.set()
            release.wait(5)
            return True
        return False

    warm = _warm(probe, clock, deadline_seconds=600)
    first = warm.start().started_at
    warm.join(5)
    assert warm.status().stage is WarmStage.FAILED
    warm.start()
    assert third.wait(5)
    during = warm.status()
    assert (during.stage, during.started_at) == (WarmStage.SERVER_STARTING, first)
    release.set()
    warm.join(5)
    assert warm.status().stage is WarmStage.READY


def test_status_survives_a_failing_reply_p50():
    def broken() -> float | None:
        raise ConnectionError

    warm = ProbeWarmup(lambda: True, WarmMode.MODAL_GPU, 180, broken, clock=StepClock())
    warm.start()
    warm.join(5)
    assert warm.status().reply_p50_seconds is None
    assert ReadyWarmup(WarmMode.PROVIDER_API, broken).start().reply_p50_seconds is None


def test_start_rearms_a_ready_probe_after_the_ready_ttl():
    clock = StepClock()
    up = [True]
    warm = _warm(lambda: up[0], clock)
    warm.start()
    warm.join(5)
    assert warm.status().stage is WarmStage.READY
    clock.advance(301)
    up[0] = False
    assert warm.status().stage is WarmStage.READY  # status() never re-arms
    rearmed = warm.start()
    assert (rearmed.stage, rearmed.started_at) == (WarmStage.SERVER_STARTING, clock.now)
    up[0] = True
    warm.join(5)
    assert warm.status().stage is WarmStage.READY


def test_start_keeps_ready_within_the_ready_ttl():
    clock = StepClock()
    warm = _warm(lambda: True, clock)
    first = warm.start().started_at
    warm.join(5)
    clock.advance(299)
    again = warm.start()
    assert (again.stage, again.started_at) == (WarmStage.READY, first)


def test_ollama_probe_true_only_on_200():
    from emporio.support.infrastructure.warmup import ollama_load_probe

    calls: list[httpx.Request] = []
    outcomes = iter([404, 500, 200])

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(next(outcomes))

    probe = ollama_load_probe(
        "http://localhost:11434/v1", "emporio-gemma", transport=httpx.MockTransport(handler)
    )
    assert [probe(), probe(), probe()] == [False, False, True]
    assert {(r.method, r.url.path) for r in calls} == {("POST", "/api/generate")}
    assert json.loads(calls[0].content) == {
        "model": "emporio-gemma",
        "prompt": "",
        "keep_alive": "30m",
    }
