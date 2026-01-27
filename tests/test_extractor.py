"""Tests for src.extractor.PDFExtractor.

Testing strategy:
    All five tests exercise the public ``extract()`` method of PDFExtractor
    while mocking its private extraction helpers so that no real PDF parsing,
    OCR, or filesystem access is needed.

    * ``unittest.mock.patch.object`` is used to stub the private methods
      (_extract_with_docling, _extract_with_pymupdf, _extract_with_tesseract).
    * ``Path.exists`` is patched where necessary to avoid real filesystem
      checks (except the deliberate FileNotFoundError test).

Coverage targets:
    1. FileNotFoundError when the path does not exist.
    2. Happy path -- Docling succeeds on the first try.
    3. Fallback from Docling to PyMuPDF.
    4. RuntimeError when every extractor returns None.
    5. PyMuPDF returns an insufficient result (avg_chars_per_page <= 100),
       triggering the Tesseract fallback.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.extractor import PDFExtractor
from src.models import ExtractionResult, PageText


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    text: str = "Sample extracted text.",
    num_pages: int = 10,
    total_chars: int = 5000,
    avg_chars_per_page: float = 500.0,
    extraction_method: str = "docling",
    is_digital_pdf: bool = True,
) -> ExtractionResult:
    """Build a valid ExtractionResult with sensible defaults."""
    return ExtractionResult(
        text=text,
        pages=[],
        num_pages=num_pages,
        total_chars=total_chars,
        avg_chars_per_page=avg_chars_per_page,
        extraction_method=extraction_method,
        is_digital_pdf=is_digital_pdf,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPDFExtractor:
    """Unit tests for PDFExtractor.extract using mocked private methods."""

    def test_extract_file_not_found(self) -> None:
        """Calling extract() with a path that does not exist must raise
        FileNotFoundError.  No private extractors should be invoked."""
        extractor = PDFExtractor()

        with pytest.raises(FileNotFoundError, match="PDF not found"):
            extractor.extract("/nonexistent/file.pdf")

    def test_extract_docling_success(self) -> None:
        """When Docling returns a valid ExtractionResult with total_chars > 500,
        extract() should return that result immediately without falling through
        to PyMuPDF or Tesseract."""
        extractor = PDFExtractor()
        docling_result = _make_result(
            text="A" * 1000,
            num_pages=5,
            total_chars=1000,
            avg_chars_per_page=200.0,
            extraction_method="docling",
            is_digital_pdf=True,
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                PDFExtractor,
                "_extract_with_docling",
                return_value=docling_result,
            ) as mock_docling,
            patch.object(
                PDFExtractor, "_extract_with_pymupdf"
            ) as mock_pymupdf,
            patch.object(
                PDFExtractor, "_extract_with_tesseract"
            ) as mock_tesseract,
        ):
            result = extractor.extract("/fake/book.pdf")

        assert result is docling_result
        assert result.extraction_method == "docling"
        assert result.total_chars == 1000
        assert result.num_pages == 5
        mock_docling.assert_called_once()
        mock_pymupdf.assert_not_called()
        mock_tesseract.assert_not_called()

    def test_extract_docling_fallback_pymupdf(self) -> None:
        """When Docling returns None, extract() should fall back to PyMuPDF.
        If PyMuPDF returns a result with avg_chars_per_page > 100, that result
        is returned and Tesseract is never called."""
        extractor = PDFExtractor()
        pymupdf_result = _make_result(
            text="B" * 3000,
            num_pages=10,
            total_chars=3000,
            avg_chars_per_page=300.0,
            extraction_method="pymupdf",
            is_digital_pdf=True,
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                PDFExtractor,
                "_extract_with_docling",
                return_value=None,
            ) as mock_docling,
            patch.object(
                PDFExtractor,
                "_extract_with_pymupdf",
                return_value=pymupdf_result,
            ) as mock_pymupdf,
            patch.object(
                PDFExtractor, "_extract_with_tesseract"
            ) as mock_tesseract,
        ):
            result = extractor.extract("/fake/book.pdf")

        assert result is pymupdf_result
        assert result.extraction_method == "pymupdf"
        assert result.avg_chars_per_page == 300.0
        mock_docling.assert_called_once()
        mock_pymupdf.assert_called_once()
        mock_tesseract.assert_not_called()

    def test_extract_all_fail(self) -> None:
        """When all three extraction strategies return None, extract() must
        raise a RuntimeError indicating total failure."""
        extractor = PDFExtractor()

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                PDFExtractor, "_extract_with_docling", return_value=None
            ),
            patch.object(
                PDFExtractor, "_extract_with_pymupdf", return_value=None
            ),
            patch.object(
                PDFExtractor, "_extract_with_tesseract", return_value=None
            ),
        ):
            with pytest.raises(
                RuntimeError, match="All extraction methods failed"
            ):
                extractor.extract("/fake/book.pdf")

    def test_extract_pymupdf_insufficient_fallback_tesseract(self) -> None:
        """When Docling returns None and PyMuPDF returns a result with
        avg_chars_per_page <= 100 (insufficient digital text), extract()
        should fall through to Tesseract.  If Tesseract succeeds, its result
        is returned."""
        extractor = PDFExtractor()

        # PyMuPDF returns an insufficient result (scanned PDF, very low text)
        insufficient_pymupdf = _make_result(
            text="C" * 100,
            num_pages=2,
            total_chars=100,
            avg_chars_per_page=50.0,
            extraction_method="pymupdf",
            is_digital_pdf=False,
        )
        tesseract_result = _make_result(
            text="D" * 4000,
            num_pages=2,
            total_chars=4000,
            avg_chars_per_page=2000.0,
            extraction_method="tesseract",
            is_digital_pdf=False,
        )

        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(
                PDFExtractor,
                "_extract_with_docling",
                return_value=None,
            ) as mock_docling,
            patch.object(
                PDFExtractor,
                "_extract_with_pymupdf",
                return_value=insufficient_pymupdf,
            ) as mock_pymupdf,
            patch.object(
                PDFExtractor,
                "_extract_with_tesseract",
                return_value=tesseract_result,
            ) as mock_tesseract,
        ):
            result = extractor.extract("/fake/book.pdf")

        assert result is tesseract_result
        assert result.extraction_method == "tesseract"
        assert result.avg_chars_per_page == 2000.0
        mock_docling.assert_called_once()
        mock_pymupdf.assert_called_once()
        mock_tesseract.assert_called_once()
