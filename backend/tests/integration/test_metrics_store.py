from decimal import Decimal

import pytest
from psycopg_pool import ConnectionPool

from emporio.support.application.ports import TurnMetrics
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.metrics_store import PgMetricsStore

pytestmark = pytest.mark.postgres


def test_metrics_row_roundtrip(pg_pool: ConnectionPool) -> None:
    m = TurnMetrics(
        "web:customer:14", "gemma", "google/gemma-4-31B-it", Scope.LOJA,
        120, 30, 40, 2, ("search_products", "get_order"), 900, 80, 700, 90,
        Decimal("0.012300"), "trace-9",
    )  # fmt: skip
    with pg_pool.connection() as conn:
        conn.execute("TRUNCATE turn_metrics")
    try:
        PgMetricsStore(pg_pool).save(m)
        with pg_pool.connection() as conn:
            row = conn.execute(
                "SELECT thread_id, provider, model, scope, input_tokens, output_tokens,"
                " cached_tokens, llm_calls, tools, ms_total, ms_guard, ms_llm, ms_tools,"
                " cost_brl, trace_id FROM turn_metrics"
            ).fetchone()
        assert row == (
            "web:customer:14", "gemma", "google/gemma-4-31B-it", "loja", 120, 30, 40, 2,
            ["search_products", "get_order"], 900, 80, 700, 90, Decimal("0.012300"), "trace-9",
        )  # fmt: skip
    finally:
        with pg_pool.connection() as conn:
            conn.execute("TRUNCATE turn_metrics")


def test_reply_p50_from_turn_metrics(pg_pool: ConnectionPool) -> None:
    store = PgMetricsStore(pg_pool)
    with pg_pool.connection() as conn:
        conn.execute("TRUNCATE turn_metrics")
    try:
        assert store.reply_p50_seconds("gemma") is None
        for provider, ms in (("gemma", 1000), ("gemma", 3000), ("gemma", 9000), ("fake", 50)):
            store.save(
                TurnMetrics(
                    "web:anon:s", provider, "m", Scope.LOJA, 1, 1, 0, 1, (), ms, 0, 0, 0, None, "t"
                )
            )
        assert store.reply_p50_seconds("gemma") == 3.0
    finally:
        with pg_pool.connection() as conn:
            conn.execute("TRUNCATE turn_metrics")


def test_reply_p50_ignores_failed_turns(pg_pool: ConnectionPool) -> None:
    store = PgMetricsStore(pg_pool)
    with pg_pool.connection() as conn:
        conn.execute("TRUNCATE turn_metrics")
    try:
        for ms, failed in ((1000, False), (2000, False), (60000, True), (90000, True)):
            store.save(
                TurnMetrics(
                    "web:anon:s", "gemma", "m", Scope.LOJA, 1, 1, 0, 1, (), ms, 0, 0, 0, None,
                    "t", failed,
                )
            )  # fmt: skip
        assert store.reply_p50_seconds("gemma") == 1.5
    finally:
        with pg_pool.connection() as conn:
            conn.execute("TRUNCATE turn_metrics")
