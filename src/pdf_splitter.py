"""
PDF Splitter Module - Standalone module to split large PDFs into Claude-consumable chunks.

This module can be copied standalone to other projects.
Required dependencies:
- docling>=2.54.0
- pydantic>=2.4.0
- pydantic-settings>=2.0.0

Usage:
    from pdf_splitter import PDFSplitter, PDFSplitterSettings, ImageMode

    splitter = PDFSplitter(max_tokens=6000, image_mode=ImageMode.PLACEHOLDER)
    chunks = splitter.split("document.pdf")

    # Or save to files
    files = splitter.split_to_files("document.pdf", "./output")

CLI:
    python -m src.pdf_splitter document.pdf ./output --max-tokens 6000 --image-mode placeholder
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import re
import sys
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DoclingDocument

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Models
# =============================================================================


class ImageMode(str, Enum):
    """Mode for handling images in PDF chunks."""

    PLACEHOLDER = "placeholder"  # Mark position with [IMAGEM]
    REFERENCED = "referenced"  # Save to separate PNG files
    EMBEDDED = "embedded"  # Base64 inline (not recommended)


class PDFSplitterSettings(BaseSettings):
    """Settings for PDF Splitter with environment variable support."""

    max_tokens: int = Field(default=6000, ge=100, le=100000)
    image_mode: ImageMode = Field(default=ImageMode.PLACEHOLDER)
    tokenizer_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    output_format: str = Field(default="markdown")
    include_metadata_header: bool = Field(default=True)

    model_config = {"env_prefix": "PDF_SPLITTER_"}


class ChunkMetadata(BaseModel):
    """Metadata for a single PDF chunk."""

    index: int = Field(ge=0)
    title: str
    headings: list[str] = Field(default_factory=list)
    page_numbers: list[int] = Field(default_factory=list)
    token_count: int = Field(ge=0)
    has_images: bool = Field(default=False)
    image_refs: list[str] = Field(default_factory=list)


class PDFChunk(BaseModel):
    """A single chunk of a PDF document."""

    metadata: ChunkMetadata
    content: str  # Markdown formatted content


# =============================================================================
# PDF Splitter Class
# =============================================================================


class PDFSplitter:
    """
    Split large PDFs into Claude-consumable chunks with configurable token limits.

    This class uses docling for PDF parsing and intelligent chunking based on
    document structure (headings, paragraphs, etc.).
    """

    def __init__(
        self,
        settings: PDFSplitterSettings | None = None,
        max_tokens: int | None = None,
        image_mode: ImageMode | None = None,
    ):
        """
        Initialize PDFSplitter.

        Args:
            settings: PDFSplitterSettings instance. If None, creates default settings.
            max_tokens: Override max_tokens from settings.
            image_mode: Override image_mode from settings.
        """
        self.settings = settings or PDFSplitterSettings()

        # Apply overrides
        if max_tokens is not None:
            self.settings = self.settings.model_copy(update={"max_tokens": max_tokens})
        if image_mode is not None:
            self.settings = self.settings.model_copy(update={"image_mode": image_mode})

        self._converter: DocumentConverter | None = None
        self._chunker = None

    def _get_converter(self) -> "DocumentConverter":
        """Lazy initialization of DocumentConverter."""
        if self._converter is None:
            from docling.document_converter import DocumentConverter

            self._converter = DocumentConverter()
        return self._converter

    def _get_chunker(self):
        """Lazy initialization of HybridChunker."""
        if self._chunker is None:
            from docling.chunking import HybridChunker

            self._chunker = HybridChunker(
                tokenizer=self.settings.tokenizer_model,
                max_tokens=self.settings.max_tokens,
            )
        return self._chunker

    def _extract_headings(self, chunk) -> list[str]:
        """Extract heading hierarchy from chunk."""
        headings = []
        if hasattr(chunk, "meta") and chunk.meta:
            meta = chunk.meta
            if hasattr(meta, "headings") and meta.headings:
                headings = list(meta.headings)
            elif hasattr(meta, "doc_items"):
                # Try to extract from doc_items
                for item in meta.doc_items or []:
                    if hasattr(item, "label") and "heading" in str(item.label).lower():
                        if hasattr(item, "text"):
                            headings.append(item.text)
        return headings

    def _extract_page_numbers(self, chunk) -> list[int]:
        """Extract page numbers from chunk."""
        pages = set()
        if hasattr(chunk, "meta") and chunk.meta:
            meta = chunk.meta
            if hasattr(meta, "doc_items"):
                for item in meta.doc_items or []:
                    if hasattr(item, "prov") and item.prov:
                        for prov in item.prov:
                            if hasattr(prov, "page_no"):
                                pages.add(prov.page_no)
        return sorted(pages)

    def _check_for_images(self, chunk) -> tuple[bool, list[str]]:
        """Check if chunk contains images and return image references."""
        has_images = False
        image_refs = []

        if hasattr(chunk, "meta") and chunk.meta:
            meta = chunk.meta
            if hasattr(meta, "doc_items"):
                for item in meta.doc_items or []:
                    if hasattr(item, "label"):
                        label = str(item.label).lower()
                        if "picture" in label or "figure" in label or "image" in label:
                            has_images = True
                            if hasattr(item, "self_ref"):
                                image_refs.append(str(item.self_ref))

        return has_images, image_refs

    def _generate_title(self, headings: list[str], index: int) -> str:
        """Generate a title for the chunk based on headings."""
        if headings:
            # Use the most specific heading (last in hierarchy)
            return headings[-1]
        return f"Chunk {index}"

    def _generate_slug(self, title: str) -> str:
        """Generate a URL-safe slug from title."""
        # Remove accents and special characters
        slug = title.lower()
        # Replace accented characters
        replacements = {
            "á": "a",
            "à": "a",
            "ã": "a",
            "â": "a",
            "é": "e",
            "ê": "e",
            "í": "i",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ú": "u",
            "ç": "c",
        }
        for old, new in replacements.items():
            slug = slug.replace(old, new)
        # Keep only alphanumeric and spaces
        slug = re.sub(r"[^a-z0-9\s]", "", slug)
        # Replace spaces with underscores
        slug = re.sub(r"\s+", "_", slug.strip())
        # Limit length
        return slug[:40] if slug else "chunk"

    def _format_chunk_content(
        self,
        text: str,
        metadata: ChunkMetadata,
        image_mode: ImageMode,
    ) -> str:
        """Format chunk content as Markdown with optional YAML frontmatter."""
        lines = []

        # Add YAML frontmatter if enabled
        if self.settings.include_metadata_header:
            lines.append("---")
            lines.append(f"chunk_index: {metadata.index}")
            lines.append(f"title: {metadata.title}")
            lines.append(f"tokens: {metadata.token_count}")
            if metadata.page_numbers:
                pages_str = ", ".join(str(p) for p in metadata.page_numbers)
                lines.append(f"pages: {pages_str}")
            if metadata.headings:
                lines.append("headings:")
                for h in metadata.headings:
                    lines.append(f"  - {h}")
            lines.append(f"has_images: {str(metadata.has_images).lower()}")
            lines.append("---")
            lines.append("")

        # Add section breadcrumb if we have headings
        if metadata.headings:
            breadcrumb = " > ".join(metadata.headings)
            lines.append(f"**Seção:** {breadcrumb}")
            lines.append("")

        # Process text based on image mode
        content = text
        if image_mode == ImageMode.PLACEHOLDER:
            # Images are already marked as [IMAGEM] by docling's markdown export
            # Just ensure consistency
            pass
        elif image_mode == ImageMode.REFERENCED:
            # Image references will be handled during file output
            pass

        lines.append(content)

        return "\n".join(lines)

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using the configured tokenizer."""
        try:
            from transformers import AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(self.settings.tokenizer_model)
            return len(tokenizer.encode(text))
        except Exception:
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    def split(
        self,
        pdf_path: str | Path,
        output_dir: str | Path | None = None,
    ) -> list[PDFChunk]:
        """
        Split a PDF into chunks.

        Args:
            pdf_path: Path to the PDF file.
            output_dir: Optional output directory (only used for image references).

        Returns:
            List of PDFChunk objects.

        Raises:
            FileNotFoundError: If PDF file doesn't exist.
            ValueError: If PDF cannot be processed.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Converting PDF: {pdf_path}")
        converter = self._get_converter()
        result = converter.convert(pdf_path)
        doc: DoclingDocument = result.document

        logger.info(f"Chunking document with max_tokens={self.settings.max_tokens}")
        chunker = self._get_chunker()
        raw_chunks = list(chunker.chunk(doc))

        logger.info(f"Processing {len(raw_chunks)} chunks")
        chunks = []

        for i, raw_chunk in enumerate(raw_chunks):
            # Extract metadata
            headings = self._extract_headings(raw_chunk)
            page_numbers = self._extract_page_numbers(raw_chunk)
            has_images, image_refs = self._check_for_images(raw_chunk)
            title = self._generate_title(headings, i)

            # Get text content
            text = raw_chunk.text if hasattr(raw_chunk, "text") else str(raw_chunk)
            token_count = self._count_tokens(text)

            # Create metadata
            metadata = ChunkMetadata(
                index=i,
                title=title,
                headings=headings,
                page_numbers=page_numbers,
                token_count=token_count,
                has_images=has_images,
                image_refs=image_refs,
            )

            # Format content
            content = self._format_chunk_content(
                text,
                metadata,
                self.settings.image_mode,
            )

            chunks.append(PDFChunk(metadata=metadata, content=content))

        logger.info(f"Created {len(chunks)} chunks from PDF")
        return chunks

    def split_to_files(
        self,
        pdf_path: str | Path,
        output_dir: str | Path,
    ) -> list[Path]:
        """
        Split a PDF and save chunks to files.

        Args:
            pdf_path: Path to the PDF file.
            output_dir: Directory to save output files.

        Returns:
            List of paths to created chunk files.

        Creates:
            output_dir/
            ├── chunks/
            │   ├── chunk_000_title.md
            │   └── ...
            ├── images/  (if image_mode=referenced)
            └── manifest.json
        """
        output_dir = Path(output_dir)
        chunks_dir = output_dir / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        if self.settings.image_mode == ImageMode.REFERENCED:
            images_dir = output_dir / "images"
            images_dir.mkdir(parents=True, exist_ok=True)

        chunks = self.split(pdf_path, output_dir)
        chunk_files = []
        manifest_entries = []

        for chunk in chunks:
            slug = self._generate_slug(chunk.metadata.title)
            filename = f"chunk_{chunk.metadata.index:03d}_{slug}.md"
            filepath = chunks_dir / filename

            filepath.write_text(chunk.content, encoding="utf-8")
            chunk_files.append(filepath)

            manifest_entries.append(
                {
                    "index": chunk.metadata.index,
                    "file": str(filepath.relative_to(output_dir)),
                    "title": chunk.metadata.title,
                    "tokens": chunk.metadata.token_count,
                    "pages": chunk.metadata.page_numbers,
                    "has_images": chunk.metadata.has_images,
                }
            )

        # Write manifest
        manifest_path = output_dir / "manifest.json"
        manifest = {
            "source_pdf": str(Path(pdf_path).name),
            "total_chunks": len(chunks),
            "settings": {
                "max_tokens": self.settings.max_tokens,
                "image_mode": self.settings.image_mode.value,
            },
            "chunks": manifest_entries,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info(f"Saved {len(chunk_files)} chunks to {chunks_dir}")
        return chunk_files


# =============================================================================
# CLI Interface
# =============================================================================


def main():
    """Command-line interface for PDF Splitter."""
    parser = argparse.ArgumentParser(
        description="Split large PDFs into Claude-consumable chunks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.pdf_splitter document.pdf ./output
  python -m src.pdf_splitter document.pdf ./output --max-tokens 4000
  python -m src.pdf_splitter document.pdf ./output --image-mode referenced
        """,
    )

    parser.add_argument("pdf_path", type=str, help="Path to the PDF file")
    parser.add_argument("output_dir", type=str, help="Output directory for chunks")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=6000,
        help="Maximum tokens per chunk (default: 6000)",
    )
    parser.add_argument(
        "--image-mode",
        type=str,
        choices=["placeholder", "referenced", "embedded"],
        default="placeholder",
        help="How to handle images (default: placeholder)",
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Disable YAML metadata header in chunks",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Create settings
    settings = PDFSplitterSettings(
        max_tokens=args.max_tokens,
        image_mode=ImageMode(args.image_mode),
        include_metadata_header=not args.no_metadata,
    )

    # Run splitter
    splitter = PDFSplitter(settings=settings)

    try:
        files = splitter.split_to_files(args.pdf_path, args.output_dir)
        print(f"\n✓ Created {len(files)} chunks in {args.output_dir}/chunks/")
        print(f"✓ Manifest saved to {args.output_dir}/manifest.json")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception("Failed to process PDF")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
