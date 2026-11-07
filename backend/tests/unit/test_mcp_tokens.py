import pytest
from pydantic import SecretStr

from emporio.config import ConfigError, Settings, mcp_token_identities

ANON = "a" * 32
CUSTOMER = "c" * 40


def _identities(raw: str) -> dict[str, int | None]:
    settings = Settings(_env_file=None, mcp_tokens=SecretStr(raw))  # pyright: ignore[reportCallIssue]  # pydantic-settings init kwarg
    return mcp_token_identities(settings)


def test_valid_pairs_map_tokens_to_identities():
    assert _identities(f"{ANON}=anon, {CUSTOMER}=14") == {ANON: None, CUSTOMER: 14}


def test_empty_setting_means_no_tokens():
    assert _identities("  ") == {}
    assert mcp_token_identities(Settings(_env_file=None)) == {}  # pyright: ignore[reportCallIssue]  # pydantic-settings init kwarg


def test_short_token_is_rejected_without_echoing_it():
    with pytest.raises(ConfigError, match="at least 32 characters") as exc:
        _identities("short-token=anon")
    assert "short-token" not in str(exc.value)


def test_duplicate_token_is_rejected_without_echoing_it():
    with pytest.raises(ConfigError, match="duplicate") as exc:
        _identities(f"{ANON}=anon,{ANON}=14")
    assert ANON not in str(exc.value)


@pytest.mark.parametrize("identity", ["", "bob", "-3", "14=2"])
def test_bad_identity_is_rejected_without_echoing_the_token(identity: str):
    with pytest.raises(ConfigError, match="customer id or anon") as exc:
        _identities(f"{ANON}={identity}")
    assert ANON not in str(exc.value)


def test_pair_without_identity_is_rejected_without_echoing_it():
    with pytest.raises(ConfigError, match="token=identity") as exc:
        _identities(ANON)
    assert ANON not in str(exc.value)
