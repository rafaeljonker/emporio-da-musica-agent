"""The web API (FastAPI + the built frontend) on Modal, with Railway Postgres and Langfuse Cloud.

Deploy with `make deploy-api [LLM_APP=emporio-llm-<gpu>-<weights>] [LOADTEST=1]`. LOADTEST=1
deploys `emporio-api-loadtest`: scripted model, raised rate limits, no GPU. From backend/,
`uv run modal run ../deploy/modal_api.py::ingest` migrates and indexes the data into the
`emporio-db` database (frontend/dist must exist: `make web-build`).
"""

import os
import subprocess
import sys
from pathlib import Path

import modal

# Under the GPU scaledown (deploy/modal_llm.py GPU_SCALEDOWN_SECONDS = 600): a READY older than this
# is probed again, so the API never reports a GPU that has already scaled down.
WARM_READY_TTL_SECONDS = 540
# USD per hour, modal.com/pricing on 2026-11-06. Keys must match deploy/modal_llm.py GPUS.
GPU_PRICES = {"H100": "3.95", "L40S": "1.95"}
FASTEMBED_CACHE = "/models/fastembed"
MINUTES = 60

LLM_APP = os.environ.get("EMPORIO_LLM_APP", "emporio-llm-h100-fp8")
LOADTEST = os.environ.get("EMPORIO_LOADTEST", "")
if LOADTEST not in ("", "1"):
    msg = f"EMPORIO_LOADTEST must be unset or 1, got {LOADTEST!r}"
    raise SystemExit(msg)
LLM_GPU = LLM_APP.removeprefix("emporio-llm-").split("-")[0].upper()
if not LLM_APP.startswith("emporio-llm-") or LLM_GPU not in GPU_PRICES:
    gpus = "|".join(GPU_PRICES).lower()
    msg = f"EMPORIO_LLM_APP must be emporio-llm-<{gpus}>-<weights>, got {LLM_APP!r}"
    raise SystemExit(msg)

# Local repo root. In the container this file sits in /root, so these paths only matter at deploy.
ROOT = Path(__file__).resolve().parents[1]
NO_CACHE = ["**/__pycache__", "**/__pycache__/**"]

runtime_env = {
    "PYTHONPATH": "/app/backend/src",
    "HF_HUB_OFFLINE": "1",  # e5 is baked below: a runtime download fails loudly instead
    "LLM_PROVIDER": "gemma",
    "WARM_READY_TTL_SECONDS": str(WARM_READY_TTL_SECONDS),
    "GPU_USD_PER_HOUR": GPU_PRICES[LLM_GPU],
}
if LOADTEST:
    # RATE_LIMIT_MULTIPLIER boots only together with EMPORIO_FAKE_MODEL=1 (cost guard).
    runtime_env |= {"EMPORIO_FAKE_MODEL": "1", "RATE_LIMIT_MULTIPLIER": "100"}


def bake_e5() -> None:
    """Build step: download e5 into FASTEMBED_CACHE with the same registration the app uses."""
    from emporio.embeddings import E5Embedder

    E5Embedder().embed_query("violão")


image = (
    modal.Image.debian_slim(python_version="3.12")
    # Runtime deps from uv.lock: no dev group, the project itself comes from the source mount.
    .uv_sync(uv_project_dir=str(ROOT / "backend"), frozen=True, extra_options="--no-dev")
    .env(
        {
            "PYTHONUNBUFFERED": "1",
            "FASTEMBED_CACHE_PATH": FASTEMBED_CACHE,
            # The container re-imports this file: it must see the deploy-time choices.
            "EMPORIO_LLM_APP": LLM_APP,
            "EMPORIO_LOADTEST": LOADTEST,
        }
    )
    # Only the embedder module, so the e5 layer is rebuilt when it changes and not on every edit.
    .add_local_file(
        ROOT / "backend/src/emporio/__init__.py", "/bake/emporio/__init__.py", copy=True
    )
    .add_local_file(
        ROOT / "backend/src/emporio/embeddings.py", "/bake/emporio/embeddings.py", copy=True
    )
    .run_function(bake_e5, env={"PYTHONPATH": "/bake"})
    .env(runtime_env)
    # Under /app so emporio.paths.REPO_ROOT resolves to /app.
    .add_local_dir(ROOT / "backend/src", "/app/backend/src", ignore=NO_CACHE)
    .add_local_dir(ROOT / "backend/migrations", "/app/backend/migrations")
    .add_local_dir(ROOT / "data", "/app/data")
    .add_local_dir(ROOT / "frontend/dist", "/app/frontend/dist")
)

app = modal.App("emporio-api-loadtest" if LOADTEST else "emporio-api")

db_secret = modal.Secret.from_name("emporio-db")
web_secrets = [
    db_secret,
    modal.Secret.from_name("emporio-langfuse"),
    modal.Secret.from_name("emporio-web"),
]
if not LOADTEST:
    web_secrets.append(modal.Secret.from_name("emporio-vllm"))


@app.function(
    image=image,
    secrets=web_secrets,
    max_containers=1,  # rate limits, locks and the warm-up status live in this one process
    scaledown_window=300,
)
@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web() -> object:  # the FastAPI app
    if not LOADTEST:
        url = modal.Function.from_name(LLM_APP, "serve").get_web_url()
        if not url:
            msg = f"{LLM_APP} has no web URL: run make deploy-llm first"
            raise SystemExit(msg)
        os.environ["VLLM_BASE_URL"] = f"{url}/v1"
    from emporio.web import create_web_app

    return create_web_app()


@app.function(image=image, secrets=[db_secret], timeout=30 * MINUTES)
def ingest() -> None:
    for module in ("emporio.migrate", "emporio.ingest"):
        subprocess.run([sys.executable, "-m", module], check=True)
