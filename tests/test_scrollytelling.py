"""Tests for src.scrollytelling -- Scrollytelling page generation.

Covers:
- generate_scrollytelling: file creation and HTML structure
- Data embedding: THESES, CHAINS, CITATIONS, GROUPS constants
- Section presence: hero, 4 parts, network, citations, conclusion
- Accessibility: lang, viewport, prefers-reduced-motion
- Loading from files: JSON + citation_groups
"""

import json
from pathlib import Path

import pytest

from src.models import BookAnalysis, Citation, Thesis, ThesisChain
from src.scrollytelling import generate_scrollytelling


class TestGenerateScrollytelling:
    """Tests for file creation and basic HTML structure."""

    def test_creates_file(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)

        assert path.exists(), "scrollytelling.html should be created"
        assert path.name == "scrollytelling.html"

    def test_html_references_scrollama(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "scrollama" in content, "Should reference Scrollama.js"

    def test_html_references_d3(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "d3@7" in content, "Should reference D3.js v7"

    def test_steps_present(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert 'data-step="1"' in content, "Should have step 1"
        assert 'data-step="10"' in content, "Should have step 10 (network)"
        assert 'data-step="11"' in content, "Should have step 11 (citations)"


class TestDataEmbedding:
    """Tests for JavaScript data embedding."""

    def test_theses_embedded(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "const THESES" in content, "Should embed THESES constant"
        assert "T1.1.1" in content, "Should contain thesis ID T1.1.1"

    def test_chains_embedded(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "const CHAINS" in content, "Should embed CHAINS constant"

    def test_citations_embedded(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "const CITATIONS" in content, "Should embed CITATIONS constant"

    def test_groups_embedded(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "const GROUPS" in content, "Should embed GROUPS constant"


class TestSectionPresence:
    """Tests for the presence of all narrative sections."""

    def test_hero_section(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "Cristianismo B\u00e1sico" in content, "Hero should have title"
        assert "John Stott" in content, "Hero should have author"

    def test_four_parts_mentioned(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "Parte 1" in content, "Should mention Parte 1"
        assert "Parte 2" in content, "Should mention Parte 2"
        assert "Parte 3" in content, "Should mention Parte 3"
        assert "Parte 4" in content, "Should mention Parte 4"

    def test_network_svg(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "network-svg" in content, "Should have network SVG element"

    def test_part_colors(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "#048fcc" in content, "Should use ICE cyan for Parte 1"
        assert "#dc3545" in content, "Should use red for Parte 2"
        assert "#fd7e14" in content, "Should use orange for Parte 3"
        assert "#28a745" in content, "Should use green for Parte 4"


class TestAccessibility:
    """Tests for accessibility features."""

    def test_lang_attribute(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert 'lang="pt-BR"' in content, "Should have lang=pt-BR"

    def test_viewport_meta(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "viewport" in content, "Should have viewport meta tag"

    def test_prefers_reduced_motion(
        self, tmp_path: Path, sample_book_analysis: BookAnalysis
    ):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_scrollytelling(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "prefers-reduced-motion" in content, "Should support reduced motion"


class TestLoadFromFiles:
    """Tests for loading analysis from JSON files."""

    def test_loads_from_json_files(self, tmp_path: Path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        theses = [
            Thesis(
                id="T1.1.1",
                title="Test thesis",
                description="Desc",
                chapter="Cap 1",
                part="Parte 1 - A Pessoa de Cristo",
            ).model_dump(mode="json"),
        ]
        chains = [
            ThesisChain(
                from_thesis_id="T1.1.1",
                to_thesis_id="T1.1.2",
                relationship="supports",
            ).model_dump(mode="json"),
        ]
        citations = [
            Citation(
                reference="Jo 3:16",
                citation_type="biblical",
            ).model_dump(mode="json"),
        ]

        (output_dir / "theses.json").write_text(
            json.dumps(theses, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / "chains.json").write_text(
            json.dumps(chains, ensure_ascii=False), encoding="utf-8"
        )
        (output_dir / "citations.json").write_text(
            json.dumps(citations, ensure_ascii=False), encoding="utf-8"
        )

        path = generate_scrollytelling(output_dir)

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Cristianismo B\u00e1sico" in content
        assert "T1.1.1" in content

    def test_loads_citation_groups(self, tmp_path: Path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        (output_dir / "theses.json").write_text("[]", encoding="utf-8")
        (output_dir / "chains.json").write_text("[]", encoding="utf-8")
        (output_dir / "citations.json").write_text("[]", encoding="utf-8")

        groups = {
            "groups": [
                {
                    "theme": "Cristologia",
                    "description": "Passagens cristologicas",
                    "references": ["Jo 1:1", "Jo 10:30"],
                },
            ]
        }
        (output_dir / "citation_groups.json").write_text(
            json.dumps(groups, ensure_ascii=False), encoding="utf-8"
        )

        path = generate_scrollytelling(output_dir)

        content = path.read_text(encoding="utf-8")
        assert "Cristologia" in content, "Should include citation group theme"


class TestPartFilterFallback:
    """Test that theses with empty part field are matched via ID derivation."""

    def test_part_theses_shown_with_empty_part(self, tmp_path: Path):
        """Theses with empty part should appear via ID fallback."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        analysis = BookAnalysis(
            theses=[
                Thesis(
                    id="T1.1.1",
                    title="Tese derivada da Parte 1",
                    description="Desc",
                    thesis_type="main",
                    part="",
                ),
                Thesis(
                    id="T3.7.1",
                    title="Tese derivada da Parte 3",
                    description="Desc",
                    thesis_type="main",
                    part="",
                ),
            ],
        )

        path = generate_scrollytelling(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        # The thesis titles should appear in the part theses steps
        assert "Tese derivada da Parte 1" in content, "T1.x thesis should appear in Parte 1"
        assert "Tese derivada da Parte 3" in content, "T3.x thesis should appear in Parte 3"

    def test_overview_bar_counts_with_empty_part(self, tmp_path: Path):
        """Part bar percentages should be non-zero when parts derived from IDs."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        analysis = BookAnalysis(
            theses=[
                Thesis(id="T1.1.1", title="A", description="D", part=""),
                Thesis(id="T2.5.1", title="B", description="D", part=""),
            ],
        )

        path = generate_scrollytelling(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        # Both parts should have 50% width
        assert "width:50.0%" in content, "Each part should have 50% in the bar"
