import pytest

from emporio.db import DatabaseNotConfigured, database_url


def test_database_url_missing_raises_clear_error(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseNotConfigured, match="make db"):
        database_url()
