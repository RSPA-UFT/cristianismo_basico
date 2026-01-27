"""Tests for src.pipeline -- the main orchestrator module.

Covers:
- Full end-to-end pipeline execution with all external dependencies mocked.
- Cached extraction loading from an existing extracted_text.md file.
- Chapter-level JSON cache to skip LLM re-analysis.
- Graceful handling of a missing extraction cache file.

Strategy: Every test relies on extensive mocking so that no real PDF, LLM,
or filesystem side-effects occur.  We use ``tmp_path`` fixtures whenever we
need concrete directories on disk.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from src.pipeline import _load_cached_extraction, run_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_extraction(text: str = "x" * 1000) -> ExtractionResult:
    """Return a minimal ExtractionResult for test scaffolding."""
    return ExtractionResult(
        text=text,
        num_pages=10,
        total_chars=len(text),
        avg_chars_per_page=len(text) / 10,
        extraction_method="docling",
        is_digital_pdf=True,
    )


def _make_chunk(index: int = 0, title: str = "Capitulo 1") -> ChunkInfo:
    """Return a minimal ChunkInfo for test scaffolding."""
    return ChunkInfo(
        index=index,
        title=title,
        text="Some chapter text " * 50,
        char_count=900,
        source="markdown_heading",
    )


def _make_chapter_analysis(
    title: str = "Capitulo 1",
    chapter: str = "Cap 1",
) -> ChapterAnalysis:
    """Return a ChapterAnalysis with one thesis and one citation."""
    return ChapterAnalysis(
        chunk_title=title,
        theses=[
            Thesis(
                id="T1.1.1",
                title="Test thesis",
                description="A test thesis description",
                chapter=chapter,
                supporting_text="This is a long enough supporting text for testing purposes here.",
                citations=[
                    Citation(
                        reference="Jo 3:16",
                        text="For God so loved",
                        citation_type="biblical",
                    )
                ],
                confidence=0.9,
            )
        ],
        citations=[
            Citation(
                reference="Jo 3:16",
                text="For God so loved",
                citation_type="biblical",
            )
        ],
    )


def _make_settings(tmp_path: Path) -> Settings:
    """Build a Settings instance pointing at *tmp_path* directories."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    per_chapter = output_dir / "per_chapter"
    per_chapter.mkdir(exist_ok=True)
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    # Create a dummy PDF path (does not need to exist for mocked tests)
    pdf_path = tmp_path / "book.pdf"
    pdf_path.touch()

    return Settings(
        project_dir=tmp_path,
        pdf_filename="book.pdf",
        output_dir=output_dir,
        llm_provider="ollama",
    )


# ---------------------------------------------------------------------------
# Test 1: Full end-to-end pipeline
# ---------------------------------------------------------------------------

class TestRunPipelineEndToEnd:
    """Mock every external collaborator and verify run_pipeline returns a
    BookAnalysis with expected attributes."""

    @patch("src.pipeline.OutputWriter")
    @patch("src.pipeline.ThesisAnalyzer")
    @patch("src.pipeline.HierarchicalChunker")
    @patch("src.pipeline.PDFExtractor")
    @patch("src.pipeline._load_cached_extraction", return_value=None)
    def test_pipeline_end_to_end(
        self,
        mock_load_cache,
        mock_extractor_cls,
        mock_chunker_cls,
        mock_analyzer_cls,
        mock_writer_cls,
        tmp_path,
    ):
        """Full pipeline run: extract -> chunk -> analyze -> output.

        Asserts that:
        - run_pipeline returns a BookAnalysis instance.
        - PDFExtractor.extract was called once (cache miss).
        - HierarchicalChunker.chunk was called with the extraction result.
        - ThesisAnalyzer methods (analyze_chunk, extract_chains,
          correlate_citations, synthesize) were all invoked.
        - OutputWriter.save_book_analysis was called with the final analysis.
        """
        cfg = _make_settings(tmp_path)

        # -- PDFExtractor mock --
        extraction = _make_extraction()
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = extraction
        mock_extractor_cls.return_value = mock_extractor

        # -- HierarchicalChunker mock --
        chunk = _make_chunk()
        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [chunk]
        mock_chunker_cls.return_value = mock_chunker

        # -- ThesisAnalyzer mock --
        chapter_analysis = _make_chapter_analysis()
        mock_analyzer = MagicMock()
        mock_analyzer.analyze_chunk.return_value = chapter_analysis
        mock_analyzer.extract_chains.return_value = (
            [
                ThesisChain(
                    from_thesis_id="T1.1.1",
                    to_thesis_id="T1.1.2",
                    relationship="supports",
                )
            ],
            "argument flow text",
        )
        mock_analyzer.correlate_citations.return_value = {"corr": "data"}
        mock_analyzer.synthesize.return_value = (
            chapter_analysis.theses,
            "Final summary",
        )
        mock_analyzer_cls.return_value = mock_analyzer

        # -- OutputWriter mock --
        mock_writer = MagicMock()
        mock_writer.save_book_analysis.return_value = {"report": "/tmp/report.md"}
        mock_writer_cls.return_value = mock_writer

        # -- Act --
        result = run_pipeline(cfg)

        # -- Assert --
        assert isinstance(result, BookAnalysis), (
            "run_pipeline must return a BookAnalysis instance"
        )
        assert len(result.theses) > 0, "BookAnalysis should contain at least one thesis"
        assert len(result.chains) == 1, "BookAnalysis should contain exactly one chain"
        assert result.summary == "Final summary"

        mock_extractor.extract.assert_called_once()
        mock_chunker.chunk.assert_called_once_with(extraction)
        mock_analyzer.analyze_chunk.assert_called_once_with(chunk)
        mock_analyzer.extract_chains.assert_called_once()
        mock_analyzer.correlate_citations.assert_called_once()
        mock_analyzer.synthesize.assert_called_once()
        mock_writer.save_book_analysis.assert_called_once()


# ---------------------------------------------------------------------------
# Test 2: Cached extraction loaded from disk
# ---------------------------------------------------------------------------

class TestLoadCachedExtraction:
    """Verify _load_cached_extraction reads the markdown cache and uses
    fitz to determine the page count."""

    def test_pipeline_cache_extraction(self, tmp_path):
        """Create a fake extracted_text.md with the expected metadata header,
        then verify _load_cached_extraction returns an ExtractionResult with
        the correct text body and page count.

        fitz is imported locally inside _load_cached_extraction, so we
        patch it via sys.modules before calling the function.
        """
        cfg = _make_settings(tmp_path)

        # Write a cache file with >500 chars after the header marker
        body_text = "A" * 800
        header = (
            "# Extraction Metadata\n"
            "Pages: 100\n"
            "Method: docling\n"
            "---\n\n"
        )
        cache_file = cfg.output_dir / "extracted_text.md"
        cache_file.write_text(header + body_text, encoding="utf-8")

        # Mock fitz.open to return a doc-like context-manager with len() == 100
        mock_fitz = MagicMock()
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda self: 100
        mock_doc.__enter__ = lambda self: self
        mock_doc.__exit__ = MagicMock(return_value=False)
        mock_fitz.open.return_value = mock_doc

        # -- Act --
        # Patch fitz in sys.modules so that `import fitz` inside the
        # function body resolves to our mock.
        with patch.dict("sys.modules", {"fitz": mock_fitz}):
            result = _load_cached_extraction(cfg)

        # -- Assert --
        assert result is not None, (
            "_load_cached_extraction should return an ExtractionResult "
            "when the cache file exists and has >500 chars"
        )
        assert isinstance(result, ExtractionResult)
        assert result.text == body_text, (
            "Returned text must be the body after stripping the metadata header"
        )
        assert result.num_pages == 100, "num_pages should come from fitz doc length"
        assert result.total_chars == 800
        assert result.extraction_method == "docling"
        assert result.is_digital_pdf is True

    def test_load_cached_extraction_missing(self, tmp_path):
        """When extracted_text.md does not exist, return None immediately."""
        cfg = _make_settings(tmp_path)

        # Make sure the cache file does NOT exist
        cache_path = cfg.output_dir / "extracted_text.md"
        assert not cache_path.exists(), "Pre-condition: cache file must not exist"

        result = _load_cached_extraction(cfg)

        assert result is None, (
            "_load_cached_extraction must return None when there is no cache file"
        )


# ---------------------------------------------------------------------------
# Test 3: Chapter-level JSON cache skips LLM analysis
# ---------------------------------------------------------------------------

class TestChapterCacheSkipsLLM:
    """When per_chapter/chapter_NN_theses.json files already exist on disk,
    the pipeline should load them instead of calling ThesisAnalyzer.analyze_chunk."""

    @patch("src.pipeline.OutputWriter")
    @patch("src.pipeline.ThesisAnalyzer")
    @patch("src.pipeline.HierarchicalChunker")
    @patch("src.pipeline._load_cached_extraction")
    def test_pipeline_cache_chapters(
        self,
        mock_load_cache,
        mock_chunker_cls,
        mock_analyzer_cls,
        mock_writer_cls,
        tmp_path,
    ):
        """Pre-populate per_chapter JSON caches for two chunks and confirm
        that ThesisAnalyzer.analyze_chunk is never called for them.
        """
        cfg = _make_settings(tmp_path)

        # -- Extraction (returned from cache helper mock) --
        mock_load_cache.return_value = _make_extraction()

        # -- Two chunks --
        chunk_0 = _make_chunk(index=0, title="Capitulo 1")
        chunk_1 = _make_chunk(index=1, title="Capitulo 2")

        mock_chunker = MagicMock()
        mock_chunker.chunk.return_value = [chunk_0, chunk_1]
        mock_chunker_cls.return_value = mock_chunker

        # -- Pre-populate chapter caches on disk --
        analysis_0 = _make_chapter_analysis("Capitulo 1", "Cap 1")
        analysis_1 = _make_chapter_analysis("Capitulo 2", "Cap 2")

        cache_0 = cfg.per_chapter_dir / "chapter_00_theses.json"
        cache_0.write_text(analysis_0.model_dump_json(), encoding="utf-8")

        cache_1 = cfg.per_chapter_dir / "chapter_01_theses.json"
        cache_1.write_text(analysis_1.model_dump_json(), encoding="utf-8")

        # -- ThesisAnalyzer mock (should NOT be called for analyze_chunk) --
        mock_analyzer = MagicMock()
        mock_analyzer.extract_chains.return_value = ([], "")
        mock_analyzer.correlate_citations.return_value = {}
        mock_analyzer.synthesize.return_value = ([], "Summary")
        mock_analyzer_cls.return_value = mock_analyzer

        # -- OutputWriter mock --
        mock_writer = MagicMock()
        mock_writer.save_book_analysis.return_value = {}
        mock_writer_cls.return_value = mock_writer

        # -- Act --
        result = run_pipeline(cfg)

        # -- Assert --
        assert isinstance(result, BookAnalysis)
        mock_analyzer.analyze_chunk.assert_not_called(), (
            "analyze_chunk must NOT be called when all chapters are cached"
        )
