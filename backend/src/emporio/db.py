import os

import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from emporio.shared.errors import DomainError


class DatabaseNotConfigured(DomainError):
    """DATABASE_URL is missing from the environment."""

    def __init__(self) -> None:
        super().__init__("DATABASE_URL is not set; run `make db` or see .env.example")


class IndexUnavailable(DomainError):
    """The database behind a search index cannot be reached."""

    def __init__(self) -> None:
        super().__init__("search index unavailable: database unreachable")


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise DatabaseNotConfigured
    return url


def register_vector_if_available(conn: psycopg.Connection) -> None:
    """Register pgvector adapters; a no-op until the extension exists."""
    exists = conn.execute("SELECT 1 FROM pg_type WHERE typname = 'vector'").fetchone()
    conn.commit()
    if exists:
        register_vector(conn)


def connect(url: str | None = None) -> psycopg.Connection:
    conn = psycopg.connect(url or database_url())
    register_vector_if_available(conn)
    return conn


def make_pool(
    url: str | None = None, *, min_size: int = 1, max_size: int = 4, timeout: float = 30.0
) -> ConnectionPool:
    """Shared autocommit pool for read adapters; callers close it."""
    return ConnectionPool(
        url or database_url(),
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        kwargs={"autocommit": True},
        configure=register_vector_if_available,
        check=ConnectionPool.check_connection,
        open=True,
    )
