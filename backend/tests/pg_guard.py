from psycopg.conninfo import conninfo_to_dict


def pg_skip_reason(url: str | None) -> str | None:
    """Why postgres tests must not run against `url`, or None when it is safe.

    Decides from the URL alone (no connection): tests truncate and drop tables.
    """
    if not url:
        return "DATABASE_URL not set; run `make test-pg`"
    dbname = conninfo_to_dict(url).get("dbname") or ""
    if not str(dbname).endswith("_test"):
        return f"database {dbname!r} is not a *_test database; run `make test-pg`"
    return None
