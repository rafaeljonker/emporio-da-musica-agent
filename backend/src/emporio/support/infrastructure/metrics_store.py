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
