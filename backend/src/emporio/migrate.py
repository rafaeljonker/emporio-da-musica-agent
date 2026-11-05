import logging
from pathlib import Path

import psycopg

from emporio.db import connect
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
    applied: list[str] = []
    for path in sorted(directory.glob("[0-9][0-9][0-9]_*.sql")):
        version = path.name.split("_", 1)[0]
        if version in done:
            continue
        with conn.transaction():
            conn.execute(path.read_text())  # pyright: ignore[reportCallIssue, reportArgumentType]
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        applied.append(version)
        log.info("applied migration %s", path.name)
    return applied


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with connect() as conn:
        applied = apply_migrations(conn)
    log.info("applied: %s", applied or "nothing to do")


if __name__ == "__main__":
    main()
