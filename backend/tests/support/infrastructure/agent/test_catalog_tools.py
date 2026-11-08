import pytest

from emporio.catalog.domain.product import ProductStatus
from emporio.support.infrastructure.agent import tools
from tests.catalog.fakes import product
from tests.support.fakes import ANON, make_box


def test_search_reports_discontinued_product() -> None:
    gone = product(id=1, name="Violao Antigo", status=ProductStatus.DISCONTINUED, stock=0)

    result = tools.search_products(make_box(gone), ANON, query="violao antigo")

    assert isinstance(result, dict)
    found = result["products"]
    assert isinstance(found, list)
    assert found[0]["status"] == "discontinued"


def test_calc_installments_error_names_the_maximum() -> None:
    result = tools.calc_installments(make_box(), ANON, total=100, count=10)

    assert isinstance(result, str)
    assert result.startswith("Esse parcelamento não é permitido para esse valor.")
    assert "O máximo é 2x" in result


def test_unknown_product_is_product_not_found_text() -> None:
    assert tools.get_product(make_box(), ANON, product_id=99) == "Produto não encontrado."


def test_calc_installments_huge_total_is_a_crash_not_text() -> None:
    # The edges cap the total (le=MAX_REAIS); past them, InvalidMoney is a bug.
    with pytest.raises(tools.ToolCrashed) as crash:
        tools.calc_installments(make_box(), ANON, total=1e30)
    assert str(crash.value) == "calc_installments raised InvalidMoney"
