from emporio.support.application.ports import AgentRunner, MetricsStore, Reply
from emporio.support.domain.ai_tells import ai_tells
from emporio.support.domain.bubbles import split_bubbles
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope

CHAT_ERROR = "Perdi o fio da conversa aqui. Manda de novo?"


class HandleMessage:
    def __init__(self, runner: AgentRunner, metrics: MetricsStore) -> None:
        self._runner = runner
        self._metrics = metrics

    def __call__(self, identity: ChannelIdentity, text: str) -> Reply:
        if not text.strip():
            return Reply(split_bubbles(CHAT_ERROR), Scope.LOJA, "", ())
        answer, scope, metrics = self._runner.run(identity, text)
        self._metrics.save(metrics)
        return Reply(split_bubbles(answer), scope, metrics.trace_id, ai_tells(answer))
