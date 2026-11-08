from dataclasses import FrozenInstanceError

import pytest

from emporio.shared.result import Err, Ok, Result


def test_ok_and_err_are_frozen() -> None:
    for result, field in ((Ok(1), "value"), (Err("boom"), "error")):
        with pytest.raises(FrozenInstanceError):
            setattr(result, field, "changed")


def _describe(result: Result[int, str]) -> str:
    match result:
        case Ok(value):
            return f"ok {value + 1}"
        case Err(error):
            return f"err {error.upper()}"


def test_match_narrows_ok_and_err() -> None:
    assert (_describe(Ok(1)), _describe(Err("no"))) == ("ok 2", "err NO")
