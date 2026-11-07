from uuid import uuid4

import pytest
from conftest import DEMO_EMAIL, StartServer, login
from playwright.sync_api import Page, expect

AGENT_TIMEOUT_MS = 90_000  # a real model (or a cold GPU) can take a while


def test_login_chat_happy_path(page: Page, real_model: bool) -> None:
    login(page)
    composer = page.get_by_label("Mensagem", exact=True)
    if not real_model:
        # The scripted model is ready at once: the chat opens with focus in the composer.
        expect(composer).to_be_focused()
    composer.fill("Oi")
    composer.press("Enter")

    log = page.get_by_role("log")
    expect(log.locator("p", has_text="Você: Oi")).to_have_count(1)
    agent = log.locator("p", has_text="Assistente: ")
    if real_model:
        expect(agent.first).to_be_visible(timeout=AGENT_TIMEOUT_MS)
    else:
        expect(agent).to_have_text(
            ["Assistente: Oi! Aqui é o modo de teste da Empório", "Assistente: Você escreveu: Oi"],
            timeout=AGENT_TIMEOUT_MS,
        )
    typing = page.get_by_role("status").filter(has_text="O assistente está digitando")
    expect(typing).to_have_count(0, timeout=AGENT_TIMEOUT_MS)
    expect(log.get_by_text("Perdi o fio")).to_have_count(0)


def test_queued_message_sent_once_when_ready(page: Page, start_server: StartServer) -> None:
    # Its own server: scripted model that warms for ~10 s from the login (room to type), GPU copy.
    url = start_server({"EMPORIO_FAKE_MODEL": "1", "EMPORIO_FAKE_WARM_SECONDS": "10"})
    login(page, url)
    expect(page.get_by_role("heading", name="Afinando o atendimento")).to_be_visible()
    composer = page.get_by_label("Mensagem", exact=True)
    composer.fill("Oi")
    composer.press("Enter")

    log = page.get_by_role("log")
    expect(log.get_by_text("Vai assim que o assistente ficar pronto")).to_be_visible()
    expect(log.locator("p", has_text="Você: Oi")).to_have_count(1)

    agent = log.locator("p", has_text="Assistente: ")
    expect(agent).to_have_text(
        ["Assistente: Oi! Aqui é o modo de teste da Empório", "Assistente: Você escreveu: Oi"],
        timeout=AGENT_TIMEOUT_MS,
    )
    expect(log.locator("p", has_text="Você: ")).to_have_count(1)
    expect(log.get_by_text("Vai assim que o assistente ficar pronto")).to_have_count(0)
    expect(page.get_by_role("heading", name="Afinando o atendimento")).to_have_count(0)


# The API allows 5 logins per minute per IP (auth.py). Only the tests about the login form
# log in through it; the rest start from `signed_in_page` (one login for the whole run).
def test_wrong_password_shows_error(page: Page) -> None:
    page.goto("/")
    email = page.get_by_label("E-mail")
    email.fill(DEMO_EMAIL)
    page.get_by_label("Senha").fill("not-the-password")
    page.get_by_role("button", name="Entrar").click()

    expect(page.get_by_role("alert")).to_have_text(
        "E-mail ou senha não bateram. Confere e tenta de novo."
    )
    expect(email).to_be_focused()
    expect(email).to_have_attribute("aria-invalid", "true")
    expect(page.get_by_role("heading", name="Assistente da Empório")).to_have_count(0)


def test_switch_customer_appends_divider(signed_in_page: Page, real_model: bool) -> None:
    page = signed_in_page
    composer = page.get_by_label("Mensagem", exact=True)
    log = page.get_by_role("log")
    agent = log.locator("p", has_text="Assistente: ")
    typing = page.get_by_role("status").filter(has_text="O assistente está digitando")

    composer.fill("Oi")
    composer.press("Enter")
    expect(agent.first).to_be_visible(timeout=AGENT_TIMEOUT_MS)
    expect(typing).to_have_count(0, timeout=AGENT_TIMEOUT_MS)
    first_reply = agent.count()

    customer = page.request.get("/api/customers").json()[0]
    first_name = customer["name"].split(" ")[0]
    selector = page.get_by_role("combobox", name="Conversar como…")
    selector.click()
    page.get_by_role("option", name=customer["name"]).click()

    divider = log.get_by_text(f"Agora conversando como {first_name}")
    expect(divider).to_be_visible()
    expect(selector).to_contain_text(customer["name"])
    expect(selector).to_be_focused()  # SC 3.2.2: the switch never moves focus
    # The thread above the divider stays.
    expect(log.locator("p", has_text="Você: Oi")).to_have_count(1)
    expect(agent).to_have_count(first_reply)

    # The server rotated the session; what the browser can see is a fresh turn answering below
    # the divider (the scripted model echoes only the new message, in two bubbles).
    composer.fill("Tudo bem?")
    composer.press("Enter")
    expect(agent.nth(first_reply)).to_be_visible(timeout=AGENT_TIMEOUT_MS)
    expect(typing).to_have_count(0, timeout=AGENT_TIMEOUT_MS)
    if not real_model:
        expect(agent).to_have_count(first_reply + 2)
        expect(agent.last).to_have_text("Assistente: Você escreveu: Tudo bem?")
    after_divider = divider.locator("xpath=following::p[contains(., 'Você: Tudo bem?')]")
    expect(after_divider).to_have_count(1)


def test_sending_follows_to_the_bottom_when_scrolled_up(signed_in_page: Page) -> None:
    page = signed_in_page
    page.set_viewport_size({"width": 1024, "height": 500})
    composer = page.get_by_label("Mensagem", exact=True)
    log = page.get_by_role("log")
    typing = page.get_by_role("status").filter(has_text="O assistente está digitando")
    for n in range(4):
        composer.fill(f"Mensagem {n}")
        composer.press("Enter")
        expect(log.locator("p", has_text=f"Você: Mensagem {n}")).to_have_count(1)
        reply = log.get_by_text(f"Assistente: Você escreveu: Mensagem {n}")
        expect(reply).to_have_count(1, timeout=AGENT_TIMEOUT_MS)
        expect(typing).to_have_count(0, timeout=AGENT_TIMEOUT_MS)

    log.evaluate("el => { el.scrollTop = 0 }")
    expect(log.locator("p", has_text="Você: Mensagem 3")).not_to_be_in_viewport()
    composer.fill("Mensagem final")
    composer.press("Enter")
    expect(log.locator("p", has_text="Você: Mensagem final")).to_be_in_viewport()


def test_failed_turn_offers_resend(signed_in_page: Page, real_model: bool) -> None:
    if real_model:
        pytest.skip("[falha] is a scripted-model marker")
    page = signed_in_page
    composer = page.get_by_label("Mensagem", exact=True)
    log = page.get_by_role("log")
    error_line = log.get_by_text("Perdi o fio da conversa aqui.")
    resend = log.get_by_role("button", name="Manda de novo?")

    # The scripted model fails every turn with the marker, so its resend fails the same way:
    # one more request with the same text, the old error line replaced, no second user bubble.
    composer.fill("isso vai dar [falha]")
    composer.press("Enter")
    expect(resend).to_have_count(1, timeout=AGENT_TIMEOUT_MS)
    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/api/chat")) as sent:
        resend.click()
    if sent.value.post_data_json != {"text": "isso vai dar [falha]"}:
        pytest.fail(f"resend sent {sent.value.post_data_json!r}")
    expect(composer).to_be_focused()
    expect(resend).to_have_count(1, timeout=AGENT_TIMEOUT_MS)
    expect(error_line).to_have_count(1)
    expect(log.locator("p", has_text="Você: ")).to_have_count(1)

    # A dropped request fails once; its resend reaches the real server and the bubbles arrive.
    page.route("**/api/chat", lambda route: route.abort(), times=1)
    composer.fill("Oi")
    composer.press("Enter")
    expect(error_line).to_have_count(2, timeout=AGENT_TIMEOUT_MS)
    resend.last.click()
    expect(log.locator("p", has_text="Assistente: ")).to_have_text(
        ["Assistente: Oi! Aqui é o modo de teste da Empório", "Assistente: Você escreveu: Oi"],
        timeout=AGENT_TIMEOUT_MS,
    )
    expect(error_line).to_have_count(1)
    expect(log.locator("p", has_text="Você: Oi")).to_have_count(1)


def test_logout_returns_to_login(signed_in_page: Page) -> None:
    page = signed_in_page
    page.get_by_role("button", name="Sair").click()
    login_title = page.get_by_role("heading", name="Entra aí pra conversar com a Empório")
    expect(login_title).to_be_visible()
    expect(page.request.get("/api/auth/me")).not_to_be_ok()
    page.reload()
    expect(login_title).to_be_visible()


# One unbroken token in a value (a long cost basis) must wrap inside the panel, not widen it.
LONG_VALUE = "PrecoPorTokenAindaNaoConfirmadoPeloProvedor" * 3
SSE_TURN = "".join(
    f"event: {name}\ndata: {data}\n\n"
    for name, data in [
        ("typing", "{}"),
        ("bubble", '{"kind": "text", "text": "Oi", "delay_ms": 0}'),
        (
            "metrics",
            '{"input_tokens": 1200, "output_tokens": 80, "ms_model": 900, "ms_guard": 10,'
            ' "ms_llm": 800, "ms_tools": 20, "cost_brl": "0.0123",'
            f' "cost_basis": "{LONG_VALUE}", "action": "sem ferramenta"}}',
        ),
        ("done", '{"trace_id": null}'),
    ]
)


def test_metrics_panel_fits_320px(signed_in_page: Page) -> None:
    page = signed_in_page
    page.set_viewport_size({"width": 320, "height": 640})
    page.route(
        "**/api/chat",
        lambda route: route.fulfill(status=200, content_type="text/event-stream", body=SSE_TURN),
    )
    composer = page.get_by_label("Mensagem", exact=True)
    composer.fill("Oi")
    composer.press("Enter")
    typing = page.get_by_role("status").filter(has_text="O assistente está digitando")
    expect(typing).to_have_count(0, timeout=AGENT_TIMEOUT_MS)

    log = page.get_by_role("log")
    toggle = page.get_by_role("button", name="Métricas ·")
    expect(toggle).to_have_attribute("aria-expanded", "false")  # the turn's totals are in
    before = log.bounding_box()
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    panel = page.get_by_role("region", name="Métricas")
    expect(panel).to_contain_text(LONG_VALUE[:20])
    # A floating panel: opening it never moves the transcript.
    if log.bounding_box() != before:
        pytest.fail("opening the metrics panel moved the transcript")
    panel.evaluate("el => Promise.all(el.getAnimations().map(a => a.finished))")
    fits = panel.evaluate(
        "el => { const r = el.getBoundingClientRect();"
        " return el.scrollWidth <= el.clientWidth && r.left >= 0 && r.right <= innerWidth"
        " && r.top >= 0 && r.bottom <= innerHeight }"
    )
    if not fits:
        pytest.fail("the metrics panel does not fit the 320 px viewport")

    # Escape closes it and returns focus to the toggle; so does the toggle; outside click closes.
    panel.focus()
    page.keyboard.press("Escape")
    expect(panel).to_be_hidden()
    expect(toggle).to_be_focused()
    toggle.click()
    expect(panel).to_be_visible()
    toggle.click()
    expect(panel).to_be_hidden()
    toggle.click()
    page.get_by_role("heading", level=1).click()
    expect(panel).to_be_hidden()


PACED_TURN = "".join(
    f"event: {name}\ndata: {data}\n\n"
    for name, data in [
        ("typing", "{}"),
        ("bubble", '{"kind": "text", "text": "Primeira", "delay_ms": 0}'),
        ("bubble", '{"kind": "text", "text": "Segunda", "delay_ms": 3000}'),
        ("done", '{"trace_id": null}'),
    ]
)


def test_typing_dots_sit_under_the_last_bubble(signed_in_page: Page) -> None:
    page = signed_in_page
    page.route(
        "**/api/chat",
        lambda route: route.fulfill(status=200, content_type="text/event-stream", body=PACED_TURN),
    )
    composer = page.get_by_label("Mensagem", exact=True)
    composer.fill("Oi")
    composer.press("Enter")
    log = page.get_by_role("log")
    first = log.locator("p", has_text="Assistente: Primeira")
    dots = log.locator(".typing-dot").first
    expect(first).to_be_visible(timeout=AGENT_TIMEOUT_MS)
    # Visible in the conversation, hidden from the log; the status region speaks it instead.
    expect(dots).to_be_visible()
    typing = page.get_by_role("status").filter(has_text="O assistente está digitando")
    expect(typing).to_have_count(1)
    if not log.locator("[aria-hidden=true]:has(.typing-dot)").count():
        pytest.fail("the typing dots are not aria-hidden inside the log")
    if dots.bounding_box()["y"] <= first.bounding_box()["y"]:
        pytest.fail("the typing dots are not under the last bubble")
    expect(log.locator("p", has_text="Assistente: Segunda")).to_be_visible(timeout=AGENT_TIMEOUT_MS)
    expect(dots).to_have_count(0)


def test_catalog_create_then_ask(signed_in_page: Page, real_model: bool) -> None:
    page = signed_in_page
    name = f"Cavaquinho Teste {uuid4().hex[:6]}"
    trigger = page.get_by_role("button", name="Catálogo")
    trigger.click()
    dialog = page.get_by_role("dialog", name="Cadastrar produto")
    expect(dialog).to_be_visible()
    dialog.get_by_label("Nome").fill(name)
    dialog.get_by_role("combobox", name="Categoria").click()
    page.get_by_role("option", name="Violões", exact=True).click()
    dialog.get_by_label("Preço (R$)").fill("899,90")
    dialog.get_by_label("Estoque").fill("3")
    dialog.get_by_label("Especificações").fill("Cordas: aço\nTampo: abeto")
    dialog.get_by_role("button", name="Cadastrar", exact=True).click()

    saved = dialog.get_by_role("heading", name="Produto cadastrado.")
    expect(saved).to_be_focused()
    expect(dialog.get_by_role("button", name=f"Editar {name}")).to_be_visible()
    mine = [p for p in page.request.get("/api/catalog/products/mine").json() if p["name"] == name]
    if [(p["price"], p["stock"], p["category"]) for p in mine] != [("899.90", 3, "Violões")]:
        pytest.fail(f"GET mine has {mine!r}")

    dialog.get_by_role("button", name="Perguntar ao assistente").click()
    expect(dialog).to_have_count(0)
    composer = page.get_by_label("Mensagem", exact=True)
    expect(composer).to_have_value(f"Vocês têm o {name}?")
    expect(composer).to_be_focused()
    log = page.get_by_role("log")
    expect(log.locator("p", has_text="Você: ")).to_have_count(0)  # filled, never sent

    composer.press("Enter")
    agent = log.locator("p", has_text="Assistente: ")
    expect(agent.first).to_be_visible(timeout=AGENT_TIMEOUT_MS)
    if not real_model:
        expect(agent.last).to_have_text(
            f"Assistente: Você escreveu: Vocês têm o {name}?", timeout=AGENT_TIMEOUT_MS
        )


def test_catalog_dialog_shows_field_errors(signed_in_page: Page) -> None:
    page = signed_in_page
    trigger = page.get_by_role("button", name="Catálogo")
    trigger.click()
    dialog = page.get_by_role("dialog", name="Cadastrar produto")
    dialog.get_by_role("button", name="Cadastrar", exact=True).click()

    name = dialog.get_by_label("Nome")
    expect(name).to_have_attribute("aria-invalid", "true")
    expect(name).to_be_focused()
    expect(name).to_have_accessible_description("Escreve o nome do produto, de 2 a 120 caracteres.")
    expect(dialog.get_by_label("Preço (R$)")).to_have_attribute("aria-invalid", "true")

    # Escape closes it and focus returns to the trigger.
    page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)
    expect(trigger).to_be_focused()
