from langchain_core.callbacks import BaseCallbackHandler

from emporio.support.domain.channel_identity import ChannelIdentity


class RecordingTracer:
    """TracerFactory fake: records each turn's identity and returns `trace-<n>`."""

    def __init__(self) -> None:
        self.turns: list[ChannelIdentity] = []

    def for_turn(self, identity: ChannelIdentity) -> tuple[list[BaseCallbackHandler], str]:
        self.turns.append(identity)
        return [], f"trace-{len(self.turns)}"

    def turn_metadata(self, identity: ChannelIdentity) -> dict[str, str]:
        return {}
