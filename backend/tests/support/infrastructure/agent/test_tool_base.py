from dataclasses import replace

import pytest

from emporio.shared.errors import StoreUnavailable
from emporio.support.infrastructure.agent import tools
from emporio.support.infrastructure.agent.tools import base
from tests.support.fakes import ANON, make_box


def test_store_unavailable_is_index_unavailable() -> None:
    @base.safe
    def boom() -> str:
        raise StoreUnavailable

    assert boom() == "Busca indisponível agora; ofereça encaminhar para a equipe."


def test_unexpected_exception_is_reduced_to_tool_name_and_type() -> None:
    def broken(question: str, k: int) -> object:
        raise RuntimeError("segredo@exemplo.com")

    box = replace(make_box(), search_policies=broken)  # pyright: ignore[reportArgumentType]
    with pytest.raises(tools.ToolCrashed) as crash:
        tools.search_policies(box, ANON, "troca")
    assert str(crash.value) == "search_policies raised RuntimeError"
