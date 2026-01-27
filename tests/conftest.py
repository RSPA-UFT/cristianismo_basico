"""Shared pytest fixtures for the cristianismo-basico test suite.

This module provides reusable fixtures and builder functions that produce
realistic Portuguese theological data matching the models and LLM response
formats used throughout the project.

Fixtures
--------
- tmp_output_dir       : temporary directory tree with output/, chunks/, per_chapter/
- test_settings        : Settings instance pointing to tmp dirs (ollama provider)
- sample_extraction_result : ExtractionResult with markdown headings
- sample_chunk         : ChunkInfo for chapter 1
- sample_citation      : biblical Citation for Jo 3:16
- sample_thesis        : Thesis with id T1.1.1
- sample_chapter_analysis : ChapterAnalysis with 2 theses and 2 citations
- sample_book_analysis : BookAnalysis with theses, chains, citations, summary

Builder functions (plain helpers, not fixtures)
-----------------------------------------------
- make_thesis_extraction_response()
- make_chain_extraction_response()
- make_citation_correlation_response()
- make_dedup_response()
- make_synthesis_response()
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.config import Settings
from src.models import (
    BookAnalysis,
    ChapterAnalysis,
    ChunkInfo,
    Citation,
    ExtractionResult,
    PageText,
    Thesis,
    ThesisChain,
)


# ---------------------------------------------------------------------------
# Directory and configuration fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create and return a temporary output directory tree.

    Structure::

        <tmp_path>/output/
        <tmp_path>/output/chunks/
        <tmp_path>/output/per_chapter/
    """
    output = tmp_path / "output"
    output.mkdir()
    (output / "chunks").mkdir()
    (output / "per_chapter").mkdir()
    return output


@pytest.fixture()
def test_settings(tmp_output_dir: Path) -> Settings:
    """Return a Settings instance suitable for testing.

    - Uses the ollama provider so no real API keys are required.
    - Points project_dir and output_dir to temporary paths.
    - All LLM parameters are set to deterministic defaults.
    """
    return Settings(
        llm_provider="ollama",
        ollama_model="qwen2.5:14b",
        ollama_reasoning_model="deepseek-r1:32b",
        ollama_base_url="http://localhost:11434/v1",
        openai_api_key="",
        openai_model="gpt-4o",
        anthropic_api_key="",
        anthropic_model="claude-sonnet-4-20250514",
        llm_temperature=0.3,
        llm_max_retries=3,
        project_dir=tmp_output_dir.parent,
        pdf_filename="Cristianismo_Basico_John_Stott.pdf",
        output_dir=tmp_output_dir,
    )


# ---------------------------------------------------------------------------
# Model instance fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_extraction_result() -> ExtractionResult:
    """Return a realistic ExtractionResult with markdown heading structure.

    The text contains two top-level sections (## headings) that mirror the
    book's prefacio and first chapter, providing enough structure for the
    chunker to split on.
    """
    prefacio_text = (
        "## PREFACIO\n\n"
        "O proposito deste livro e apresentar a essencia do cristianismo "
        "historico tal como se encontra no Novo Testamento. Nao pretende "
        "ser uma obra de teologia sistematica, mas uma tentativa de "
        "descrever a pessoa e a obra de Cristo de maneira acessivel ao "
        "leitor comum.\n\n"
        "John Stott busca demonstrar que o cristianismo e uma religiao "
        "fundamentada em evidencias historicas e em proposicoes racionais. "
        "A fe crista nao e um salto no escuro, mas uma confianca baseada "
        "em fatos.\n"
    )

    capitulo_text = (
        "## A ABORDAGEM CORRETA\n\n"
        "Antes de examinar as evidencias do cristianismo, precisamos "
        "adotar a abordagem correta. Muitas pessoas rejeitam o "
        "cristianismo sem jamais te-lo examinado seriamente. Outras "
        "aceitam-no por tradicao familiar, sem compreende-lo.\n\n"
        "A abordagem correta exige honestidade intelectual e disposicao "
        "para seguir as evidencias aonde quer que elas conduzam. Jesus "
        "disse: \"Se alguem quiser fazer a vontade de Deus, conhecera a "
        "respeito da doutrina\" (Jo 7:17). A busca pela verdade requer "
        "obediencia moral tanto quanto investigacao intelectual.\n\n"
        "Stott argumenta que a atitude de Cristo diante de seus criticos "
        "era de paciencia e convite ao exame honesto. Ele citava as "
        "Escrituras para fundamentar suas afirmacoes (cf. Mt 22:29; "
        "Jo 5:39).\n"
    )

    full_text = prefacio_text + "\n" + capitulo_text

    pages = [
        PageText(page_number=1, text=prefacio_text),
        PageText(page_number=2, text=capitulo_text[:len(capitulo_text) // 2]),
        PageText(page_number=3, text=capitulo_text[len(capitulo_text) // 2:]),
    ]

    return ExtractionResult(
        text=full_text,
        pages=pages,
        num_pages=3,
        total_chars=len(full_text),
        avg_chars_per_page=len(full_text) / 3,
        extraction_method="pymupdf",
        is_digital_pdf=True,
    )


@pytest.fixture()
def sample_chunk() -> ChunkInfo:
    """Return a ChunkInfo representing chapter 1 with realistic theological text."""
    text = (
        "## Capitulo 1 - A Pessoa de Cristo\n\n"
        "A questao central do cristianismo e a pessoa de Jesus Cristo. "
        "Quem foi ele? Qual era a sua verdadeira identidade? Ao longo "
        "dos seculos, muitas respostas foram propostas para esta "
        "pergunta fundamental.\n\n"
        "Stott argumenta que devemos ouvir o que o proprio Cristo "
        "disse a respeito de si mesmo. Suas afirmacoes foram de fato "
        "as mais surpreendentes que alguem ja fez. Ele declarou: "
        "\"Eu e o Pai somos um\" (Jo 10:30), e \"Quem me ve a mim "
        "ve o Pai\" (Jo 14:9).\n\n"
        "A evidencia dos Evangelhos demonstra que Jesus nao se "
        "apresentou meramente como um profeta ou mestre moral. Ele "
        "fez afirmacoes explicitas de divindade, reivindicando "
        "prerrogativas que pertencem somente a Deus, como perdoar "
        "pecados (Mc 2:5-7) e julgar o mundo (Mt 25:31-46).\n\n"
        "C.S. Lewis formulou o famoso trilema: Jesus era ou um "
        "mentiroso, ou um lunatico, ou verdadeiramente o Senhor. "
        "Nao ha espaco logico para considera-lo apenas um grande "
        "mestre moral se suas afirmacoes eram falsas.\n"
    )

    return ChunkInfo(
        index=0,
        title="Capitulo 1 - A Pessoa de Cristo",
        part="Parte 1 - A Pessoa de Cristo",
        chapter="Capitulo 1",
        part_index=1,
        chapter_index=1,
        text=text,
        char_count=len(text),
        page_range="15-32",
        source="markdown_heading",
    )


@pytest.fixture()
def sample_citation() -> Citation:
    """Return a biblical Citation for Jo 3:16."""
    return Citation(
        reference="Jo 3:16",
        text="Porque Deus amou o mundo de tal maneira que deu o seu Filho "
             "unigenito, para que todo aquele que nele cre nao pereca, mas "
             "tenha a vida eterna.",
        page=42,
        citation_type="biblical",
    )


@pytest.fixture()
def sample_thesis(sample_citation: Citation) -> Thesis:
    """Return a Thesis with id T1.1.1 including citations."""
    return Thesis(
        id="T1.1.1",
        title="Cristo afirmou ser Deus encarnado",
        description=(
            "Stott argumenta que Jesus nao se apresentou meramente como "
            "profeta ou mestre moral, mas fez afirmacoes explicitas de "
            "divindade, equiparando-se ao Pai. As evidencias dos Evangelhos "
            "mostram que ele reivindicou prerrogativas divinas."
        ),
        thesis_type="main",
        chapter="Capitulo 1",
        part="Parte 1 - A Pessoa de Cristo",
        page_range="15-32",
        supporting_text=(
            "Suas afirmacoes foram de fato as mais surpreendentes que "
            "alguem ja fez. Ele declarou: 'Eu e o Pai somos um'."
        ),
        citations=[
            sample_citation,
            Citation(
                reference="Jo 10:30",
                text="Eu e o Pai somos um",
                citation_type="biblical",
            ),
            Citation(
                reference="Jo 14:9",
                text="Quem me ve a mim ve o Pai",
                citation_type="biblical",
            ),
        ],
        confidence=0.95,
    )


@pytest.fixture()
def sample_chapter_analysis(
    sample_thesis: Thesis, sample_citation: Citation
) -> ChapterAnalysis:
    """Return a ChapterAnalysis with 2 theses and 2 citations."""
    second_thesis = Thesis(
        id="T1.1.2",
        title="O trilema de Lewis reforca a divindade de Cristo",
        description=(
            "C.S. Lewis argumentou que Jesus era ou mentiroso, ou lunatico, "
            "ou verdadeiramente Senhor. Nao ha espaco logico para "
            "considera-lo apenas um grande mestre moral se suas afirmacoes "
            "de divindade eram falsas."
        ),
        thesis_type="supporting",
        chapter="Capitulo 1",
        part="Parte 1 - A Pessoa de Cristo",
        page_range="15-32",
        supporting_text=(
            "Jesus era ou um mentiroso, ou um lunatico, ou verdadeiramente "
            "o Senhor."
        ),
        citations=[
            Citation(
                reference="Jo 10:30",
                text="Eu e o Pai somos um",
                citation_type="biblical",
            ),
        ],
        confidence=0.88,
    )

    second_citation = Citation(
        reference="Jo 10:30",
        text="Eu e o Pai somos um",
        page=28,
        citation_type="biblical",
    )

    return ChapterAnalysis(
        chunk_title="Capitulo 1 - A Pessoa de Cristo",
        theses=[sample_thesis, second_thesis],
        citations=[sample_citation, second_citation],
    )


@pytest.fixture()
def sample_book_analysis(
    sample_chapter_analysis: ChapterAnalysis,
) -> BookAnalysis:
    """Return a BookAnalysis with theses, chains, citations, summary, and argument flow."""
    theses = list(sample_chapter_analysis.theses)

    # Add a thesis from a later part to enable cross-part chains
    soteriologia_thesis = Thesis(
        id="T2.5.1",
        title="A natureza universal do pecado",
        description=(
            "Stott demonstra que o pecado e universal e afeta todas as "
            "dimensoes da existencia humana. Ninguem escapa de sua "
            "influencia, o que torna a obra redentora de Cristo "
            "absolutamente necessaria."
        ),
        thesis_type="main",
        chapter="Capitulo 5",
        part="Parte 2 - A Necessidade do Homem",
        page_range="78-95",
        supporting_text=(
            "Todos pecaram e destituidos estao da gloria de Deus."
        ),
        citations=[
            Citation(
                reference="Rm 3:23",
                text="Todos pecaram e destituidos estao da gloria de Deus",
                citation_type="biblical",
            ),
        ],
        confidence=0.92,
    )
    theses.append(soteriologia_thesis)

    chains = [
        ThesisChain(
            from_thesis_id="T1.1.1",
            to_thesis_id="T1.1.2",
            relationship="supports",
            reasoning_type="deductive",
            explanation=(
                "As afirmacoes de divindade de Cristo (T1.1.1) sao "
                "reafirmadas pelo trilema de Lewis (T1.1.2), que "
                "elimina logicamente as alternativas."
            ),
            strength=0.9,
        ),
        ThesisChain(
            from_thesis_id="T1.1.1",
            to_thesis_id="T2.5.1",
            relationship="precedes",
            reasoning_type="deductive",
            explanation=(
                "A confirmacao da divindade de Cristo (Parte 1) precede "
                "e fundamenta a compreensao da gravidade do pecado "
                "(Parte 2), pois e a santidade de Deus revelada em "
                "Cristo que expoe a profundidade do pecado humano."
            ),
            strength=0.85,
        ),
    ]

    citations = list(sample_chapter_analysis.citations) + [
        Citation(
            reference="Rm 3:23",
            text="Todos pecaram e destituidos estao da gloria de Deus",
            page=85,
            citation_type="biblical",
        ),
    ]

    return BookAnalysis(
        theses=theses,
        chains=chains,
        citations=citations,
        summary=(
            "Em 'Cristianismo Basico', John Stott apresenta o argumento "
            "central da fe crista em quatro partes progressivas. Na Parte 1, "
            "ele demonstra que Cristo fez afirmacoes explicitas de divindade, "
            "sustentadas por evidencias historicas e pelo trilema de Lewis. "
            "Na Parte 2, Stott expoe a universalidade e gravidade do pecado, "
            "mostrando que a necessidade humana de redencao e inescapavel. "
            "Na Parte 3, a obra de Cristo na cruz e apresentada como a "
            "unica solucao para o problema do pecado. Finalmente, na Parte 4, "
            "Stott descreve a resposta que se espera do ser humano: "
            "arrependimento, fe e obediencia."
        ),
        argument_flow=(
            "O livro segue uma progressao logica em 4 partes: primeiro "
            "estabelece quem Cristo e (Parte 1), depois diagnostica o "
            "problema humano do pecado (Parte 2), apresenta a solucao "
            "na cruz (Parte 3) e conclui com o chamado a resposta pessoal "
            "(Parte 4). Cada parte depende logicamente da anterior, formando "
            "um argumento cumulativo e coerente."
        ),
    )


# ---------------------------------------------------------------------------
# Builder functions -- return JSON strings matching LLM response formats
# ---------------------------------------------------------------------------


def make_thesis_extraction_response(
    *,
    theses: list[dict] | None = None,
    citations: list[dict] | None = None,
) -> str:
    """Build a JSON string matching the LLM thesis-extraction response format.

    This is the format expected by ``ThesisAnalyzer.analyze_chunk()``.

    Parameters
    ----------
    theses : list[dict] | None
        List of thesis dicts. If *None*, a realistic default is used.
    citations : list[dict] | None
        List of citation dicts. If *None*, a realistic default is used.

    Returns
    -------
    str
        A JSON-encoded string.
    """
    if theses is None:
        theses = [
            {
                "id": "T1",
                "title": "Cristo afirmou ser Deus encarnado",
                "description": (
                    "Stott argumenta que Jesus nao se apresentou meramente "
                    "como profeta ou mestre moral, mas fez afirmacoes "
                    "explicitas de divindade, equiparando-se ao Pai."
                ),
                "thesis_type": "main",
                "supporting_text": (
                    "Suas afirmacoes foram de fato as mais surpreendentes "
                    "que alguem ja fez."
                ),
                "citations": [
                    {
                        "reference": "Jo 10:30",
                        "text": "Eu e o Pai somos um",
                        "citation_type": "biblical",
                    },
                    {
                        "reference": "Jo 14:9",
                        "text": "Quem me ve a mim ve o Pai",
                        "citation_type": "biblical",
                    },
                ],
                "confidence": 0.95,
            },
            {
                "id": "T2",
                "title": "O trilema de Lewis elimina a opcao de 'grande mestre'",
                "description": (
                    "Lewis demonstrou que as afirmacoes de Jesus nao "
                    "permitem classifica-lo como apenas um bom mestre "
                    "moral. Ele era mentiroso, lunatico ou Senhor."
                ),
                "thesis_type": "supporting",
                "supporting_text": (
                    "Jesus era ou um mentiroso, ou um lunatico, ou "
                    "verdadeiramente o Senhor."
                ),
                "citations": [],
                "confidence": 0.88,
            },
        ]

    if citations is None:
        citations = [
            {
                "reference": "Jo 10:30",
                "text": "Eu e o Pai somos um",
                "citation_type": "biblical",
            },
            {
                "reference": "Jo 14:9",
                "text": "Quem me ve a mim ve o Pai",
                "citation_type": "biblical",
            },
            {
                "reference": "Mc 2:5-7",
                "text": "Filho, perdoados estao os teus pecados",
                "citation_type": "biblical",
            },
        ]

    payload = {"theses": theses, "citations": citations}
    return json.dumps(payload, ensure_ascii=False)


def make_chain_extraction_response(
    *,
    chains: list[dict] | None = None,
    argument_flow: str | None = None,
) -> str:
    """Build a JSON string matching the LLM chain-extraction response format.

    This is the format expected by ``ThesisAnalyzer.extract_chains()``.

    Parameters
    ----------
    chains : list[dict] | None
        List of chain dicts. If *None*, a realistic default is used.
    argument_flow : str | None
        Narrative summary of the book's argument. If *None*, a default is used.

    Returns
    -------
    str
        A JSON-encoded string.
    """
    if chains is None:
        chains = [
            {
                "from_thesis_id": "T1.1.1",
                "to_thesis_id": "T1.1.2",
                "relationship": "supports",
                "reasoning_type": "deductive",
                "explanation": (
                    "As afirmacoes de divindade de Cristo sao reafirmadas "
                    "pelo trilema de Lewis, que elimina logicamente as "
                    "alternativas."
                ),
                "strength": 0.9,
            },
            {
                "from_thesis_id": "T1.1.1",
                "to_thesis_id": "T2.5.1",
                "relationship": "precedes",
                "reasoning_type": "deductive",
                "explanation": (
                    "A divindade de Cristo revelada na Parte 1 precede a "
                    "compreensao da gravidade do pecado na Parte 2."
                ),
                "strength": 0.85,
            },
            {
                "from_thesis_id": "T2.5.1",
                "to_thesis_id": "T3.7.1",
                "relationship": "precedes",
                "reasoning_type": "inductive",
                "explanation": (
                    "O diagnostico do pecado universal prepara a necessidade "
                    "da cruz como unica solucao."
                ),
                "strength": 0.88,
            },
        ]

    if argument_flow is None:
        argument_flow = (
            "O livro segue uma progressao logica em 4 partes. Na Parte 1, "
            "Stott estabelece a divindade de Cristo atraves de suas "
            "afirmacoes e evidencias historicas. Na Parte 2, ele diagnostica "
            "o pecado humano como problema universal. Na Parte 3, apresenta "
            "a cruz como solucao divina. Na Parte 4, descreve a resposta "
            "esperada: arrependimento e fe."
        )

    payload = {"chains": chains, "argument_flow": argument_flow}
    return json.dumps(payload, ensure_ascii=False)


def make_citation_correlation_response(
    *,
    grouped_citations: list[dict] | None = None,
    cross_references: list[dict] | None = None,
) -> str:
    """Build a JSON string matching the LLM citation-correlation response format.

    This is the format expected by ``ThesisAnalyzer.correlate_citations()``.

    Parameters
    ----------
    grouped_citations : list[dict] | None
        Themed groups of citations. If *None*, a realistic default is used.
    cross_references : list[dict] | None
        Cross-reference entries. If *None*, a realistic default is used.

    Returns
    -------
    str
        A JSON-encoded string.
    """
    if grouped_citations is None:
        grouped_citations = [
            {
                "theme": "Cristologia - Divindade de Cristo",
                "description": (
                    "Passagens que atestam a divindade de Jesus Cristo, "
                    "incluindo suas auto-declaracoes e o testemunho dos "
                    "apostolos sobre sua natureza divina."
                ),
                "references": ["Jo 10:30", "Jo 14:9", "Jo 1:1", "Cl 2:9"],
                "related_thesis_ids": ["T1.1.1", "T1.1.2"],
            },
            {
                "theme": "Hamartiologia - Universalidade do pecado",
                "description": (
                    "Textos que demonstram a extensao universal do pecado "
                    "e seus efeitos sobre toda a humanidade."
                ),
                "references": ["Rm 3:23", "Rm 5:12", "Is 53:6"],
                "related_thesis_ids": ["T2.5.1"],
            },
            {
                "theme": "Soteriologia - Obra redentora de Cristo",
                "description": (
                    "Passagens centrais sobre a salvacao operada por Cristo "
                    "na cruz e a justificacao pela fe."
                ),
                "references": ["Jo 3:16", "Rm 5:8", "Ef 2:8-9", "1Pe 2:24"],
                "related_thesis_ids": ["T3.7.1"],
            },
        ]

    if cross_references is None:
        cross_references = [
            {
                "primary": "Jo 10:30",
                "related": ["Jo 14:9", "Jo 1:1"],
                "connection": (
                    "Todas as tres passagens atestam a unidade ontologica "
                    "entre Jesus e o Pai, fundamentando a cristologia de "
                    "Stott."
                ),
            },
            {
                "primary": "Rm 3:23",
                "related": ["Rm 5:12", "Is 53:6"],
                "connection": (
                    "Estas passagens convergem na afirmacao da "
                    "universalidade do pecado humano, cada uma enfatizando "
                    "um aspecto diferente da queda."
                ),
            },
        ]

    payload = {
        "grouped_citations": grouped_citations,
        "cross_references": cross_references,
    }
    return json.dumps(payload, ensure_ascii=False)


def make_dedup_response(
    *,
    duplicates: list[dict] | None = None,
) -> str:
    """Build a JSON string matching the LLM dedup response format.

    This is the format expected by ``ThesisAnalyzer._dedup_part()``.

    Parameters
    ----------
    duplicates : list[dict] | None
        List of duplicate pairs to remove. If *None*, returns an empty list
        (no duplicates found).

    Returns
    -------
    str
        A JSON-encoded string.
    """
    if duplicates is None:
        duplicates = []

    payload = {"duplicates": duplicates}
    return json.dumps(payload, ensure_ascii=False)


def make_synthesis_response(
    *,
    theses: list[dict] | None = None,
    summary: str | None = None,
) -> str:
    """Build a JSON string matching the LLM synthesis response format.

    This is the format expected by ``ThesisAnalyzer.synthesize()``.

    Parameters
    ----------
    theses : list[dict] | None
        Final selected theses. If *None*, a realistic default set is used.
    summary : str | None
        Executive summary of the book's argument. If *None*, a default is used.

    Returns
    -------
    str
        A JSON-encoded string.
    """
    if theses is None:
        theses = [
            {
                "id": "T1.1.1",
                "title": "Cristo afirmou ser Deus encarnado",
                "description": (
                    "Stott argumenta que Jesus fez afirmacoes explicitas "
                    "de divindade, equiparando-se ao Pai."
                ),
                "thesis_type": "main",
                "chapter": "Capitulo 1",
                "part": "Parte 1 - A Pessoa de Cristo",
                "supporting_text": (
                    "Suas afirmacoes foram de fato as mais surpreendentes "
                    "que alguem ja fez."
                ),
                "citations": [
                    {
                        "reference": "Jo 10:30",
                        "text": "Eu e o Pai somos um",
                        "citation_type": "biblical",
                    },
                ],
                "confidence": 0.95,
            },
            {
                "id": "T2.5.1",
                "title": "A natureza universal do pecado",
                "description": (
                    "Stott demonstra que o pecado e universal e afeta todas "
                    "as dimensoes da existencia humana."
                ),
                "thesis_type": "main",
                "chapter": "Capitulo 5",
                "part": "Parte 2 - A Necessidade do Homem",
                "supporting_text": (
                    "Todos pecaram e destituidos estao da gloria de Deus."
                ),
                "citations": [
                    {
                        "reference": "Rm 3:23",
                        "text": "Todos pecaram e destituidos estao da gloria de Deus",
                        "citation_type": "biblical",
                    },
                ],
                "confidence": 0.92,
            },
            {
                "id": "T3.7.1",
                "title": "A morte de Cristo como substituicao penal",
                "description": (
                    "Stott defende que a morte de Jesus na cruz foi um "
                    "sacrificio substitutivo, no qual ele assumiu a penalidade "
                    "do pecado em lugar da humanidade."
                ),
                "thesis_type": "main",
                "chapter": "Capitulo 7",
                "part": "Parte 3 - A Obra de Cristo",
                "supporting_text": (
                    "Ele mesmo levou em seu corpo os nossos pecados sobre "
                    "o madeiro."
                ),
                "citations": [
                    {
                        "reference": "1Pe 2:24",
                        "text": (
                            "Ele mesmo levou em seu corpo os nossos pecados "
                            "sobre o madeiro"
                        ),
                        "citation_type": "biblical",
                    },
                ],
                "confidence": 0.93,
            },
        ]

    if summary is None:
        summary = (
            "Em 'Cristianismo Basico', John Stott apresenta o argumento "
            "central da fe crista em quatro partes progressivas. Na Parte 1, "
            "ele demonstra a divindade de Cristo. Na Parte 2, expoe a "
            "universalidade do pecado. Na Parte 3, apresenta a cruz como "
            "solucao. Na Parte 4, descreve a resposta esperada do homem."
        )

    payload = {"theses": theses, "summary": summary}
    return json.dumps(payload, ensure_ascii=False)
