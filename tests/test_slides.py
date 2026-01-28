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

        assert "Cristianismo B\u00e1sico" in content
        assert "John Stott" in content

    def test_contains_stats(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Should contain statistics section."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "Vis\u00e3o Geral" in content
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
        assert "Cristianismo B\u00e1sico" in content

    def test_part_filter_uses_id_fallback(self, tmp_path: Path):
        """Theses with empty part field should still appear in part slides via ID derivation."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        analysis = BookAnalysis(
            theses=[
                Thesis(
                    id="T1.1.1",
                    title="Tese da Parte 1",
                    description="Desc",
                    thesis_type="main",
                    part="",  # empty — must be derived from ID
                ),
                Thesis(
                    id="T2.5.1",
                    title="Tese da Parte 2",
                    description="Desc",
                    thesis_type="main",
                    part="",
                ),
            ],
        )

        path = generate_slides(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        assert "Tese da Parte 1" in content, "Thesis T1.x should appear in Parte 1 slide"
        assert "Tese da Parte 2" in content, "Thesis T2.x should appear in Parte 2 slide"
        # Parts 1 and 2 should each have 1 thesis, not 0
        assert "1 teses" in content, "Parts with data should show non-zero thesis counts"

    def test_all_scholarly_shown(self, tmp_path: Path):
        """All scholarly citations should be shown, not limited to 8."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        scholarly = [
            Citation(
                reference=f"Author {i}",
                citation_type="scholarly",
                author=f"Author {i}",
                work=f"Work {i}",
            )
            for i in range(1, 18)
        ]

        analysis = BookAnalysis(citations=scholarly)
        path = generate_slides(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        for i in range(1, 18):
            assert f"Author {i}" in content, f"Author {i} should appear in scholarly slide"

    def test_part_headings_use_darkened_colors(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Part headings should use darkened text colors for WCAG contrast."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        # Darkened colors should appear in heading style attributes
        assert "#036c9a" in content, "Parte 1 heading should use darkened blue"
        assert "#b02a37" in content, "Parte 2 heading should use darkened red"
        assert "#c96209" in content, "Parte 3 heading should use darkened orange"
        assert "#1e7b34" in content, "Parte 4 heading should use darkened green"

    def test_scholarly_grid_layout(self, tmp_path: Path):
        """Scholarly citations should use 2-column grid layout."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        scholarly = [
            Citation(
                reference=f"Author {i}",
                citation_type="scholarly",
                author=f"Author {i}",
                work=f"Work {i}",
            )
            for i in range(1, 10)
        ]

        analysis = BookAnalysis(citations=scholarly)
        path = generate_slides(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        assert "scholarly-grid" in content, "Should use scholarly-grid class for 2-column layout"
        assert "grid-template-columns: 1fr 1fr" in content, "Grid should have 2 columns"

    def test_flow_slide_has_sub_sections(self, tmp_path: Path):
        """Flow slide with long text should be split into vertical sub-slides."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        analysis = BookAnalysis(
            argument_flow=(
                "First paragraph of flow text.\n\n"
                "Second paragraph with more details.\n\n"
                "Third paragraph with even more.\n\n"
                "Fourth paragraph concluding."
            ),
        )

        path = generate_slides(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        assert "Fluxo Argumentativo" in content
        assert "Fluxo Argumentativo (cont.)" in content, "Should have continuation sub-slides"

    def test_summary_truncation(self, tmp_path: Path):
        """Long summaries should be truncated."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        long_summary = "A" * 800
        analysis = BookAnalysis(summary=long_summary)

        path = generate_slides(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        # The full 800 chars should not appear; truncated version with ... should
        assert "A" * 800 not in content, "Full 800-char summary should not appear"
        assert "..." in content, "Truncated summary should end with ellipsis"

    def test_flow_card_has_overflow_protection(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Flow card CSS should include max-height and overflow-y for safety."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "max-height: 420px" in content, "flow-card should have max-height"
        assert "overflow-y: auto" in content, "flow-card should have overflow-y: auto"
