import logging

from emporio.support.application.ports import AgentRunner, MetricsStore, Reply
from emporio.support.domain.ai_tells import ai_tells
from emporio.support.domain.bubbles import split_bubbles
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope

logger = logging.getLogger("emporio.support.handle_message")
CHAT_ERROR = "Perdi o fio da conversa aqui. Manda de novo?"


class HandleMessage:
    def __init__(self, runner: AgentRunner, metrics: MetricsStore) -> None:
        self._runner = runner
        self._metrics = metrics

    def __call__(self, identity: ChannelIdentity, text: str) -> Reply:
        if not text.strip():
            return Reply(split_bubbles(CHAT_ERROR), Scope.LOJA, "", (), None, failed=True)
        answer, scope, metrics = self._runner.run(identity, text)
        try:
            self._metrics.save(metrics)
        except Exception:  # a metrics outage must not lose a produced reply
            logger.exception("metrics save failed")
        bubbles = split_bubbles(answer)
        return Reply(
            bubbles,
            scope,
            metrics.trace_id,
            ai_tells("\n\n".join(bubbles)),  # measured on what the customer receives
            metrics,
            failed=metrics.failed,
        )
