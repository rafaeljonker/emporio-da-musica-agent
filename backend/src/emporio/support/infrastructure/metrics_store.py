from psycopg_pool import ConnectionPool

from emporio.support.application.ports import TurnMetrics

_INSERT = """
INSERT INTO turn_metrics (
    thread_id, provider, model, scope, input_tokens, output_tokens, cached_tokens, llm_calls,
    tools, ms_total, ms_guard, ms_llm, ms_tools, cost_brl, trace_id
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


class PgMetricsStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def save(self, m: TurnMetrics) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                _INSERT,
                (
                    m.thread_id, m.provider, m.model, m.scope.value, m.input_tokens,
                    m.output_tokens, m.cached_tokens, m.llm_calls, list(m.tools), m.ms_total,
                    m.ms_guard, m.ms_llm, m.ms_tools, m.cost_brl, m.trace_id,
                ),
            )  # fmt: skip

    def reply_p50_seconds(self, provider: str, limit: int = 50) -> float | None:
        """Median turn time over the last `limit` turns of `provider`, None when there are none."""
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY ms_total) FROM"
                " (SELECT ms_total FROM turn_metrics WHERE provider = %s ORDER BY id DESC LIMIT %s)"
                " recent",
                (provider, limit),
            ).fetchone()
        return None if row is None or row[0] is None else float(row[0]) / 1000
