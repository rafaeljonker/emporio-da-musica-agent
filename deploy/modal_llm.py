"""Gemma 4 31B on vLLM, served from Modal behind an OpenAI-compatible API.

Deploy with `make deploy-llm [LLM_GPU=H100|L40S] [LLM_WEIGHTS=fp8|bf16]`. Image recipe from
https://modal.com/docs/examples/vllm_inference; the CUDA base matches torch 2.14 (CUDA 13.0).
"""

import os
import subprocess
import threading
import time
from typing import IO

import modal

# Taken when this module is imported in the container, a few seconds after the container starts:
# the [boot +Ns] lines count from it.
BOOT_T0 = time.monotonic()

GPUS = ("H100", "L40S")
WEIGHTS = {
    "fp8": ("RedHatAI/gemma-4-31B-it-FP8-dynamic", "d4ab4f579dd3516f97d8a6a4c98d0653480bad15"),
    "bf16": ("google/gemma-4-31B-it", "842da3794eaa0b77d5f08bae87a17459d91ff475"),
}
GPU_SCALEDOWN_SECONDS = 300
SERVED_MODEL_NAME = "google/gemma-4-31B-it"
VLLM_VERSION = "0.33.0"
VLLM_PORT = 8000
MINUTES = 60

GPU = os.environ.get("EMPORIO_GPU", "H100")
WEIGHTS_KEY = os.environ.get("EMPORIO_WEIGHTS", "fp8")
# Both weights repos are public (not gated), so no emporio-hf secret is mounted.
HF_VOLUME = os.environ.get("EMPORIO_HF_VOLUME", "huggingface-cache")
if GPU not in GPUS:
    msg = f"EMPORIO_GPU must be one of {GPUS}, got {GPU!r}"
    raise SystemExit(msg)
if WEIGHTS_KEY not in WEIGHTS:
    msg = f"EMPORIO_WEIGHTS must be one of {tuple(WEIGHTS)}, got {WEIGHTS_KEY!r}"
    raise SystemExit(msg)
REPO, REVISION = WEIGHTS[WEIGHTS_KEY]

image = (
    modal.Image.from_registry("nvidia/cuda:13.0.3-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install(f"vllm=={VLLM_VERSION}")
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",
            "PYTHONUNBUFFERED": "1",
            "VLLM_LOG_STATS_INTERVAL": "10",
            # The container re-imports this file: it must see the deploy-time choices.
            "EMPORIO_GPU": GPU,
            "EMPORIO_WEIGHTS": WEIGHTS_KEY,
            "EMPORIO_HF_VOLUME": HF_VOLUME,
        }
    )
)
hf_cache = modal.Volume.from_name(HF_VOLUME, create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)
volumes = {"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache}

app = modal.App(f"emporio-llm-{GPU.lower()}-{WEIGHTS_KEY}")


@app.function(image=image, volumes=volumes, timeout=60 * MINUTES)
def download() -> str:
    from huggingface_hub import snapshot_download

    path = snapshot_download(REPO, revision=REVISION)
    hf_cache.commit()
    return path


def _stream_with_boot_time(stream: IO[str]) -> None:
    for line in stream:
        print(f"[boot +{time.monotonic() - BOOT_T0:.1f}s] {line}", end="", flush=True)


def _exit_when_done(process: subprocess.Popen[str]) -> None:
    # A failed boot kills the container now, not after the 10-min startup_timeout.
    code = process.wait()
    print(f"[boot +{time.monotonic() - BOOT_T0:.1f}s] vllm exited with code {code}", flush=True)
    os._exit(1)


@app.function(
    image=image,
    gpu=GPU,
    volumes=volumes,
    secrets=[modal.Secret.from_name("emporio-vllm")],
    scaledown_window=GPU_SCALEDOWN_SECONDS,
    max_containers=1,  # cost guard: never more than one GPU
    timeout=60 * MINUTES,
)
@modal.concurrent(max_inputs=32)
@modal.web_server(port=VLLM_PORT, startup_timeout=10 * MINUTES)
def serve() -> None:
    # vLLM reads VLLM_API_KEY (from the emporio-vllm secret) itself; never on argv.
    if not os.environ.get("VLLM_API_KEY"):
        msg = "VLLM_API_KEY is empty: check the emporio-vllm secret"
        raise SystemExit(msg)
    cmd = [
        "vllm",
        "serve",
        REPO,
        "--revision",
        REVISION,
        "--served-model-name",
        SERVED_MODEL_NAME,
        "--max-model-len",
        "16384",
        "--enable-prefix-caching",
        "--kv-cache-dtype",
        "fp8",
        "--gpu-memory-utilization",
        "0.92",
        "--enable-auto-tool-choice",
        "--tool-call-parser",
        "gemma4",
        "--host",
        "0.0.0.0",
        "--port",
        str(VLLM_PORT),
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    threading.Thread(target=_stream_with_boot_time, args=(process.stdout,), daemon=True).start()
    threading.Thread(target=_exit_when_done, args=(process,), daemon=True).start()
