"""The pt-BR texts the agent and MCP clients read: one map per context, pinned byte for byte."""

from emporio.catalog.domain.errors import CatalogErrorCode
from emporio.orders.domain.errors import OrdersErrorCode
from emporio.support.application.handle_message import CHAT_ERROR
from emporio.support.infrastructure.agent import tools
from emporio.support.infrastructure.agent.graph import ABUSE_REPLY, NO_MORE_TOOLS
from emporio.support.infrastructure.agent.tools.base import INDEX_UNAVAILABLE, TOOL_FAILURE
from emporio.support.infrastructure.agent.tools.catalog import (
    CATALOG_TEXT,
    INSTALLMENTS_NOT_ALLOWED,
    PRODUCT_NOT_FOUND,
)
from emporio.support.infrastructure.agent.tools.orders import (
    ASK_EMAIL_OR_PHONE,
    ASK_ORDER_IDENTITY,
    ORDER_NOT_FOUND,
    ORDERS_TEXT,
)
from tests.unit.support.test_tools import ANON, make_box


def test_every_catalog_code_has_tool_text() -> None:
    assert set(CATALOG_TEXT) == set(CatalogErrorCode)


def test_every_orders_code_has_tool_text() -> None:
    assert set(ORDERS_TEXT) == set(OrdersErrorCode)


def test_tool_texts_unchanged() -> None:
    assert {
        "ORDER_NOT_FOUND": ORDER_NOT_FOUND,
        "ASK_ORDER_IDENTITY": ASK_ORDER_IDENTITY,
        "ASK_EMAIL_OR_PHONE": ASK_EMAIL_OR_PHONE,
        "INSTALLMENTS_NOT_ALLOWED": INSTALLMENTS_NOT_ALLOWED,
        "INDEX_UNAVAILABLE": INDEX_UNAVAILABLE,
        "PRODUCT_NOT_FOUND": PRODUCT_NOT_FOUND,
        "TOOL_FAILURE": TOOL_FAILURE,
        "CHAT_ERROR": CHAT_ERROR,
        "ABUSE_REPLY": ABUSE_REPLY,
        "NO_MORE_TOOLS": NO_MORE_TOOLS,
        "installments_past_max": tools.calc_installments(make_box(), ANON, total=1200, count=13),
    } == {
        "ORDER_NOT_FOUND": (
            "Os dados não conferem com nenhum pedido. Não revele nada sobre pedidos; "
            "peça para conferir o número e o e-mail ou telefone."
        ),
        "ASK_ORDER_IDENTITY": "Peça o número do pedido e o e-mail ou telefone do cadastro.",
        "ASK_EMAIL_OR_PHONE": "Peça o e-mail ou telefone do cadastro do pedido.",
        "INSTALLMENTS_NOT_ALLOWED": "Esse parcelamento não é permitido para esse valor.",
        "INDEX_UNAVAILABLE": "Busca indisponível agora; ofereça encaminhar para a equipe.",
        "PRODUCT_NOT_FOUND": "Produto não encontrado.",
        "TOOL_FAILURE": (
            "Não consegui consultar isso agora; ofereça passar o e-mail e o WhatsApp da loja."
        ),
        "CHAT_ERROR": "Perdi o fio da conversa aqui. Manda de novo?",
        "ABUSE_REPLY": (
            "Vamos manter a conversa respeitosa. "
            "Posso te ajudar com instrumentos, pedidos ou dúvidas da loja."
        ),
        "NO_MORE_TOOLS": "Responda com o que você já tem, sem chamar mais ferramentas.",
        "installments_past_max": (
            "Esse parcelamento não é permitido para esse valor. O máximo é 12x de R$ 100."
        ),
    }
