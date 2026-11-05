import pytest

from emporio.orders.domain.identity import IdentityMismatch, matches_identity, normalize_phone
from tests.unit.orders.factories import cust


def test_phone_matches_with_country_code_and_formatting():
    c = cust(phone="(67) 98432-1098")
    assert matches_identity(c, "+55 (67) 98432-1098")
    assert matches_identity(c, "67984321098")


def test_email_matches_case_insensitive():
    assert matches_identity(cust(email="pedro.oliveira@jmail.com"), " Pedro.Oliveira@JMAIL.com ")


def test_wrong_email_does_not_match():
    assert not matches_identity(cust(email="a@b.com"), "joao.silva@gmail.com")


def test_wrong_phone_does_not_match():
    assert not matches_identity(cust(phone="(67) 98432-1098"), "(67) 90000-0000")


@pytest.mark.parametrize("raw", ["", "   ", "abc"])
def test_empty_or_non_digit_input_never_matches(raw: str):
    assert not matches_identity(cust(phone="", email=""), raw)


def test_normalize_phone_keeps_digits_and_strips_country_code():
    assert normalize_phone("+55 (67) 98432-1098") == "67984321098"
    assert normalize_phone("5511912345678") == "11912345678"
    assert normalize_phone("55123456789") == "55123456789"  # 11 digits: not a country code


def test_identity_mismatch_message_carries_no_data():
    assert str(IdentityMismatch()) == "identity does not match the order's customer"
