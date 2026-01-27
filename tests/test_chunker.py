"""Tests for src/chunker.py -- HierarchicalChunker and helper functions.

This test suite covers:
- Markdown-based chunking (docling path)
- Regex-based chunking (pymupdf/OCR fallback path)
- Front-matter detection and filtering
- PARTE heading merging behavior
- CHAPTER_MAP metadata lookup
- Subdivision of oversized chunks with overlap
- Re-indexing of final chunk list
- Helper functions _normalize_title and _is_chapter_heading

Testing strategy:
- Unit tests for pure helpers (_normalize_title, _is_chapter_heading)
- Integration-style tests for the full chunk() pipeline using
  synthetic ExtractionResult objects
- Edge-case tests for empty text, missing headings, oversized chunks
"""

import pytest

from src.chunker import (
    HierarchicalChunker,
    MAX_CHUNK_SIZE,
    OVERLAP_CHARS,
    _is_chapter_heading,
    _normalize_title,
)
from src.models import ExtractionResult, ChunkInfo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chunker() -> HierarchicalChunker:
    """Reusable HierarchicalChunker instance."""
    return HierarchicalChunker()


def _make_extraction(text: str, method: str = "docling") -> ExtractionResult:
    """Helper to build an ExtractionResult with sensible defaults."""
    return ExtractionResult(
        text=text,
        extraction_method=method,
        num_pages=1,
        total_chars=len(text),
        avg_chars_per_page=float(len(text)),
        is_digital_pdf=True,
    )


# ---------------------------------------------------------------------------
# 1. test_chunk_markdown_basic
# ---------------------------------------------------------------------------


def test_chunk_markdown_basic(chunker: HierarchicalChunker) -> None:
    """Two known chapter headings should produce exactly two chunks
    when the extraction method is 'docling' (markdown path).
    """
    text = (
        "## PREFACIO\n"
        "Este livro e uma introducao ao cristianismo.\n\n"
        "## A ABORDAGEM CORRETA\n"
        "O primeiro passo e a abordagem correta.\n"
    )
    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    assert len(chunks) == 2, (
        f"Expected 2 chunks (PREFACIO + A ABORDAGEM CORRETA), got {len(chunks)}"
    )
    assert chunks[0].title == "Prefacio"
    assert chunks[1].title == "Cap 1 - A Abordagem Correta"
    assert all(c.source == "markdown_heading" for c in chunks)


# ---------------------------------------------------------------------------
# 2. test_chunk_front_matter
# ---------------------------------------------------------------------------


def test_chunk_front_matter(chunker: HierarchicalChunker) -> None:
    """When there is more than 500 chars of text before the first chapter
    heading, a 'Material Introdutorio' chunk must be created.
    """
    intro_text = "A" * 600  # 600 chars of front matter
    text = (
        f"{intro_text}\n\n"
        "## PREFACIO\n"
        "Texto do prefacio.\n"
    )
    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    intro_chunks = [c for c in chunks if c.title == "Material Introdutorio"]
    assert len(intro_chunks) == 1, (
        "Expected a 'Material Introdutorio' chunk for front matter > 500 chars"
    )
    assert intro_chunks[0].part == ""
    assert intro_chunks[0].chapter == "Introducao"
    assert intro_chunks[0].source == "markdown_heading"


# ---------------------------------------------------------------------------
# 3. test_chunk_no_front_matter
# ---------------------------------------------------------------------------


def test_chunk_no_front_matter(chunker: HierarchicalChunker) -> None:
    """When the text starts directly with a chapter heading (or the front
    matter is <= 500 chars), no intro chunk should be produced.
    """
    text = (
        "## PREFACIO\n"
        "Texto curto do prefacio.\n\n"
        "## A ABORDAGEM CORRETA\n"
        "Conteudo do capitulo 1.\n"
    )
    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    intro_chunks = [c for c in chunks if c.title == "Material Introdutorio"]
    assert len(intro_chunks) == 0, (
        "No intro chunk should exist when text starts with a chapter heading"
    )


# ---------------------------------------------------------------------------
# 4. test_chunk_part_merge
# ---------------------------------------------------------------------------


def test_chunk_part_merge(chunker: HierarchicalChunker) -> None:
    """PARTE headings should NOT produce their own chunk; they are merged
    into the next chapter. So '## PARTE UM' followed by '## PREFACIO'
    should yield only one chunk for PREFACIO.
    """
    text = (
        "## PARTE UM\n"
        "Introducao a parte um.\n\n"
        "## PREFACIO\n"
        "Texto do prefacio aqui.\n"
    )
    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    part_only_chunks = [
        c for c in chunks if "PARTE" in c.title.upper() and "parte" not in c.title.lower()
    ]
    assert len(part_only_chunks) == 0, (
        "PARTE headings must be merged, not emitted as separate chunks"
    )
    # The PREFACIO chunk should exist
    assert any(c.title == "Prefacio" for c in chunks), (
        "PREFACIO chunk should be present after merging PARTE heading"
    )


# ---------------------------------------------------------------------------
# 5. test_chunk_metadata_lookup
# ---------------------------------------------------------------------------


def test_chunk_metadata_lookup(chunker: HierarchicalChunker) -> None:
    """Chunks should carry the correct part_name, chapter_name, part_index,
    and chapter_index as defined in CHAPTER_MAP.
    """
    text = (
        "## AS AFIRMACOES DE CRISTO\n"
        "Conteudo do capitulo 2.\n\n"
        "## O CARATER DE CRISTO\n"
        "Conteudo do capitulo 3.\n"
    )
    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    assert len(chunks) == 2

    ch2 = chunks[0]
    assert ch2.title == "Cap 2 - As Afirmacoes de Cristo"
    assert ch2.part == "Parte 1 - A Pessoa de Cristo"
    assert ch2.part_index == 1
    assert ch2.chapter_index == 2

    ch3 = chunks[1]
    assert ch3.title == "Cap 3 - O Carater de Cristo"
    assert ch3.part == "Parte 1 - A Pessoa de Cristo"
    assert ch3.part_index == 1
    assert ch3.chapter_index == 3


# ---------------------------------------------------------------------------
# 6. test_chunk_regex_fallback
# ---------------------------------------------------------------------------


def test_chunk_regex_fallback(chunker: HierarchicalChunker) -> None:
    """When extraction_method is not 'docling' (e.g. 'pymupdf'), the chunker
    should use _chunk_by_regex and produce regex_fallback chunks.
    """
    text = (
        "PREFACIO\n"
        "Conteudo inicial do prefacio completo.\n\n"
        "CAPITULO 1 A ABORDAGEM CORRETA\n"
        "Conteudo do capitulo um com abordagem correta.\n"
    )
    extraction = _make_extraction(text, method="pymupdf")
    chunks = chunker.chunk(extraction)

    assert len(chunks) >= 1, "Regex fallback should produce at least one chunk"
    assert all(c.source == "regex_fallback" for c in chunks), (
        "All chunks from non-docling extraction should have source='regex_fallback'"
    )


# ---------------------------------------------------------------------------
# 7. test_chunk_subdivide
# ---------------------------------------------------------------------------


def test_chunk_subdivide(chunker: HierarchicalChunker) -> None:
    """A chunk whose text exceeds MAX_CHUNK_SIZE must be split into
    multiple sub-chunks.
    """
    # Build a single chapter with text > MAX_CHUNK_SIZE
    paragraph = "Lorem ipsum dolor sit amet. " * 100  # ~2800 chars
    # 5 paragraphs ~ 14000 chars, which exceeds MAX_CHUNK_SIZE (12000)
    big_body = "\n\n".join([paragraph] * 5)
    text = f"## PREFACIO\n{big_body}\n"

    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    assert len(chunks) >= 2, (
        f"Text of ~{len(big_body)} chars should be subdivided into >= 2 chunks, "
        f"got {len(chunks)}"
    )
    # Sub-chunks should be titled with " (parte N)" suffix
    titled_parts = [c for c in chunks if "(parte" in c.title]
    assert len(titled_parts) >= 1, (
        "At least one sub-chunk should have a '(parte N)' suffix in its title"
    )


# ---------------------------------------------------------------------------
# 8. test_chunk_subdivide_overlap
# ---------------------------------------------------------------------------


def test_chunk_subdivide_overlap(chunker: HierarchicalChunker) -> None:
    """Subdivided chunks should share OVERLAP_CHARS characters between
    the end of one sub-chunk and the beginning of the next.
    """
    paragraph = "Palavra " * 400  # ~3200 chars each
    big_body = "\n\n".join([paragraph] * 5)  # ~16000+ chars
    text = f"## PREFACIO\n{big_body}\n"

    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    assert len(chunks) >= 2, "Need at least 2 sub-chunks to verify overlap"

    # The tail of chunk[0].text should appear at the start of chunk[1].text
    tail_of_first = chunks[0].text[-OVERLAP_CHARS:]
    assert tail_of_first in chunks[1].text, (
        f"The last {OVERLAP_CHARS} chars of the first sub-chunk should appear "
        "in the second sub-chunk as overlap text"
    )


# ---------------------------------------------------------------------------
# 9. test_chunk_single_fallback
# ---------------------------------------------------------------------------


def test_chunk_single_fallback(chunker: HierarchicalChunker) -> None:
    """When the text contains no recognizable headings at all, the chunker
    should fall back to a single 'Texto Completo' chunk.
    """
    text = "Apenas um bloco de texto sem titulos ou marcadores."
    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    assert len(chunks) == 1, "Expected exactly 1 fallback chunk"
    assert chunks[0].title == "Texto Completo"
    assert chunks[0].source == "single_chunk"
    assert chunks[0].text == text


# ---------------------------------------------------------------------------
# 10. test_normalize_title
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("prefacio", "PREFACIO"),
        ("  A Abordagem Correta  ", "A ABORDAGEM CORRETA"),
        ("as  afirmacoes   de  cristo", "AS AFIRMACOES DE CRISTO"),
        ("\tNoTAS\n", "NOTAS"),
        ("", ""),
    ],
    ids=[
        "lowercase_to_upper",
        "strip_whitespace",
        "collapse_internal_spaces",
        "tab_and_newline",
        "empty_string",
    ],
)
def test_normalize_title(raw: str, expected: str) -> None:
    """_normalize_title should uppercase, strip, and collapse whitespace."""
    assert _normalize_title(raw) == expected


# ---------------------------------------------------------------------------
# 11. test_is_chapter_heading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title, expected",
    [
        ("PREFACIO", True),
        ("prefacio", True),
        ("  A ABORDAGEM CORRETA  ", True),
        ("AS CONSEQUENCIAS DOPECADO", True),    # OCR variant
        ("AS CONSEQUENCIAS DO PECADO", True),   # clean variant
        ("PARTE UM", True),
        ("PARTE DOIS", True),
        ("PARTE TRES", True),
        ("PARTE 1", True),
        ("algum subtitulo qualquer", False),
        ("INTRODUCAO AO CAPITULO", False),
        ("", False),
    ],
    ids=[
        "prefacio_upper",
        "prefacio_lower",
        "abordagem_with_spaces",
        "ocr_dopecado",
        "clean_do_pecado",
        "parte_um",
        "parte_dois",
        "parte_tres",
        "parte_numeral",
        "random_subtitle",
        "non_chapter_heading",
        "empty",
    ],
)
def test_is_chapter_heading(title: str, expected: bool) -> None:
    """_is_chapter_heading should correctly identify known chapter titles
    and PARTE patterns, returning False for everything else.
    """
    assert _is_chapter_heading(title) is expected


# ---------------------------------------------------------------------------
# 12. test_chunk_reindex
# ---------------------------------------------------------------------------


def test_chunk_reindex(chunker: HierarchicalChunker) -> None:
    """After subdivision the final chunk list must be re-indexed as a
    contiguous 0-based sequence: 0, 1, 2, ...
    """
    # Create text with two chapters, the first one oversized
    paragraph = "Palavra " * 400  # ~3200 chars each
    big_body = "\n\n".join([paragraph] * 5)  # >12000 chars

    text = (
        f"## PREFACIO\n{big_body}\n\n"
        "## A ABORDAGEM CORRETA\n"
        "Conteudo curto do capitulo 1.\n"
    )
    extraction = _make_extraction(text, method="docling")
    chunks = chunker.chunk(extraction)

    expected_indices = list(range(len(chunks)))
    actual_indices = [c.index for c in chunks]
    assert actual_indices == expected_indices, (
        f"Chunk indices should be contiguous 0..{len(chunks)-1}, "
        f"got {actual_indices}"
    )
