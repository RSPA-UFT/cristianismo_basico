"""Tests for the OutputWriter class in src/output.py.

This module tests every public method of OutputWriter plus the private
_generate_report helper.  All tests use pytest's tmp_path fixture so that
files are written to a temporary directory that is automatically cleaned up.

Testing strategy
----------------
- Happy-path validation for every method (files created, content correct).
- Edge-case coverage for filename sanitisation (special characters in titles).
- Structural verification of generated JSON and Markdown outputs.
- Section-level checks for the Markdown report generator.
"""

import json

import pytest

from src.config import Settings
from src.models import (
    BookAnalysis,
    ChapterAnalysis,
    ChunkInfo,
    Citation,
    ExtractionResult,
    Thesis,
    ThesisChain,
)
from src.output import OutputWriter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def writer(tmp_path):
    """Return an OutputWriter backed by a temporary output directory."""
    cfg = Settings(output_dir=tmp_path / "output")
    cfg.ensure_output_dirs()
    return OutputWriter(cfg)


@pytest.fixture
def sample_extraction() -> ExtractionResult:
    """Minimal ExtractionResult for testing save_extracted_text."""
    return ExtractionResult(
        text="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        num_pages=10,
        total_chars=56,
        avg_chars_per_page=5.6,
        extraction_method="pymupdf",
        is_digital_pdf=True,
    )


@pytest.fixture
def sample_chunks() -> list[ChunkInfo]:
    """Two chunks with simple titles."""
    return [
        ChunkInfo(
            index=0,
            title="Introducao",
            part="Parte 1",
            chapter="Capitulo 1",
            text="Texto da introducao.",
            char_count=20,
            source="markdown_heading",
        ),
        ChunkInfo(
            index=1,
            title="O Argumento Cristao",
            part="Parte 1",
            chapter="Capitulo 2",
            text="Texto do argumento.",
            char_count=19,
            source="markdown_heading",
        ),
    ]


@pytest.fixture
def sample_chapter_analysis() -> ChapterAnalysis:
    """A ChapterAnalysis with one thesis and one citation."""
    return ChapterAnalysis(
        chunk_title="Capitulo 1 - O Argumento Cristao",
        theses=[
            Thesis(
                id="T1.1.1",
                title="Cristo como Deus",
                description="Stott defende a divindade de Cristo.",
                thesis_type="main",
                chapter="Capitulo 1",
                part="Parte 1",
                confidence=0.95,
                citations=[
                    Citation(reference="Jo 1:1", citation_type="biblical"),
                ],
            ),
        ],
        citations=[
            Citation(reference="Jo 1:1", citation_type="biblical"),
        ],
    )


@pytest.fixture
def sample_book_analysis() -> BookAnalysis:
    """A BookAnalysis with theses, chains, citations, summary, and flow."""
    thesis_main = Thesis(
        id="T1.1.1",
        title="Cristo como Deus",
        description="Stott defende a divindade de Cristo.",
        thesis_type="main",
        chapter="Capitulo 1",
        part="Parte 1",
        confidence=0.95,
        supporting_text="No principio era o Verbo.",
        citations=[Citation(reference="Jo 1:1", citation_type="biblical")],
    )
    thesis_support = Thesis(
        id="T1.1.2",
        title="Evidencia historica",
        description="Registros historicos corroboram.",
        thesis_type="supporting",
        chapter="Capitulo 1",
        part="Parte 1",
        confidence=0.85,
    )
    chain = ThesisChain(
        from_thesis_id="T1.1.1",
        to_thesis_id="T1.1.2",
        relationship="supports",
        reasoning_type="deductive",
        explanation="A divindade implica evidencias historicas.",
        strength=0.9,
    )
    citation_bib = Citation(reference="Jo 1:1", citation_type="biblical")
    citation_sch = Citation(reference="Stott 1958", citation_type="scholarly")

    return BookAnalysis(
        theses=[thesis_main, thesis_support],
        chains=[chain],
        citations=[citation_bib, citation_sch],
        summary="Este livro apresenta o argumento central do cristianismo.",
        argument_flow="Parte 1 introduz a pessoa de Cristo.",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSaveExtractedText:
    """Tests for OutputWriter.save_extracted_text."""

    def test_save_extracted_text(self, writer, sample_extraction):
        """The header must contain the extraction method and page count."""
        path = writer.save_extracted_text(sample_extraction)

        assert path.exists(), "extracted_text.md was not created"
        content = path.read_text(encoding="utf-8")

        # Verify header metadata
        assert "pymupdf" in content, "Extraction method missing from header"
        assert "10" in content, "Page count missing from header"
        assert "56" in content, "Total chars missing from header"

    def test_save_extracted_text_content(self, writer, sample_extraction):
        """The actual body text must appear after the --- separator."""
        path = writer.save_extracted_text(sample_extraction)
        content = path.read_text(encoding="utf-8")

        # Split on the horizontal rule; body comes after it
        parts = content.split("---")
        assert len(parts) >= 2, "Expected --- separator in extracted text file"

        body = parts[-1]
        assert "Lorem ipsum" in body, (
            "Expected body text after the --- separator"
        )


class TestSaveChunks:
    """Tests for OutputWriter.save_chunks."""

    def test_save_chunks(self, writer, sample_chunks):
        """Two chunks should produce two .md files with correct names."""
        paths = writer.save_chunks(sample_chunks)

        assert len(paths) == 2, f"Expected 2 chunk files, got {len(paths)}"
        assert paths[0].name.startswith("chunk_00_"), (
            f"First chunk filename unexpected: {paths[0].name}"
        )
        assert paths[1].name.startswith("chunk_01_"), (
            f"Second chunk filename unexpected: {paths[1].name}"
        )
        for p in paths:
            assert p.exists(), f"Chunk file {p} was not created"

    def test_save_chunks_sanitized_names(self, writer):
        """Special characters in chunk titles must be stripped/replaced."""
        chunk = ChunkInfo(
            index=0,
            title="Cap/3 - Vida & Morte!?",
            text="Texto especial.",
            char_count=15,
            source="regex_fallback",
        )
        paths = writer.save_chunks([chunk])

        filename = paths[0].name
        assert "/" not in filename, "Slash should be removed from filename"
        assert "&" not in filename, "Ampersand should be removed from filename"
        assert "!" not in filename, "Exclamation mark should be removed"
        assert "?" not in filename, "Question mark should be removed"
        assert filename.startswith("chunk_00_"), (
            f"Unexpected filename prefix: {filename}"
        )
        assert filename.endswith(".md"), "Chunk file must end with .md"


class TestSaveChapterAnalysis:
    """Tests for OutputWriter.save_chapter_analysis."""

    def test_save_chapter_analysis(self, writer, sample_chapter_analysis):
        """JSON file must be created and contain expected keys."""
        path = writer.save_chapter_analysis(sample_chapter_analysis, index=1)

        assert path.exists(), "Chapter analysis JSON was not created"
        assert path.name == "chapter_01_theses.json", (
            f"Unexpected filename: {path.name}"
        )

        data = json.loads(path.read_text(encoding="utf-8"))
        assert "chunk_title" in data, "Missing 'chunk_title' key in JSON"
        assert "theses" in data, "Missing 'theses' key in JSON"
        assert "citations" in data, "Missing 'citations' key in JSON"
        assert len(data["theses"]) == 1, "Expected exactly 1 thesis"
        assert data["theses"][0]["id"] == "T1.1.1"


class TestSaveBookAnalysis:
    """Tests for OutputWriter.save_book_analysis."""

    def test_save_book_analysis_creates_files(self, writer, sample_book_analysis):
        """All four output files must be created."""
        paths = writer.save_book_analysis(sample_book_analysis)

        expected_keys = {"theses", "chains", "citations", "report"}
        assert set(paths.keys()) == expected_keys, (
            f"Returned path keys {set(paths.keys())} != {expected_keys}"
        )

        assert paths["theses"].name == "theses.json"
        assert paths["chains"].name == "chains.json"
        assert paths["citations"].name == "citations.json"
        assert paths["report"].name == "report.md"

        for key, p in paths.items():
            assert p.exists(), f"{key} file was not created at {p}"

    def test_save_book_analysis_theses_content(self, writer, sample_book_analysis):
        """theses.json must contain the correct thesis data."""
        paths = writer.save_book_analysis(sample_book_analysis)
        theses_data = json.loads(
            paths["theses"].read_text(encoding="utf-8")
        )

        assert isinstance(theses_data, list), "theses.json must be a JSON list"
        assert len(theses_data) == 2, "Expected 2 theses"
        assert theses_data[0]["id"] == "T1.1.1"
        assert theses_data[0]["title"] == "Cristo como Deus"
        assert theses_data[1]["id"] == "T1.1.2"
        assert theses_data[1]["thesis_type"] == "supporting"


class TestSaveCitationCorrelation:
    """Tests for OutputWriter.save_citation_correlation."""

    def test_save_citation_correlation(self, writer):
        """The saved JSON must round-trip correctly."""
        correlation = {
            "biblical": [
                {"reference": "Jo 1:1", "count": 3},
                {"reference": "Rm 8:28", "count": 1},
            ],
            "scholarly": [
                {"reference": "Stott 1958", "count": 2},
            ],
        }
        path = writer.save_citation_correlation(correlation)

        assert path.exists(), "citation_groups.json was not created"
        assert path.name == "citation_groups.json"

        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded == correlation, (
            "Round-tripped JSON does not match original"
        )


class TestGenerateReport:
    """Tests for OutputWriter._generate_report (private helper)."""

    def test_generate_report_summary(self, writer, sample_book_analysis):
        """Report must contain the Resumo Executivo section and summary text."""
        report = writer._generate_report(sample_book_analysis)

        assert "## Resumo Executivo" in report, (
            "Missing 'Resumo Executivo' section heading"
        )
        assert sample_book_analysis.summary in report, (
            "Summary text not found in report"
        )
        assert "## Fluxo Argumentativo" in report, (
            "Missing 'Fluxo Argumentativo' section heading"
        )

    def test_generate_report_statistics(self, writer, sample_book_analysis):
        """Report must include a statistics table with correct values."""
        report = writer._generate_report(sample_book_analysis)

        assert "## Estatisticas" in report, (
            "Missing 'Estatisticas' section heading"
        )
        # Table header row
        assert "| Metrica | Valor |" in report, (
            "Statistics table header not found"
        )
        # Concrete counts from sample_book_analysis: 2 theses, 1 main, 1 supporting
        assert "| Total de teses | 2 |" in report, (
            "Total thesis count incorrect in stats table"
        )
        assert "| Teses principais (main) | 1 |" in report, (
            "Main thesis count incorrect in stats table"
        )
        assert "| Teses de suporte | 1 |" in report, (
            "Supporting thesis count incorrect in stats table"
        )
        # 1 biblical, 1 scholarly, 0 footnotes
        assert "| Citacoes biblicas | 1 |" in report
        assert "| Citacoes academicas | 1 |" in report

    def test_generate_report_chains(self, writer, sample_book_analysis):
        """When chains exist the report must include the chain graph section."""
        report = writer._generate_report(sample_book_analysis)

        assert "## Grafo de Encadeamento" in report, (
            "Missing 'Grafo de Encadeamento' section when chains are present"
        )
        # The arrow for non-contradicts relationships is the standard arrow
        assert "T1.1.1" in report, "from_thesis_id not found in chain graph"
        assert "T1.1.2" in report, "to_thesis_id not found in chain graph"
        assert "supports" in report, "Relationship label missing in chain graph"
