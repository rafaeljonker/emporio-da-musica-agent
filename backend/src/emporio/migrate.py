import logging
from pathlib import Path

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import DictRow, dict_row

from emporio.db import connect, database_url, register_vector_if_available
from emporio.paths import MIGRATIONS_DIR

log = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""


def apply_migrations(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending `NNN_*.sql` files in order, one transaction each; return their versions."""
    conn.execute(_CREATE_TABLE)
    conn.commit()
    done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    conn.commit()  # end the read transaction so each migration below is its own transaction
    applied: list[str] = []
    for path in sorted(directory.glob("[0-9][0-9][0-9]_*.sql")):
        version = path.name.split("_", 1)[0]
        if version in done:
            continue
        try:
            # SQL comes from repo-trusted files, not user input, so the non-literal query is safe.
            conn.execute(path.read_text())  # pyright: ignore[reportCallIssue, reportArgumentType]
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
            conn.commit()
        except psycopg.Error:
            conn.rollback()
            raise
        applied.append(version)
        log.info("applied migration %s", path.name)
    if applied:  # the extension may have just been created on this connection
        register_vector_if_available(conn)
    return applied


def setup_checkpointer(url: str | None = None) -> None:
    """Create or upgrade the LangGraph checkpoint tables; idempotent, on its own connection."""
    with psycopg.Connection[DictRow].connect(
        url or database_url(), autocommit=True, prepare_threshold=0, row_factory=dict_row
    ) as conn:
        PostgresSaver(conn).setup()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with connect() as conn:
        applied = apply_migrations(conn)
    setup_checkpointer()
    log.info("applied: %s", applied or "nothing to do")


if __name__ == "__main__":
    main()
