from contextlib import nullcontext

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class SaverLockMissing(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "PostgresSaver has no `lock` attribute any more: the per-call pooled-connection "
            "override in emporio.support.infrastructure.checkpointer must be re-checked "
            "against the installed langgraph-checkpoint-postgres."
        )


def make_checkpointer(url: str, *, max_size: int = 4) -> PostgresSaver:
    """Saver on its own pool, opened at full size: it needs dict_row, which our positional
    adapters reject. Growing one connection at a time over a high-RTT proxy queues turns.

    Tables come from `emporio.migrate`; close the pool through `saver.conn`.
    """
    pool = ConnectionPool(
        url,
        min_size=max_size,
        max_size=max_size,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        check=ConnectionPool.check_connection,
        open=True,
    )
    saver = PostgresSaver(pool)  # pyright: ignore[reportArgumentType]  # pool is dict_row-typed at runtime
    # The saver-wide lock guards one shared Connection; each call here checks out its own
    # pooled connection, so the lock only queued every thread's checkpoint I/O behind one.
    if not hasattr(saver, "lock"):
        raise SaverLockMissing
    saver.lock = nullcontext()  # pyright: ignore[reportAttributeAccessIssue]  # only used as `with self.lock`
    return saver
