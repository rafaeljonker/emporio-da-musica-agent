"""Browser e2e: a real uvicorn server (scripted model unless `make e2e PROVIDER=...`)."""

import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator

import httpx
import pytest
from playwright.sync_api import Browser, Page, StorageState, expect

from emporio.paths import REPO_ROOT

# Test-only credentials, generated per run; never the owner's demo login.
DEMO_EMAIL = "e2e@emporio.test"
DEMO_PASSWORD = secrets.token_urlsafe(16)
BOOT_SECONDS = 180  # first run may download the e5 embedder

type StartServer = Callable[[dict[str, str]], str]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_ready(url: str, process: subprocess.Popen[bytes], log_path: str) -> None:
    deadline = time.monotonic() + BOOT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            with open(log_path) as log:
                pytest.fail(f"server exited with {process.returncode}:\n{log.read()[-4000:]}")
        try:
            if httpx.get(f"{url}/api/auth/me", timeout=2).status_code == 401:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.5)
    pytest.fail(f"server not ready in {BOOT_SECONDS} s")


@pytest.fixture(scope="session")
def start_server() -> Iterator[StartServer]:
    """Factory: start one uvicorn per call with `extra_env` on top; all stop at session end."""
    running: list[subprocess.Popen[bytes]] = []

    def start(extra_env: dict[str, str]) -> str:
        port = _free_port()
        env = {
            **os.environ,
            "DEMO_EMAIL": DEMO_EMAIL,
            "DEMO_PASSWORD": DEMO_PASSWORD,
            "SESSION_SECRET": secrets.token_hex(32),
            "SESSION_HTTPS_ONLY": "false",
            **extra_env,
        }
        log_fd, log_path = tempfile.mkstemp(prefix="emporio-e2e-", suffix=".log")
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "--factory", "emporio.web:create_web_app",
             "--port", str(port)],
            cwd=REPO_ROOT / "backend", env=env, stdout=log_fd, stderr=subprocess.STDOUT,
        )  # fmt: skip
        os.close(log_fd)
        running.append(process)
        url = f"http://127.0.0.1:{port}"
        _wait_ready(url, process, log_path)
        return url

    yield start
    for process in running:
        process.terminate()
    for process in running:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(scope="session")
def server(start_server: StartServer) -> str:
    return start_server({})


@pytest.fixture(scope="session")
def base_url(server: str) -> str:
    """Overrides pytest-base-url so `page.goto("/")` hits the session server."""
    return server


@pytest.fixture(scope="session")
def real_model() -> bool:
    # Derived from EMPORIO_FAKE_MODEL, which `make e2e` sets: run the suite through make.
    return os.environ.get("EMPORIO_FAKE_MODEL") != "1"


def login(page: Page, url: str = "/") -> None:
    page.goto(url)
    page.get_by_label("E-mail").fill(DEMO_EMAIL)
    page.get_by_label("Senha").fill(DEMO_PASSWORD)
    page.get_by_role("button", name="Entrar").click()
    expect(page.get_by_role("heading", name="Assistente da Empório")).to_be_visible()


@pytest.fixture(scope="session")
def signed_in_state(browser: Browser, server: str) -> StorageState:
    """One login through the form for the whole run (the API allows 5 logins/min per IP).

    The tests that start from it share one session id, so one anonymous thread, until a switch.
    """
    context = browser.new_context(base_url=server)
    login(context.new_page())
    state = context.storage_state()
    context.close()
    return state


@pytest.fixture
def signed_in_page(browser: Browser, server: str, signed_in_state: StorageState) -> Iterator[Page]:
    """A fresh context already signed in, for tests that do not exercise the login form."""
    context = browser.new_context(base_url=server, storage_state=signed_in_state)
    page = context.new_page()
    page.goto("/")
    expect(page.get_by_role("heading", name="Assistente da Empório")).to_be_visible()
    yield page
    context.close()
