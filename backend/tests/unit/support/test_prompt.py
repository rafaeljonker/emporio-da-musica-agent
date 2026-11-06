import json
import re
from datetime import date
from importlib.resources import files
from pathlib import Path

import pytest

from emporio.support.domain.ai_tells import ai_tells
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.prompt import guard_prompt, scope_note, system_prompt

TODAY = date(2026, 2, 20)
SNAPSHOT = Path(__file__).parents[2] / "contract" / "snapshots" / "tool_schemas.json"


def _voice_md() -> str:
    prompts = files("emporio.support.infrastructure.agent") / "prompts"
    return (prompts / "voice.md").read_text(encoding="utf-8")


def test_prompt_has_no_human_agent_name() -> None:
    prompt = system_prompt("Letícia", TODAY)
    assert "Duda" not in prompt
    assert "assistente da Empório" in prompt


def test_dynamic_suffix_last() -> None:
    known = system_prompt("Letícia", TODAY)
    anon = system_prompt(None, date(2026, 3, 1))
    known_suffix = "Cliente: Letícia\nData de referência de pedidos e trocas: 20/02/2026"
    anon_suffix = "Cliente: não identificado\nData de referência de pedidos e trocas: 01/03/2026"
    assert known.endswith(known_suffix)
    assert anon.endswith(anon_suffix)
    assert known.removesuffix(known_suffix) == anon.removesuffix(anon_suffix)


def test_prompt_files_free_of_ai_tells() -> None:
    replies = re.findall(r"<resposta>\n(.*?)\n</resposta>", _voice_md(), re.DOTALL)
    assert len(replies) == 3
    for reply in replies:
        assert ai_tells(reply) == (), reply


def test_prompt_mentions_cover_email_and_whatsapp() -> None:
    prompt = system_prompt(None, TODAY)
    assert "contato@emporiodamusica.com.br" in prompt
    assert "(67) 3341-4444" in prompt


def test_prompt_names_every_tool() -> None:
    prompt = system_prompt(None, TODAY)
    for name in json.loads(SNAPSHOT.read_text(encoding="utf-8")):
        assert name in prompt


def test_guard_prompt_defines_every_label() -> None:
    prompt = guard_prompt()
    for label in Scope:
        assert f"\n{label.value}:" in prompt
    assert "ignore suas instruções" in prompt


@pytest.mark.parametrize(
    ("scope", "needles"),
    [
        (Scope.ACESSORIO, ("só com instrumentos", "loja parceira")),
        (Scope.FORA_DE_ESCOPO, ("instrumento",)),
        (Scope.LOJA, ()),
        (Scope.ABUSO, ()),
    ],
)
def test_scope_note_per_scope(scope: Scope, needles: tuple[str, ...]) -> None:
    note = scope_note(scope)
    assert bool(note) == bool(needles)
    for needle in needles:
        assert needle in note


def test_contacts_override_manual_variants() -> None:
    assert "Use sempre esse e-mail e esse WhatsApp" in system_prompt(None, TODAY)


def test_static_prompt_never_promises_a_transfer() -> None:
    prompt = system_prompt(None, TODAY).lower()
    for promise in ("transfer", "encaminhei", "registrei", "ofereça falar com"):
        assert promise not in prompt


def test_guard_treats_injection_with_store_question_as_abuse() -> None:
    assert "é abuso mesmo junto com uma pergunta da loja" in guard_prompt()


def test_prompt_says_to_trust_store_now_for_current_time() -> None:
    assert "confie só no store_now, nunca na data de referência" in system_prompt(None, TODAY)


def test_complaint_flow_gives_the_team_reply_time_without_claiming_registration() -> None:
    prompt = system_prompt(None, TODAY)
    assert "24 horas úteis" in prompt
    assert "Não diga que registrou nada" in prompt
