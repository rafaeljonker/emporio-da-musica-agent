from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelIdentity:
    channel: str
    customer_id: int | None
    session: str

    def thread_id(self) -> str:
        if self.customer_id is None:
            return f"{self.channel}:anon:{self.session}"
        return f"{self.channel}:customer:{self.customer_id}"
