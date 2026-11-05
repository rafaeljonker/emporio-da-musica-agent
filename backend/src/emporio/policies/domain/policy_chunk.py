from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PolicyChunk:
    section_id: str
    title: str
    parent_title: str | None
    body: str

    @property
    def embedding_text(self) -> str:
        heading = f"{self.section_id} {self.title}"
        if self.parent_title is not None:
            heading = f"{self.parent_title} > {heading}"
        return f"{heading}\n{self.body}"
