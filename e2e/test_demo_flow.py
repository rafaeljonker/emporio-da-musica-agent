from conftest import login
from playwright.sync_api import Page, expect

AGENT_TIMEOUT_MS = 90_000  # a real model (or a cold GPU) can take a while


def test_login_chat_happy_path(page: Page, real_model: bool) -> None:
    login(page)
    composer = page.get_by_label("Mensagem", exact=True)
    composer.fill("Oi")
    composer.press("Enter")

    log = page.get_by_role("log")
    expect(log.locator("p", has_text="Você: Oi")).to_have_count(1)
    agent = log.locator("p", has_text="Assistente: ")
    if real_model:
        expect(agent.first).to_be_visible(timeout=AGENT_TIMEOUT_MS)
    else:
        expect(agent).to_have_text(
            ["Assistente: Oi! Aqui é o modo de teste da Empório.", "Assistente: Você escreveu: Oi"],
            timeout=AGENT_TIMEOUT_MS,
        )
    typing = page.get_by_role("status").filter(has_text="O assistente está digitando")
    expect(typing).to_have_count(0, timeout=AGENT_TIMEOUT_MS)
    expect(log.get_by_text("Perdi o fio")).to_have_count(0)
