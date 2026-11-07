"""Mandatory Langfuse tracing (research §8). SDK v5: `Langfuse(base_url=, mask_otel_spans=)`.

Session and user ids reach the trace through the CallbackHandler itself: at the root chain it
calls `propagate_attributes` from the run metadata keys `langfuse_session_id` and
`langfuse_user_id`. `propagate_attributes` is a context manager, so `for_turn` cannot return
it; `turn_metadata` supplies those keys and the runner puts them in the graph config.
"""

import hashlib
import hmac
import json
import logging
import re
import unicodedata
from collections.abc import Callable, Iterable, Sequence
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

from emporio.platform.config import LangfuseUnreachable, Settings, require_langfuse_settings
from emporio.support.domain.channel_identity import ChannelIdentity

logger = logging.getLogger("emporio.support.tracing")

REDACTED = "[REDACTED]"
# Formatted CPF, bare 11 digits (CPF or mobile) and e-mail. The `(?<![\w-])` and `(?![\w-])`
# bounds keep ids like `cust-<10 digits>` and hex ids intact.
# ponytail: any bare 11 digit number is redacted, so numeric codes (tracking, long order ids)
# are over-redacted on purpose; narrow the digit patterns if traces lose needed identifiers.
_PII = re.compile(
    r"(?<![\w-])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\w-])"
    r"|(?<![\w-])\d{11}(?![\w-])"
    r"|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
)
# A run of 10-13 digits with spaces, dots, dashes or parentheses between them (and an optional
# +). Whether it is a phone is decided on the digits alone, so "67 9 8432 1098" and
# "55 (67) 98432-1098" are masked like the number they authenticate as.
_PHONE_RUN = re.compile(r"(?<![\w-])\+?\(?\d(?:[\s.()-]*\d){9,12}\)?(?![\w-])")
_BR_PHONE = re.compile(r"(?:55)?[1-9][1-9](?:9\d{8}|[2-9]\d{7})")
# Span attributes that carry our pseudonymous ids; never rewritten.
_IDENTIFIER_KEYS = frozenset({"user.id", "session.id", "langfuse.user.id", "langfuse.session.id"})


class TracerFactory(Protocol):
    def for_turn(self, identity: ChannelIdentity) -> tuple[list[BaseCallbackHandler], str]:
        """Fresh callbacks for one turn, and the trace id they report under."""
        ...

    def turn_metadata(self, identity: ChannelIdentity) -> dict[str, str]:
        """Run metadata that sets the trace's session and user (empty for fakes)."""
        ...


def _phone_or_same(run: re.Match[str]) -> str:
    digits = "".join(c for c in run.group() if c.isdigit())
    return REDACTED if _BR_PHONE.fullmatch(digits) else run.group()


_PARTICLES = frozenset({"da", "de", "do", "das", "dos", "e"})


def _forms(token: str) -> list[str]:
    """The token as written, accent-stripped, and as json.dumps escapes it (`\\u00ed`)."""
    plain = "".join(c for c in unicodedata.normalize("NFKD", token) if not unicodedata.combining(c))
    return [token, plain, json.dumps(token)[1:-1]]


def name_pattern(names: Iterable[str]) -> re.Pattern[str] | None:
    """Full names (any whitespace between tokens), the first token (3+ chars) and every other
    token of 4+ chars that is not a particle, each also accent-stripped and JSON-escaped.
    Langfuse serialises with ensure_ascii, so "Letícia" can arrive as `Let\\u00edcia`.
    """
    # ponytail: masks every CSV name token, so a name or surname that is also a common word is
    # over-redacted; switch to per-turn names if traces lose meaning.
    found: set[str] = set()
    for name in names:
        tokens = name.split()
        if len(tokens) > 1:
            for variant in range(3):
                found.add(r"\s+".join(re.escape(_forms(t)[variant]) for t in tokens))
        keep = [t for i, t in enumerate(tokens) if len(t) >= (3 if i == 0 else 4)]
        for token in keep:
            if token.casefold() not in _PARTICLES:
                found.update(re.escape(f) for f in _forms(token))
    if not found:
        return None
    alternatives = "|".join(sorted(found, key=len, reverse=True))
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE)


def redact(text: str, names: re.Pattern[str] | None = None) -> str:
    text = _PHONE_RUN.sub(_phone_or_same, _PII.sub(REDACTED, text))
    return names.sub(REDACTED, text) if names else text


def make_mask(names: re.Pattern[str] | None) -> Callable[..., MaskOtelSpansResult]:
    def mask_otel_spans(*, params: MaskOtelSpansParams) -> MaskOtelSpansResult:
        patches: dict[OtelSpanIdentifier, OtelSpanPatch | None] = {}
        for identifier, span in params.spans.items():
            changed = {
                key: masked
                for key, value in span.attributes.items()
                if key not in _IDENTIFIER_KEYS
                and isinstance(value, str)
                and (masked := redact(value, names)) != value
            }
            if changed:
                patches[identifier] = OtelSpanPatch(set_attributes=changed)
        return MaskOtelSpansResult(span_patches=patches)

    return mask_otel_spans


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
        who = pseudonym(self._salt, identity.customer_id)
        # The raw customer id must not reach Langfuse; anonymous thread ids carry none.
        session = (
            identity.thread_id()
            if identity.customer_id is None
            else f"{identity.channel}:{who}:{identity.session}"
        )
        # LangGraph copies configurable.thread_id into the run metadata unless the caller sets
        # `thread_id` there itself; set it to the safe session so the raw id never exports.
        return {"langfuse_session_id": session, "langfuse_user_id": who, "thread_id": session}


_client: Langfuse | None = None


def make_langfuse(settings: Settings, customer_names: Sequence[str] = ()) -> Langfuse:
    """Build the masked client and verify the server and keys now, not silently per turn."""
    global _client
    require_langfuse_settings(settings)
    client = Langfuse(
        public_key=_secret(settings.langfuse_public_key),
        secret_key=_secret(settings.langfuse_secret_key),
        base_url=settings.langfuse_base_url,
        tracing_enabled=True,
        sample_rate=1.0,
        mask_otel_spans=make_mask(name_pattern(customer_names)),
    )
    try:
        ok = client.auth_check()
    except Exception:
        logger.exception("Langfuse auth_check raised")
        ok = False
    if not ok:
        client.shutdown()  # do not leave its exporter threads running behind the error
        raise LangfuseUnreachable(settings.langfuse_base_url)
    _client = client
    return client


def shutdown_tracing() -> None:
    """Flush the last batch; call from the API lifespan exit and at the end of CLI/evals."""
    if _client is not None:
        _client.shutdown()
