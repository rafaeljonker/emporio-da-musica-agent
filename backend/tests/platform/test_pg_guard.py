from tests.pg_guard import pg_skip_reason


def test_guard_refuses_a_database_not_named_test() -> None:
    assert pg_skip_reason("postgresql://u:p@nowhere/emporio") is not None


def test_guard_refuses_a_missing_url() -> None:
    assert pg_skip_reason(None) is not None


def test_guard_accepts_a_test_database() -> None:
    assert pg_skip_reason("postgresql://u:p@nowhere:5434/emporio_test") is None
