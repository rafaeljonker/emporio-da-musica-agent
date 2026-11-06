"""`emporio local-model`: pick, download and create the Gemma 4 model Ollama serves locally.

Apple Silicon runs native Ollama (Docker on macOS has no Metal); otherwise Ollama runs in Docker,
with the GPU when `nvidia-smi` works and Docker lists the `nvidia` runtime.
Times per reply are research estimates (CPU decode is RAM-bandwidth bound), not measurements.
"""

import math
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from emporio.config import ConfigError
from emporio.paths import REPO_ROOT

Route = Literal["native", "docker-nvidia", "docker-cpu"]
NUM_CTX = 16384  # prompt plus tool schemas is about 3k tokens and grows with history
_CONTAINER_MODELFILE = "/root/Modelfile"
_ROUTE_LABEL = {
    "native": "native Ollama (Metal)",
    "docker-nvidia": "Ollama in Docker with the NVIDIA GPU",
    "docker-cpu": "Ollama in Docker on the CPU",
}


class OllamaNotInstalled(ConfigError):
    def __init__(self) -> None:
        super().__init__(
            "PROVIDER=local on this Mac needs the Ollama app: install it from "
            "https://ollama.com/download, open it once, then run this again."
        )


@dataclass(frozen=True)
class LocalPlan:
    route: Route
    tag: str
    download_gb: int
    min_ram_gb: int
    seconds_per_reply: str


def choose_local_model(system: str, machine: str, nvidia: bool, mem_gib: int) -> LocalPlan:
    """31B with an NVIDIA GPU or an Apple Silicon Mac with 32 GiB+; 12B at 16 GiB+; else e4b."""
    route: Route = (
        "native"
        if (system, machine) == ("Darwin", "arm64")
        else "docker-nvidia"
        if nvidia
        else "docker-cpu"
    )
    if route == "docker-nvidia":
        return LocalPlan(
            route, "gemma4:31b", 20, 32, "a few seconds with 24 GB+ of VRAM, minutes if it spills"
        )
    if route == "native" and mem_gib >= 32:
        return LocalPlan(route, "gemma4:31b", 20, 32, "about 10-30 s (8-15 tokens/s)")
    if mem_gib >= 16:
        metal = ", less with Metal" if route == "native" else ""
        seconds = f"about 20-60 s on CPU at 5-10 tokens/s{metal}"
        return LocalPlan(route, "gemma4:12b", 8, 16, seconds)
    return LocalPlan(route, "gemma4:e4b", 10, 8, "about 10-30 s (10-20 tokens/s on CPU)")


def setup_commands(plan: LocalPlan, model: str, modelfile: Path) -> list[list[str]]:
    """Pull the tag and create `model` from the Modelfile, natively or in the compose service."""
    if plan.route == "native":
        return [
            ["ollama", "pull", plan.tag],
            ["ollama", "create", model, "-f", str(modelfile)],
        ]
    service = "ollama-nvidia" if plan.route == "docker-nvidia" else "ollama"
    compose = ["docker", "compose", "--profile", service]
    run = [*compose, "exec", "-T", service, "ollama"]
    return [
        [*compose, "up", "-d", "--wait", service],
        [*run, "pull", plan.tag],
        [*compose, "cp", str(modelfile), f"{service}:{_CONTAINER_MODELFILE}"],
        [*run, "create", model, "-f", _CONTAINER_MODELFILE],
    ]


def warning(plan: LocalPlan) -> str:
    return (
        f"PROVIDER=local: {plan.tag} through {_ROUTE_LABEL[plan.route]}.\n"
        f"  Downloads about {plan.download_gb} GB once and needs about {plan.min_ram_gb} GB "
        "of memory.\n"
        f"  Expected time per reply (estimate): {plan.seconds_per_reply}.\n"
        "  For replies in about 2 s, use the hosted version. Ctrl-C now to stop."
    )


def _output(command: list[str]) -> str | None:
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout if done.returncode == 0 else None


def _memory_gib(system: str) -> int:
    """Nominal RAM: rounded up, since Linux reports a little less than the installed size."""
    if system == "Darwin":
        return math.ceil(int(_output(["sysctl", "-n", "hw.memsize"]) or 0) / 2**30)
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemTotal:"):
            return math.ceil(int(line.split()[1]) / 2**20)
    return 0


def detect_plan() -> LocalPlan:
    system, machine = platform.system(), platform.machine()
    docker = _output(["docker", "info"]) or ""
    nvidia = _output(["nvidia-smi"]) is not None and "nvidia" in docker
    return choose_local_model(system, machine, nvidia, _memory_gib(system))


def prepare_local_model(model: str) -> None:
    """Print the plan and warning, then pull and create `model` (both are idempotent)."""
    plan = detect_plan()
    print(warning(plan), flush=True)
    if plan.route == "native" and shutil.which("ollama") is None:
        raise OllamaNotInstalled
    with tempfile.TemporaryDirectory() as tmp:
        modelfile = Path(tmp) / "Modelfile"
        modelfile.write_text(f"FROM {plan.tag}\nPARAMETER num_ctx {NUM_CTX}\n")
        for command in setup_commands(plan, model, modelfile):
            subprocess.run(command, check=True, cwd=REPO_ROOT)
