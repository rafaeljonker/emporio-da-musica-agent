import pytest

from emporio.entrypoints.ingest import main


def test_ingest_without_database_url_exits_2_with_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert "DATABASE_URL is not set" in capsys.readouterr().err
