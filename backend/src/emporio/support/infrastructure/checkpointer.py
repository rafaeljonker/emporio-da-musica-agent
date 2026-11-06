from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def make_checkpointer(url: str) -> PostgresSaver:
    """Saver on its own small pool: it needs dict_row, which our positional adapters reject.

    Tables come from `emporio.migrate`; close the pool through `saver.conn`.
    """
    pool = ConnectionPool(
        url,
        min_size=1,
        max_size=4,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    return PostgresSaver(pool)  # pyright: ignore[reportArgumentType]  # pool is dict_row-typed at runtime
