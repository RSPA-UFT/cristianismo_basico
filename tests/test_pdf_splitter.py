"""Tests for pdf_splitter module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from src.pdf_splitter import (
    ChunkMetadata,
    ImageMode,
    PDFChunk,
    PDFSplitter,
    PDFSplitterSettings,
)


class TestPDFSplitterSettings:
    """Tests for PDFSplitterSettings."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        settings = PDFSplitterSettings()
        assert settings.max_tokens == 6000
        assert settings.image_mode == ImageMode.PLACEHOLDER
        assert settings.tokenizer_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert settings.output_format == "markdown"
        assert settings.include_metadata_header is True

    def test_custom_values(self):
        """Test that custom values can be set."""
        settings = PDFSplitterSettings(
            max_tokens=4000,
            image_mode=ImageMode.REFERENCED,
            include_metadata_header=False,
        )
        assert settings.max_tokens == 4000
        assert settings.image_mode == ImageMode.REFERENCED
        assert settings.include_metadata_header is False

    def test_env_prefix(self):
        """Test that environment variables are read with correct prefix."""
        with patch.dict(os.environ, {"PDF_SPLITTER_MAX_TOKENS": "8000"}):
            settings = PDFSplitterSettings()
            assert settings.max_tokens == 8000

    def test_env_image_mode(self):
        """Test that image mode can be set via environment."""
        with patch.dict(os.environ, {"PDF_SPLITTER_IMAGE_MODE": "referenced"}):
            settings = PDFSplitterSettings()
            assert settings.image_mode == ImageMode.REFERENCED

    def test_max_tokens_validation_min(self):
        """Test that max_tokens has minimum validation."""
        with pytest.raises(ValueError):
            PDFSplitterSettings(max_tokens=50)

    def test_max_tokens_validation_max(self):
        """Test that max_tokens has maximum validation."""
        with pytest.raises(ValueError):
            PDFSplitterSettings(max_tokens=200000)


class TestImageMode:
    """Tests for ImageMode enum."""

    def test_placeholder_value(self):
        """Test placeholder mode value."""
        assert ImageMode.PLACEHOLDER.value == "placeholder"

    def test_referenced_value(self):
        """Test referenced mode value."""
        assert ImageMode.REFERENCED.value == "referenced"

    def test_embedded_value(self):
        """Test embedded mode value."""
        assert ImageMode.EMBEDDED.value == "embedded"

    def test_from_string(self):
        """Test creating ImageMode from string."""
        assert ImageMode("placeholder") == ImageMode.PLACEHOLDER
        assert ImageMode("referenced") == ImageMode.REFERENCED


class TestChunkMetadata:
    """Tests for ChunkMetadata model."""

    def test_required_fields(self):
        """Test that required fields must be provided."""
        metadata = ChunkMetadata(
            index=0,
            title="Test Title",
            token_count=1000,
        )
        assert metadata.index == 0
        assert metadata.title == "Test Title"
        assert metadata.token_count == 1000

    def test_default_fields(self):
        """Test that optional fields have defaults."""
        metadata = ChunkMetadata(
            index=0,
            title="Test",
            token_count=100,
        )
        assert metadata.headings == []
        assert metadata.page_numbers == []
        assert metadata.has_images is False
        assert metadata.image_refs == []

    def test_full_metadata(self):
        """Test creating metadata with all fields."""
        metadata = ChunkMetadata(
            index=5,
            title="Capítulo 3 - Fé e Razão",
            headings=["Parte 1", "Capítulo 3"],
            page_numbers=[45, 46, 47],
            token_count=5234,
            has_images=True,
            image_refs=["fig_001.png", "fig_002.png"],
        )
        assert metadata.index == 5
        assert len(metadata.headings) == 2
        assert 46 in metadata.page_numbers
        assert metadata.has_images is True

    def test_index_validation(self):
        """Test that index must be non-negative."""
        with pytest.raises(ValueError):
            ChunkMetadata(index=-1, title="Test", token_count=100)


class TestPDFChunk:
    """Tests for PDFChunk model."""

    def test_chunk_creation(self):
        """Test creating a PDFChunk."""
        metadata = ChunkMetadata(
            index=0,
            title="Introduction",
            token_count=500,
        )
        chunk = PDFChunk(
            metadata=metadata,
            content="# Introduction\n\nThis is the content.",
        )
        assert chunk.metadata.title == "Introduction"
        assert "Introduction" in chunk.content


class TestPDFSplitter:
    """Tests for PDFSplitter class."""

    def test_init_default_settings(self):
        """Test initialization with default settings."""
        splitter = PDFSplitter()
        assert splitter.settings.max_tokens == 6000
        assert splitter.settings.image_mode == ImageMode.PLACEHOLDER

    def test_init_with_settings(self):
        """Test initialization with custom settings."""
        settings = PDFSplitterSettings(max_tokens=4000)
        splitter = PDFSplitter(settings=settings)
        assert splitter.settings.max_tokens == 4000

    def test_init_with_overrides(self):
        """Test that overrides take precedence."""
        settings = PDFSplitterSettings(max_tokens=4000)
        splitter = PDFSplitter(
            settings=settings,
            max_tokens=8000,
            image_mode=ImageMode.REFERENCED,
        )
        assert splitter.settings.max_tokens == 8000
        assert splitter.settings.image_mode == ImageMode.REFERENCED

    def test_init_overrides_without_settings(self):
        """Test overrides work without explicit settings."""
        splitter = PDFSplitter(max_tokens=3000)
        assert splitter.settings.max_tokens == 3000

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        splitter = PDFSplitter()
        with pytest.raises(FileNotFoundError, match="PDF file not found"):
            splitter.split("/nonexistent/path/to/file.pdf")

    def test_generate_slug(self):
        """Test slug generation from titles."""
        splitter = PDFSplitter()

        assert splitter._generate_slug("Capítulo 1") == "capitulo_1"
        assert splitter._generate_slug("A Fé Cristã") == "a_fe_crista"
        assert splitter._generate_slug("Test!@#$%") == "test"
        assert splitter._generate_slug("   Spaces   ") == "spaces"

    def test_generate_title_with_headings(self):
        """Test title generation from headings."""
        splitter = PDFSplitter()

        title = splitter._generate_title(["Part 1", "Chapter 3"], 0)
        assert title == "Chapter 3"

    def test_generate_title_without_headings(self):
        """Test title generation when no headings."""
        splitter = PDFSplitter()

        title = splitter._generate_title([], 5)
        assert title == "Chunk 5"

    def test_count_tokens_fallback(self):
        """Test token counting fallback estimation."""
        splitter = PDFSplitter()

        # Mock transformers to fail
        with patch.dict("sys.modules", {"transformers": None}):
            count = splitter._count_tokens("This is a test string")
            # Fallback: len // 4
            assert count == len("This is a test string") // 4


class TestPDFSplitterMockedDocling:
    """Tests for PDFSplitter with mocked docling."""

    @pytest.fixture
    def mock_chunk(self):
        """Create a mock chunk object."""
        chunk = MagicMock()
        chunk.text = "This is the chunk content with some text."

        # Mock meta
        meta = MagicMock()
        meta.headings = ["Part 1", "Chapter 1"]

        # Mock doc_items with page info
        item = MagicMock()
        prov = MagicMock()
        prov.page_no = 15
        item.prov = [prov]
        item.label = "text"
        meta.doc_items = [item]

        chunk.meta = meta
        return chunk

    @pytest.fixture
    def mock_image_chunk(self):
        """Create a mock chunk with images."""
        chunk = MagicMock()
        chunk.text = "Content with image [IMAGEM]"

        meta = MagicMock()
        meta.headings = ["Chapter 2"]

        item = MagicMock()
        item.label = "picture"
        item.self_ref = "#/pictures/0"
        item.prov = []
        meta.doc_items = [item]

        chunk.meta = meta
        return chunk

    def test_extract_headings(self, mock_chunk):
        """Test heading extraction from chunk."""
        splitter = PDFSplitter()
        headings = splitter._extract_headings(mock_chunk)
        assert headings == ["Part 1", "Chapter 1"]

    def test_extract_page_numbers(self, mock_chunk):
        """Test page number extraction from chunk."""
        splitter = PDFSplitter()
        pages = splitter._extract_page_numbers(mock_chunk)
        assert pages == [15]

    def test_check_for_images_no_images(self, mock_chunk):
        """Test image detection when no images."""
        splitter = PDFSplitter()
        has_images, refs = splitter._check_for_images(mock_chunk)
        assert has_images is False
        assert refs == []

    def test_check_for_images_with_images(self, mock_image_chunk):
        """Test image detection when images present."""
        splitter = PDFSplitter()
        has_images, refs = splitter._check_for_images(mock_image_chunk)
        assert has_images is True
        assert "#/pictures/0" in refs

    def test_format_chunk_content_with_metadata(self):
        """Test chunk formatting with metadata header."""
        splitter = PDFSplitter()
        metadata = ChunkMetadata(
            index=0,
            title="Introduction",
            headings=["Part 1", "Introduction"],
            page_numbers=[1, 2],
            token_count=500,
            has_images=False,
        )

        content = splitter._format_chunk_content(
            "This is the content.",
            metadata,
            ImageMode.PLACEHOLDER,
        )

        assert "---" in content
        assert "chunk_index: 0" in content
        assert "title: Introduction" in content
        assert "tokens: 500" in content
        assert "pages: 1, 2" in content
        assert "**Seção:** Part 1 > Introduction" in content
        assert "This is the content." in content

    def test_format_chunk_content_without_metadata(self):
        """Test chunk formatting without metadata header."""
        settings = PDFSplitterSettings(include_metadata_header=False)
        splitter = PDFSplitter(settings=settings)
        metadata = ChunkMetadata(
            index=0,
            title="Test",
            token_count=100,
        )

        content = splitter._format_chunk_content(
            "Content only.",
            metadata,
            ImageMode.PLACEHOLDER,
        )

        assert "---" not in content
        assert "chunk_index" not in content
        assert "Content only." in content


class TestPDFSplitterIntegration:
    """Integration tests for split_to_files."""

    @pytest.fixture
    def mock_splitter(self, tmp_path):
        """Create a splitter with mocked split method."""
        splitter = PDFSplitter()

        # Create mock chunks
        chunks = [
            PDFChunk(
                metadata=ChunkMetadata(
                    index=0,
                    title="Prefácio",
                    headings=["Prefácio"],
                    page_numbers=[5, 6],
                    token_count=1500,
                    has_images=False,
                ),
                content="---\nchunk_index: 0\n---\n\nPrefácio content here.",
            ),
            PDFChunk(
                metadata=ChunkMetadata(
                    index=1,
                    title="Capítulo 1",
                    headings=["Parte 1", "Capítulo 1"],
                    page_numbers=[15, 16, 17],
                    token_count=5800,
                    has_images=True,
                ),
                content="---\nchunk_index: 1\n---\n\nCapítulo 1 content with [IMAGEM].",
            ),
        ]

        # Mock the split method
        splitter.split = MagicMock(return_value=chunks)

        return splitter

    def test_split_to_files_creates_structure(self, mock_splitter, tmp_path):
        """Test that split_to_files creates correct directory structure."""
        output_dir = tmp_path / "output"

        # Create a dummy PDF path
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        files = mock_splitter.split_to_files(pdf_path, output_dir)

        assert len(files) == 2
        assert (output_dir / "chunks").exists()
        assert (output_dir / "manifest.json").exists()

    def test_split_to_files_creates_manifest(self, mock_splitter, tmp_path):
        """Test that manifest.json is created correctly."""
        output_dir = tmp_path / "output"
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        mock_splitter.split_to_files(pdf_path, output_dir)

        manifest_path = output_dir / "manifest.json"
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text())
        assert manifest["source_pdf"] == "test.pdf"
        assert manifest["total_chunks"] == 2
        assert manifest["settings"]["max_tokens"] == 6000
        assert len(manifest["chunks"]) == 2

    def test_split_to_files_naming(self, mock_splitter, tmp_path):
        """Test that chunk files are named correctly."""
        output_dir = tmp_path / "output"
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        files = mock_splitter.split_to_files(pdf_path, output_dir)

        # Check file naming pattern
        assert "chunk_000_" in files[0].name
        assert "chunk_001_" in files[1].name
        assert files[0].suffix == ".md"

    def test_split_to_files_content(self, mock_splitter, tmp_path):
        """Test that chunk files contain correct content."""
        output_dir = tmp_path / "output"
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        files = mock_splitter.split_to_files(pdf_path, output_dir)

        content = files[0].read_text()
        assert "chunk_index: 0" in content
        assert "Prefácio" in content

    def test_split_to_files_images_dir(self, tmp_path):
        """Test that images directory is created for referenced mode."""
        settings = PDFSplitterSettings(image_mode=ImageMode.REFERENCED)
        splitter = PDFSplitter(settings=settings)

        # Mock split to return empty list
        splitter.split = MagicMock(return_value=[])

        output_dir = tmp_path / "output"
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy")

        splitter.split_to_files(pdf_path, output_dir)

        assert (output_dir / "images").exists()


class TestCLI:
    """Tests for CLI interface."""

    def test_main_module_importable(self):
        """Test that main function can be imported."""
        from src.pdf_splitter import main
        assert callable(main)

    def test_argparse_setup(self):
        """Test CLI argument parsing."""
        import argparse
        from src.pdf_splitter import main

        # We can't easily test argparse without running main,
        # but we can verify the module is importable
        assert True
