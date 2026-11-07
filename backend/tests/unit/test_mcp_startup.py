from types import SimpleNamespace

import pytest

from emporio import bootstrap, cli
from emporio.config import ConfigError, Settings


def _wire(monkeypatch: pytest.MonkeyPatch, known: set[int]) -> list[int | None]:
    served: list[int | None] = []
    customers = SimpleNamespace(by_id=lambda cid: object() if cid in known else None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")
    toolbox = (object(), customers, object(), object())
    monkeypatch.setattr(bootstrap, "build_toolbox", lambda stack, url, settings: toolbox)
    monkeypatch.setattr(
        bootstrap,
        "build_mcp",
        lambda box, context: SimpleNamespace(run=lambda: served.append(context().customer_id)),
    )
    return served


def test_run_mcp_rejects_unknown_customer(monkeypatch: pytest.MonkeyPatch) -> None:
    served = _wire(monkeypatch, {3})

    with pytest.raises(ConfigError, match="cliente 99 não encontrado"):
        bootstrap.run_mcp(Settings(), 99)
    assert served == []


def test_run_mcp_serves_known_customer(monkeypatch: pytest.MonkeyPatch) -> None:
    served = _wire(monkeypatch, {3})

    bootstrap.run_mcp(Settings(), 3)
    assert served == [3]


def test_cli_mcp_reports_unknown_customer_and_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _wire(monkeypatch, set())
    monkeypatch.setenv("EMPORIO_MCP_CUSTOMER_ID", "99")
    monkeypatch.setattr(cli, "load_mcp_settings", Settings)

    with pytest.raises(SystemExit) as exc:
        cli.main(["mcp"])
    assert exc.value.code == 2
    assert "cliente 99 não encontrado" in capsys.readouterr().err


def test_cli_mcp_rejects_non_integer_customer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EMPORIO_MCP_CUSTOMER_ID", "abc")

    with pytest.raises(SystemExit) as exc:
        cli.main(["mcp"])
    assert exc.value.code == 2
    assert "EMPORIO_MCP_CUSTOMER_ID precisa ser um número inteiro" in capsys.readouterr().err
