from pathlib import Path

import pdfplumber  # pyright: ignore[reportMissingTypeStubs]

from emporio.platform.paths import POLICIES_PDF
from emporio.policies.domain.policy_chunk import PolicyChunk
from emporio.policies.domain.sections import clean_lines, parse_sections


def read_policy_chunks(pdf: Path = POLICIES_PDF) -> tuple[PolicyChunk, ...]:
    with pdfplumber.open(pdf) as document:  # pyright: ignore[reportUnknownMemberType]
        pages = [str(page.extract_text() or "") for page in document.pages]  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportUnknownVariableType]
    return parse_sections(clean_lines(pages))


class PdfPolicySource:
    def __init__(self, pdf: Path = POLICIES_PDF) -> None:
        self._pdf = pdf

    def chunks(self) -> tuple[PolicyChunk, ...]:
        return read_policy_chunks(self._pdf)
