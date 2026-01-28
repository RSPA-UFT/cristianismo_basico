"""Tests for src.pdf_report -- PDF/HTML report generation.

Covers:
- _build_html: HTML structure and content
- generate_pdf_report: file generation (HTML fallback)
- _load_analysis_from_files: loading from JSON files
"""

import json
from pathlib import Path

import pytest

from src.models import BookAnalysis, Citation, Thesis, ThesisChain
from src.pdf_report import _build_html, generate_pdf_report


class TestBuildHTML:
    """Tests for the _build_html function."""

    def test_html_contains_title(self, sample_book_analysis: BookAnalysis):
        """Generated HTML should contain the report title."""
        html = _build_html(sample_book_analysis)

        assert "Cristianismo Basico" in html
        assert "John Stott" in html

    def test_html_contains_summary(self, sample_book_analysis: BookAnalysis):
        """Generated HTML should contain the executive summary."""
        html = _build_html(sample_book_analysis)

        assert "Resumo Executivo" in html
        assert sample_book_analysis.summary[:50] in html

    def test_html_contains_statistics(self, sample_book_analysis: BookAnalysis):
        """Generated HTML should contain statistics table."""
        html = _build_html(sample_book_analysis)

        assert "Estatisticas" in html
        assert "Total de teses" in html
        assert str(len(sample_book_analysis.theses)) in html


class TestGeneratePDFReport:
    """Tests for the generate_pdf_report function."""

    def test_generates_html_fallback(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """When weasyprint is not available, should generate HTML file."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_pdf_report(output_dir, analysis=sample_book_analysis)

        assert path.exists(), "Report file should be created"
        assert path.suffix in (".html", ".pdf"), f"Unexpected suffix: {path.suffix}"

        content = path.read_text(encoding="utf-8")
        assert "Cristianismo Basico" in content

    def test_loads_from_json_files(self, tmp_path: Path):
        """Should be able to load analysis from JSON files when not provided."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Write minimal JSON files
        theses = [
            Thesis(id="T1.1.1", title="Test", description="Desc", chapter="Cap 1", part="Parte 1").model_dump(mode="json"),
        ]
        (output_dir / "theses.json").write_text(
            json.dumps(theses, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / "chains.json").write_text("[]", encoding="utf-8")
        (output_dir / "citations.json").write_text("[]", encoding="utf-8")

        path = generate_pdf_report(output_dir)

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "T1.1.1" in content

    def test_scholarly_section_present(self, tmp_path: Path, sample_book_analysis_with_scholarly: BookAnalysis):
        """Report should include scholarly citations section when present."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        html = _build_html(sample_book_analysis_with_scholarly)

        assert "Citacoes Academicas" in html
        assert "LEWIS" in html
