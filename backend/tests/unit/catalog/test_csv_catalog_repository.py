from pathlib import Path

import pytest

from emporio.catalog.infrastructure.csv_catalog_repository import (
    CatalogDataError,
    CsvCatalogRepository,
)

_HEADER = "product_id,price_brl,name,category_id,description,stock_quantity,status,specs,created_at"


def _repo(tmp_path: Path, *rows: str) -> CsvCatalogRepository:
    path = tmp_path / "products.csv"
    path.write_text("\n".join([_HEADER, *rows]) + "\n", encoding="utf-8")
    return CsvCatalogRepository({"products": path})


def test_specs_are_sorted_and_stringified(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        '1,10.5,A,1,d,3,active,"{""b"":2,""a"":""x""}",2021-01-01',
        "2,9,B,1,d,0,active,,2021-01-01",
    )
    first, second = repo.products()
    assert first.specs == (("a", "x"), ("b", "2"))
    assert second.specs == ()


def test_bad_specs_json_names_file_and_row(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "1,10,A,1,d,3,active,{oops,2021-01-01")
    with pytest.raises(CatalogDataError, match=r"products\.csv.*row 2"):
        repo.products()


def test_bad_price_names_row(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "1,10,A,1,d,3,active,,2021-01-01", "2,abc,B,1,d,3,active,,2021-01-01")
    with pytest.raises(CatalogDataError, match="row 3"):
        repo.products()


def test_short_row_raises_data_error_with_file_and_row(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "1,10.5,A,1,d,3,active,")  # only the unparsed created_at is missing
    with pytest.raises(CatalogDataError, match=r"products\.csv, row 2"):
        repo.products()
