from pathlib import Path

import pytest

from emporio.orders.infrastructure.csv_order_repository import CsvOrderRepository, OrdersDataError
from emporio.paths import CASE_CSV_FILES


def test_short_row_raises_data_error_with_file_and_row(tmp_path: Path) -> None:
    bad = tmp_path / "customers.csv"
    bad.write_text("customer_id,name,phone,email,city\n1,Ana\n", encoding="utf-8")
    repo = CsvOrderRepository({**CASE_CSV_FILES, "customers": bad})
    with pytest.raises(OrdersDataError, match=r"customers\.csv, row 2"):
        repo.by_id(1)
