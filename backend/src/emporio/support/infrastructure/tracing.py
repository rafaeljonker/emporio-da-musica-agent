from typing import Protocol

from langchain_core.callbacks import BaseCallbackHandler

from emporio.support.domain.channel_identity import ChannelIdentity


class TracerFactory(Protocol):
    def for_turn(self, identity: ChannelIdentity) -> tuple[list[BaseCallbackHandler], str]:
        """Fresh callbacks for one turn, and the trace id they report under."""
        ...
