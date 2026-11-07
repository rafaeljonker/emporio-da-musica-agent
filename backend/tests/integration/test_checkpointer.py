import os

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres import PostgresSaver

from emporio.platform.config import Settings
from emporio.platform.db import database_url
from emporio.platform.migrate import setup_checkpointer
from emporio.support.domain.channel_identity import ChannelIdentity
from emporio.support.domain.scope import Scope
from emporio.support.infrastructure.agent.graph import build_graph
from emporio.support.infrastructure.agent.runner import GraphRunner
from emporio.support.infrastructure.agent.tools import build_tools
from emporio.support.infrastructure.checkpointer import make_checkpointer
from tests.fakes.fake_chat_model import FakeToolCallingModel
from tests.fakes.recording_tracer import RecordingTracer
from tests.pg_guard import pg_skip_reason
from tests.unit.support.test_tools import make_box

pytestmark = pytest.mark.postgres


def test_checkpointer_persists_thread(pg_conn: object) -> None:
    assert pg_skip_reason(os.environ.get("DATABASE_URL")) is None
    setup_checkpointer(database_url())
    setup_checkpointer(database_url())  # idempotent
    ident = ChannelIdentity("web", 14, "s")
    savers: list[PostgresSaver] = []
    try:
        for texts in (["Oi."], ["De novo."]):
            saver = make_checkpointer(database_url())  # new pool per turn: a "restart"
            savers.append(saver)
            model = FakeToolCallingModel(messages=iter(AIMessage(t) for t in texts))
            graph = build_graph(model, build_tools(make_box()), lambda _m: Scope.LOJA, saver)
            settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
            GraphRunner(graph, settings, RecordingTracer(), lambda _id: None).run(ident, "pergunta")
        state = graph.get_state({"configurable": {"thread_id": ident.thread_id()}})
        assert [m.text for m in state.values["messages"]] == [
            "pergunta", "Oi.", "pergunta", "De novo.",
        ]  # fmt: skip
    finally:
        savers[-1].delete_thread(ident.thread_id())
        for saver in savers:
            saver.conn.close()  # pyright: ignore[reportAttributeAccessIssue]
