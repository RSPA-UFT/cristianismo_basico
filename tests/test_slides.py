"""Tests for src.slides -- Reveal.js slide generation.

Covers:
- generate_slides: file creation and HTML structure
- Slide content: title, summary, stats, parts, methodology
"""

import json
from pathlib import Path

import pytest

from src.models import BookAnalysis, Citation, Thesis, ThesisChain
from src.slides import generate_slides


class TestGenerateSlides:
    """Tests for the generate_slides function."""

    def test_creates_file(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Should create apresentacao.html in the output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)

        assert path.exists(), "apresentacao.html should be created"
        assert path.name == "apresentacao.html"

    def test_html_structure(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Generated HTML should contain Reveal.js structure."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "reveal.js" in content, "Should reference Reveal.js CDN"
        assert "class=\"reveal\"" in content, "Should have reveal container"
        assert "class=\"slides\"" in content, "Should have slides container"
        assert "<section>" in content or "<section " in content, "Should have slide sections"

    def test_contains_title_slide(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Should contain the title slide with book info."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "Cristianismo Basico" in content
        assert "John Stott" in content

    def test_contains_stats(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Should contain statistics section."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "Visao Geral" in content
        assert str(len(sample_book_analysis.theses)) in content

    def test_loads_from_files(self, tmp_path: Path):
        """Should load analysis from JSON files when not provided directly."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Write minimal JSON files
        theses = [
            Thesis(id="T1.1.1", title="Test", description="Desc", chapter="Cap 1", part="Parte 1 - A Pessoa de Cristo").model_dump(mode="json"),
        ]
        (output_dir / "theses.json").write_text(
            json.dumps(theses, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / "chains.json").write_text("[]", encoding="utf-8")
        (output_dir / "citations.json").write_text("[]", encoding="utf-8")

        path = generate_slides(output_dir)

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Cristianismo Basico" in content
