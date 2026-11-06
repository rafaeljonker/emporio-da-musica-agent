from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class WarmMode(StrEnum):
    MODAL_GPU = "modal_gpu"
    LOCAL_CPU = "local_cpu"
    PROVIDER_API = "provider_api"


class WarmStage(StrEnum):
    SERVER_STARTING = "server_starting"
    MODEL_LOADING = "model_loading"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True)
class WarmStatus:
    mode: WarmMode
    stage: WarmStage
    started_at: datetime
    elapsed_seconds: int
    expected_seconds: int
    reply_p50_seconds: float | None

    def to_json(self) -> dict[str, object]:
        return {
            "mode": self.mode.value,
            "stage": self.stage.value,
            "started_at": self.started_at.isoformat(),
            "elapsed_seconds": self.elapsed_seconds,
            "expected_seconds": self.expected_seconds,
            "reply_p50_seconds": self.reply_p50_seconds,
        }


class Warmup(Protocol):
    def start(self) -> WarmStatus: ...

    def status(self) -> WarmStatus: ...
