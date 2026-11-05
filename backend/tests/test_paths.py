from emporio import paths


def test_case_data_files_are_present():
    assert set(paths.CASE_CSV_FILES) == {
        "products",
        "promotions",
        "customers",
        "categories",
        "order_items",
        "orders",
    }
    for f in [*paths.CASE_CSV_FILES.values(), paths.POLICIES_PDF]:
        assert f.is_file()
        assert f.stat().st_size > 0, f
