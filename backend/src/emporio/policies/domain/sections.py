import re
from collections.abc import Sequence

from emporio.policies.domain.policy_chunk import PolicyChunk

_ZERO_WIDTH_SPACE = "​"
_HEADER = "Empório da Música Manual de Políticas e Procedimentos"
_FOOTER = re.compile(r"^Página \d+$")
_TOP_HEADING = re.compile(r"^(\d+)\. (\S.*)$")
_SUB_HEADING = re.compile(r"^(\d+)\.(\d+) (\S.*)$")


def clean_lines(pages: Sequence[str]) -> list[str]:
    """Flatten pages (skipping the cover) into content lines, without header, footer or blanks."""
    lines = (
        line.replace(_ZERO_WIDTH_SPACE, "").strip()
        for page in pages[1:]
        for line in page.splitlines()
    )
    return [line for line in lines if line and line != _HEADER and not _FOOTER.match(line)]


def parse_sections(lines: Sequence[str]) -> tuple[PolicyChunk, ...]:
    """Split content lines into one chunk per numbered (sub)section.

    A heading only counts when its number follows the sequence, so numbered steps
    inside a subsection (7.2's "1. Saudação") stay in the body.
    """
    chunks: list[PolicyChunk] = []
    top_number = 0
    top_title = ""
    section_id = ""
    title = ""
    parent: str | None = None
    body: list[str] = []

    def flush() -> None:
        text = "\n".join(body)
        if text:
            chunks.append(PolicyChunk(section_id, title, parent, text))
        body.clear()

    for line in lines:
        top = _TOP_HEADING.match(line)
        sub = _SUB_HEADING.match(line)
        if top and int(top[1]) == top_number + 1:
            flush()
            top_number = int(top[1])
            top_title = top[2]
            section_id, title, parent = top[1], top_title, None
        elif sub and top_number and int(sub[1]) == top_number:
            flush()
            section_id, title, parent = f"{sub[1]}.{sub[2]}", sub[3], top_title
        else:
            body.append(line)
    flush()
    return tuple(chunks)
