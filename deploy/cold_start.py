"""Measure a cold start of a deployed vLLM app: stop its containers, then time /health and one chat.

Usage (from backend/): uv run python ../deploy/cold_start.py --app emporio-llm-h100-fp8
Needs VLLM_API_KEY in the environment. Never prints the key or the URL.
"""

import argparse
import json
import os
import subprocess
import time

import httpx
import modal

POLL_SECONDS = 2
DEADLINE_SECONDS = 900
SERVED_MODEL_NAME = "google/gemma-4-31B-it"


def _container_ids(app: str) -> list[str]:
    out = subprocess.run(
        ["modal", "container", "list", "--json"], check=True, capture_output=True, text=True
    ).stdout
    return [c["container_id"] for c in json.loads(out) if c["app_name"] == app]


def _stop_containers(app: str) -> None:
    for container_id in _container_ids(app):
        subprocess.run(["modal", "container", "stop", container_id], check=True)
    deadline = time.monotonic() + DEADLINE_SECONDS
    while _container_ids(app):
        if time.monotonic() > deadline:
            msg = f"{app}: containers still listed after {DEADLINE_SECONDS}s of stopping"
            raise SystemExit(msg)
        time.sleep(POLL_SECONDS)


def _wait_healthy(client: httpx.Client, url: str) -> None:
    deadline = time.monotonic() + DEADLINE_SECONDS
    while time.monotonic() < deadline:
        try:
            if client.get(f"{url}/health").status_code == httpx.codes.OK:
                return
        except httpx.TransportError:
            pass  # timeout or connection reset while the container boots
        time.sleep(POLL_SECONDS)
    msg = f"/health not OK after {DEADLINE_SECONDS}s; stop the containers and read the app logs"
    raise SystemExit(msg)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True)
    app = parser.parse_args().app
    url = modal.Function.from_name(app, "serve").get_web_url()
    if url is None:
        msg = f"{app}.serve has no web URL; is it deployed?"
        raise SystemExit(msg)
    headers = {"Authorization": f"Bearer {os.environ['VLLM_API_KEY']}"}

    _stop_containers(app)
    with httpx.Client(headers=headers, follow_redirects=False, timeout=10) as client:
        start = time.monotonic()
        _wait_healthy(client, url)
        print(f"cold_start_s={time.monotonic() - start:.1f}")

        start = time.monotonic()
        body = {"model": SERVED_MODEL_NAME, "messages": [{"role": "user", "content": "Oi"}]}
        status = client.post(f"{url}/v1/chat/completions", json=body, timeout=120).status_code
        if status != httpx.codes.OK:
            # Not raise_for_status: its message carries the URL.
            msg = f"chat completion failed with HTTP {status}"
            raise SystemExit(msg)
        print(f"first_reply_s={time.monotonic() - start:.1f}")


if __name__ == "__main__":
    main()
