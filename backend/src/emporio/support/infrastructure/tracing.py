"""Mandatory Langfuse tracing (research §8). SDK v5: `Langfuse(base_url=, mask_otel_spans=)`.

Session and user ids reach the trace through the CallbackHandler itself: at the root chain it
calls `propagate_attributes` from the run metadata keys `langfuse_session_id` and
`langfuse_user_id`. `propagate_attributes` is a context manager, so `for_turn` cannot return
it; `turn_metadata` supplies those keys and the runner puts them in the graph config.
"""

import hashlib
import hmac
import logging
import re
from typing import Protocol
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langfuse.types import (
    MaskOtelSpansParams,
    MaskOtelSpansResult,
    OtelSpanIdentifier,
    OtelSpanPatch,
)
from pydantic import SecretStr

from emporio.config import LangfuseUnreachable, Settings, require_langfuse_settings
from emporio.support.domain.channel_identity import ChannelIdentity

logger = logging.getLogger("emporio.support.tracing")

REDACTED = "[REDACTED]"
# Order matters: formatted CPF, then bare 11 digits (CPF or mobile), then phones, then e-mail.
# The `(?<![\w-])` and `(?![\w-])` bounds keep ids like `cust-<10 digits>` and hex ids intact.
# ponytail: any bare 10-11 digit number is redacted, so numeric codes (tracking, long order ids)
# are over-redacted on purpose; narrow the digit patterns if traces lose needed identifiers.
_PII = re.compile(
    r"(?<![\w-])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\w-])"
    r"|(?<![\w-])\d{11}(?![\w-])"
    r"|(?<![\w-])(?:\+?55[\s-]?)?(?:\(\d{2}\)|\d{2})[\s-]?9?\d{4}[-\s]?\d{4}(?![\w-])"
    r"|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
)
# Span attributes that carry our pseudonymous ids; never rewritten.
_IDENTIFIER_KEYS = frozenset({"user.id", "session.id", "langfuse.user.id", "langfuse.session.id"})


class TracerFactory(Protocol):
    def for_turn(self, identity: ChannelIdentity) -> tuple[list[BaseCallbackHandler], str]:
        """Fresh callbacks for one turn, and the trace id they report under."""
        ...

    def turn_metadata(self, identity: ChannelIdentity) -> dict[str, str]:
        """Run metadata that sets the trace's session and user (empty for fakes)."""
        ...


def redact(text: str) -> str:
    return _PII.sub(REDACTED, text)


def mask_otel_spans(*, params: MaskOtelSpansParams) -> MaskOtelSpansResult:
    patches: dict[OtelSpanIdentifier, OtelSpanPatch | None] = {}
    for identifier, span in params.spans.items():
        changed = {
            key: redact(value)
            for key, value in span.attributes.items()
            if key not in _IDENTIFIER_KEYS and isinstance(value, str) and redact(value) != value
        }
        if changed:
            patches[identifier] = OtelSpanPatch(set_attributes=changed)
    return MaskOtelSpansResult(span_patches=patches)


def pseudonym(salt: str, customer_id: int | None) -> str:
    if customer_id is None:
        return "anon"
    digest = hmac.new(salt.encode(), str(customer_id).encode(), hashlib.sha256).hexdigest()
    return f"cust-{digest[:10]}"


def _secret(value: SecretStr | None) -> str:
    return value.get_secret_value() if value else ""


class LangfuseTracerFactory:
    def __init__(self, client: Langfuse, salt: str, public_key: str) -> None:
        self._client = client
        self._salt = salt
        self._public_key = public_key

    def for_turn(self, identity: ChannelIdentity) -> tuple[list[BaseCallbackHandler], str]:
        trace_id = Langfuse.create_trace_id(seed=uuid4().hex)
        return [
            CallbackHandler(public_key=self._public_key, trace_context={"trace_id": trace_id})
        ], trace_id

    def turn_metadata(self, identity: ChannelIdentity) -> dict[str, str]:
        return {
            "langfuse_session_id": identity.thread_id(),
            "langfuse_user_id": pseudonym(self._salt, identity.customer_id),
        }


_client: Langfuse | None = None


def make_langfuse(settings: Settings) -> Langfuse:
    """Build the masked client and verify the server and keys now, not silently per turn."""
    global _client
    require_langfuse_settings(settings)
    client = Langfuse(
        public_key=_secret(settings.langfuse_public_key),
        secret_key=_secret(settings.langfuse_secret_key),
        base_url=settings.langfuse_base_url,
        tracing_enabled=True,
        sample_rate=1.0,
        mask_otel_spans=mask_otel_spans,
    )
    try:
        ok = client.auth_check()
    except Exception:
        logger.exception("Langfuse auth_check raised")
        ok = False
    if not ok:
        raise LangfuseUnreachable(settings.langfuse_base_url)
    _client = client
    return client


def shutdown_tracing() -> None:
    """Flush the last batch; call from the API lifespan exit and at the end of CLI/evals."""
    if _client is not None:
        _client.shutdown()
