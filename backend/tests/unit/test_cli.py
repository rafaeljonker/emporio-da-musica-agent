from collections.abc import Callable

import pytest

from emporio import cli
from emporio.bootstrap import Agent
from emporio.config import MissingSetting, Provider
from emporio.support.application.ports import Reply
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope


class FakeHandle:
    def __init__(self) -> None:
        self.calls: list[tuple[ChannelIdentity, str]] = []

    def __call__(self, identity: ChannelIdentity, text: str) -> Reply:
        self.calls.append((identity, text))
        return Reply(("Oi!", "x" * 100), Scope.LOJA, "trace123", ())


class Closed:
    done = False

    def __call__(self) -> None:
        self.done = True


def _wire(monkeypatch: pytest.MonkeyPatch, handle: FakeHandle) -> Closed:
    closed = Closed()
    monkeypatch.setattr(cli, "load_settings", lambda provider=None: provider)
    monkeypatch.setattr(cli, "build_agent", lambda settings: Agent(handle, closed))
    return closed


def _typing(*lines: str) -> Callable[[str], str]:
    it = iter(lines)

    def read(prompt: str) -> str:
        try:
            return next(it)
        except StopIteration:
            raise EOFError from None

    return read


def test_cli_prints_config_error_and_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(provider: Provider | None = None) -> None:
        raise MissingSetting("VLLM_BASE_URL", Provider.GEMMA, "gemini")

    monkeypatch.setattr(cli, "load_settings", fail)
    with pytest.raises(SystemExit) as exc:
        cli.main(["chat"])
    assert exc.value.code == 2
    assert "VLLM_BASE_URL is required" in capsys.readouterr().err


def test_cli_prints_bubbles_in_order(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    handle = FakeHandle()
    closed = _wire(monkeypatch, handle)
    pauses: list[float] = []
    cli.main(
        ["chat", "--as-customer", "14"],
        read=_typing("oi", "   ", "sair", "nunca"),
        sleep=pauses.append,
    )
    out = capsys.readouterr().out.splitlines()
    assert out.index("Oi!") < out.index("x" * 100)
    assert any("loja" in line and "trace123" in line for line in out)
    assert pauses == [0.445, 1.5]
    ((identity, text),) = handle.calls
    assert text == "oi"
    assert (identity.channel, identity.customer_id) == ("cli", 14)
    assert closed.done


def test_cli_exits_on_ctrl_d_and_always_shuts_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed = _wire(monkeypatch, FakeHandle())
    cli.main(["chat"], read=_typing(), sleep=lambda _: None)
    assert closed.done


def test_cli_maps_provider_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Provider | None] = []
    monkeypatch.setattr(cli, "load_settings", lambda provider=None: seen.append(provider))
    monkeypatch.setattr(cli, "build_agent", lambda s: Agent(FakeHandle(), lambda: None))
    cli.main(["chat", "--provider", "gemini"], read=_typing(), sleep=lambda _: None)
    assert seen == [Provider.GEMINI]


def _agent(handle: object, closed: Closed, exists: bool = True) -> Agent:
    return Agent(handle, closed, lambda _id: exists)  # pyright: ignore[reportArgumentType]


class Exploding(FakeHandle):
    def __call__(self, identity: ChannelIdentity, text: str) -> Reply:
        if text == "boom":
            raise RuntimeError
        return super().__call__(identity, text)


def test_cli_turn_exception_keeps_repl_alive(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    handle, closed = Exploding(), Closed()
    monkeypatch.setattr(cli, "load_settings", lambda provider=None: provider)
    monkeypatch.setattr(cli, "build_agent", lambda s: _agent(handle, closed))
    cli.main(["chat"], read=_typing("boom", "oi"), sleep=lambda _: None)
    captured = capsys.readouterr()
    assert "erro nesta mensagem" in captured.err
    assert [text for _, text in handle.calls] == ["oi"]
    assert closed.done


def test_cli_ctrl_c_at_prompt_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    closed = Closed()
    monkeypatch.setattr(cli, "load_settings", lambda provider=None: provider)
    monkeypatch.setattr(cli, "build_agent", lambda s: _agent(FakeHandle(), closed))

    def interrupt(prompt: str) -> str:
        raise KeyboardInterrupt

    cli.main(["chat"], read=interrupt, sleep=lambda _: None)
    assert closed.done


def test_cli_unknown_customer_exits_2(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    closed = Closed()
    monkeypatch.setattr(cli, "load_settings", lambda provider=None: provider)
    monkeypatch.setattr(cli, "build_agent", lambda s: _agent(FakeHandle(), closed, exists=False))
    with pytest.raises(SystemExit) as exc:
        cli.main(["chat", "--as-customer", "999"], read=_typing(), sleep=lambda _: None)
    assert exc.value.code == 2
    assert "cliente 999 não encontrado" in capsys.readouterr().err
    assert closed.done
