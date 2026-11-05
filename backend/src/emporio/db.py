import os

import psycopg
from pgvector.psycopg import register_vector

from emporio.shared.errors import DomainError


class DatabaseNotConfigured(DomainError):
    """DATABASE_URL is missing from the environment."""

    def __init__(self) -> None:
        super().__init__("DATABASE_URL is not set; run `make db` or see .env.example")


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise DatabaseNotConfigured
    return url


def connect(url: str | None = None) -> psycopg.Connection:
    conn = psycopg.connect(url or database_url())
    exists = conn.execute("SELECT 1 FROM pg_type WHERE typname = 'vector'").fetchone()
    conn.commit()
    if exists:
        register_vector(conn)
    return conn
