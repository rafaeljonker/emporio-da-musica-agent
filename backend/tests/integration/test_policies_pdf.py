from emporio.policies.infrastructure.pdf_sections import PdfPolicySource, read_policy_chunks

EXPECTED_IDS = [
    "1", "1.1", "1.2", "2", "3", "3.1", "4", "4.1", "4.2", "4.3", "4.4", "5.1", "5.2",
    "5.3", "6.1", "6.2", "7", "7.1", "7.2", "7.3", "8.1", "8.2", "8.3", "9", "10",
]  # fmt: skip


def test_real_pdf_yields_25_sections() -> None:
    chunks = read_policy_chunks()

    assert [c.section_id for c in chunks] == EXPECTED_IDS
    assert all(100 <= len(c.body) <= 900 for c in chunks)
    hours = next(c for c in chunks if c.section_id == "2")
    assert "09:00" in hours.body
    assert "Domingo" in hours.body


def test_pdf_source_returns_same_chunks() -> None:
    assert PdfPolicySource().chunks() == read_policy_chunks()
