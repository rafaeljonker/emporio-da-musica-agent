from emporio.policies.domain.policy_chunk import PolicyChunk
from emporio.policies.domain.sections import clean_lines, parse_sections

ZWSP = "​"
HEADER = "Empório da Música Manual de Políticas e Procedimentos"


def sections_before(n: int) -> list[str]:
    return [line for i in range(1, n) for line in (f"{i}. Seção {i}", f"Texto {i}.")]


def test_subsections_become_chunks_with_parent_title() -> None:
    chunks = parse_sections(
        ["1. Pagamento", "1.1 Parcelamento", "Até 3x sem juros.", "1.2 Boleto", "À vista."]
    )

    assert [(c.section_id, c.title, c.parent_title, c.body) for c in chunks] == [
        ("1.1", "Parcelamento", "Pagamento", "Até 3x sem juros."),
        ("1.2", "Boleto", "Pagamento", "À vista."),
    ]


def test_top_level_intro_becomes_own_chunk() -> None:
    chunks = parse_sections(["1. Sobre", "Loja fundada em 2008.", "1.1 Missão", "Democratizar."])

    assert chunks[0] == PolicyChunk("1", "Sobre", None, "Loja fundada em 2008.")
    assert chunks[1].section_id == "1.1"


def test_heading_without_body_is_dropped() -> None:
    chunks = parse_sections(["1. Frete", "1.1 Região", "Frete grátis.", "2. Promoções"])

    assert [c.section_id for c in chunks] == ["1.1"]


def test_numbered_steps_inside_subsection_are_not_headings() -> None:
    chunks = parse_sections(
        [
            *sections_before(7),
            "7. Atendimento",
            "7.2 Fluxo",
            "1. Saudação: cumprimentar.",
            "2. Entendimento: identificar.",
            "5. Fechamento: encerrar.",
            "8. Garantia",
            "Texto.",
        ]
    )

    assert [c.section_id for c in chunks] == [*(str(i) for i in range(1, 7)), "7.2", "8"]
    assert "Saudação" in chunks[6].body
    assert "Fechamento" in chunks[6].body


def test_clean_lines_drops_cover_header_footer_and_zwsp() -> None:
    pages = [
        "EMPÓRIO DA MÚSICA\nCapa",
        f"{HEADER}\n1. Sobre\n{ZWSP}\n{ZWSP}• Item\n\nPágina 2",
    ]

    assert clean_lines(pages) == ["1. Sobre", "• Item"]


def test_embedding_text_format() -> None:
    with_parent = PolicyChunk("4.1", "Arrependimento", "Trocas", "7 dias.")
    without_parent = PolicyChunk("2", "Horário", None, "09:00.")

    assert with_parent.embedding_text == "Trocas > 4.1 Arrependimento\n7 dias."
    assert without_parent.embedding_text == "2 Horário\n09:00."


def test_text_before_first_heading_is_not_a_chunk() -> None:
    chunks = parse_sections(["Sumário solto.", "1. Sobre", "Texto."])

    assert [c.section_id for c in chunks] == ["1"]
