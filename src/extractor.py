"""PDF text extraction with 3-tier strategy: Docling -> PyMuPDF -> Tesseract."""

import logging
from pathlib import Path

from .models import ExtractionResult, PageText

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text from PDF using a 3-tier fallback strategy."""

    def __init__(self) -> None:
        self._docling_converter = None

    def extract(self, pdf_path: str | Path) -> ExtractionResult:
        pdf_path = Path(pdf_path).resolve()
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Extracting text from: {pdf_path.name}")

        # Tier 1: Try Docling (produces structured Markdown)
        result = self._extract_with_docling(pdf_path)
        if result and result.total_chars > 500:
            logger.info(
                f"Docling extraction successful: {result.num_pages} pages, "
                f"{result.avg_chars_per_page:.0f} avg chars/page"
            )
            return result

        # Tier 2: Try PyMuPDF (fast, for digital PDFs)
        logger.info("Docling failed or insufficient text, trying PyMuPDF...")
        result = self._extract_with_pymupdf(pdf_path)
        if result and result.avg_chars_per_page > 100:
            logger.info(
                f"PyMuPDF extraction successful: {result.num_pages} pages, "
                f"{result.avg_chars_per_page:.0f} avg chars/page"
            )
            return result

        # Tier 3: Tesseract OCR (last resort)
        logger.info("PyMuPDF insufficient, trying Tesseract OCR...")
        result = self._extract_with_tesseract(pdf_path)
        if result:
            logger.info(
                f"Tesseract extraction: {result.num_pages} pages, "
                f"{result.avg_chars_per_page:.0f} avg chars/page"
            )
            return result

        raise RuntimeError(f"All extraction methods failed for {pdf_path}")

    def _extract_with_docling(self, pdf_path: Path) -> ExtractionResult | None:
        try:
            from docling.document_converter import DocumentConverter

            logger.info("Initializing Docling converter...")
            converter = DocumentConverter()
            doc_result = converter.convert(str(pdf_path))
            markdown_text = doc_result.document.export_to_markdown()

            if not markdown_text or len(markdown_text.strip()) < 100:
                return None

            # Docling doesn't give per-page text easily in markdown mode,
            # so we estimate page count from PyMuPDF
            num_pages = self._count_pages_pymupdf(pdf_path)
            total_chars = len(markdown_text)

            return ExtractionResult(
                text=markdown_text,
                num_pages=num_pages,
                total_chars=total_chars,
                avg_chars_per_page=total_chars / max(num_pages, 1),
                extraction_method="docling",
                is_digital_pdf=True,
            )
        except Exception as e:
            logger.warning(f"Docling extraction failed: {e}")
            return None

    def _extract_with_pymupdf(self, pdf_path: Path) -> ExtractionResult | None:
        try:
            import fitz  # PyMuPDF

            pages: list[PageText] = []
            total_chars = 0

            with fitz.open(str(pdf_path)) as doc:
                num_pages = len(doc)
                for i, page in enumerate(doc):
                    text = page.get_text()
                    pages.append(PageText(page_number=i + 1, text=text))
                    total_chars += len(text.strip())

            full_text = "\n\n".join(
                f"--- Pagina {p.page_number} ---\n{p.text}" for p in pages
            )
            avg = total_chars / max(num_pages, 1)

            return ExtractionResult(
                text=full_text,
                pages=pages,
                num_pages=num_pages,
                total_chars=total_chars,
                avg_chars_per_page=avg,
                extraction_method="pymupdf",
                is_digital_pdf=avg > 100,
            )
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
            return None

    def _extract_with_tesseract(self, pdf_path: Path) -> ExtractionResult | None:
        try:
            from pdf2image import convert_from_path
            import pytesseract

            images = convert_from_path(str(pdf_path))
            pages: list[PageText] = []
            total_chars = 0

            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image, lang="por")
                pages.append(PageText(page_number=i + 1, text=text))
                total_chars += len(text.strip())

            full_text = "\n\n".join(
                f"--- Pagina {p.page_number} ---\n{p.text}" for p in pages
            )
            num_pages = len(pages)

            return ExtractionResult(
                text=full_text,
                pages=pages,
                num_pages=num_pages,
                total_chars=total_chars,
                avg_chars_per_page=total_chars / max(num_pages, 1),
                extraction_method="tesseract",
                is_digital_pdf=False,
            )
        except ImportError:
            logger.warning("Tesseract/pdf2image not installed (install with: uv pip install 'cristianismo-basico[ocr]')")
            return None
        except Exception as e:
            logger.warning(f"Tesseract extraction failed: {e}")
            return None

    def _count_pages_pymupdf(self, pdf_path: Path) -> int:
        try:
            import fitz
            with fitz.open(str(pdf_path)) as doc:
                return len(doc)
        except Exception:
            return 0
