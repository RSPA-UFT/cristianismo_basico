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
        assert ">1</strong> ideias-chave" in content, "Parts with data should show non-zero thesis counts"

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
        """Flow slide should have structured movement sub-slides."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        analysis = BookAnalysis(
            argument_flow="Any flow text",
        )

        path = generate_slides(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        assert "Fluxo Argumentativo: 4 Movimentos" in content
        assert "Movimento 1:" in content, "Should have Movement 1 sub-slide"
        assert "Movimento 2:" in content, "Should have Movement 2 sub-slide"
        assert "Movimento 3:" in content, "Should have Movement 3 sub-slide"
        assert "Movimento 4:" in content, "Should have Movement 4 sub-slide"
        assert "content-bullets" in content, "Should use bullet point structure"

    def test_summary_multi_slide(self, tmp_path: Path):
        """Long summaries should be split into multiple sub-slides."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        long_summary = (
            "Primeira frase do resumo executivo com bastante conteudo. "
            "Segunda frase explicando a Parte 1 do livro sobre a pessoa de Cristo. "
            "Terceira frase sobre a Parte 2 e a necessidade do homem diante do pecado. "
            "Quarta frase descrevendo a Parte 3 e a obra redentora de Cristo na cruz. "
            "Quinta frase sobre a Parte 4 e a resposta esperada do ser humano. "
            "Sexta frase concluindo o resumo executivo com uma visao geral completa. "
            "Setima frase adicionando mais detalhes sobre a estrutura argumentativa. "
            "Oitava frase finalizando o resumo com consideracoes metodologicas."
        )
        analysis = BookAnalysis(summary=long_summary)

        path = generate_slides(output_dir, analysis=analysis)
        content = path.read_text(encoding="utf-8")

        assert "Resumo Executivo" in content
        assert "Resumo Executivo (cont.)" in content, "Long summary should have continuation sub-slides"

    def test_no_background_color_tint(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Part slides should NOT use data-background-color with alpha tint."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert 'data-background-color' not in content, (
            "Part slides should not use data-background-color (marca-texto effect)"
        )

    def test_part_slides_have_border_accent(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Part slides should have a colored border-top accent."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "border-top: 6px solid #048fcc" in content, "Parte 1 should have blue border accent"
        assert "border-top: 6px solid #dc3545" in content, "Parte 2 should have red border accent"
        assert "border-top: 6px solid #fd7e14" in content, "Parte 3 should have orange border accent"
        assert "border-top: 6px solid #28a745" in content, "Parte 4 should have green border accent"

    def test_logo_embedded_when_provided(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Logo should be embedded as base64 when logo_path is provided."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a minimal PNG file (1x1 pixel)
        logo_path = tmp_path / "logo.png"
        import base64
        # Minimal valid PNG (1x1 transparent pixel)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        logo_path.write_bytes(png_data)

        path = generate_slides(output_dir, analysis=sample_book_analysis, logo_path=logo_path)
        content = path.read_text(encoding="utf-8")

        assert "data:image/png;base64," in content, "Logo should be embedded as base64"
        assert "125 Anos" in content, "Logo alt text should mention 125 Anos"

    def test_no_logo_when_not_provided(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """No logo should appear when logo_path is not provided."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "data:image/png;base64," not in content, "No logo should appear without logo_path"

    def test_flow_card_has_overflow_protection(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Flow card CSS should include max-height and overflow-y for safety."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "max-height: 420px" in content, "flow-card should have max-height"
        assert "overflow-y: auto" in content, "flow-card should have overflow-y: auto"

    def test_glossary_slide_present(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Glossary slide should be present with theological terms."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "Termos Explicados" in content, "Should have glossary slide"
        assert "glossary-grid" in content, "Should use glossary grid layout"
        assert "Impecabilidade" in content, "Should explain impeccability"
        assert "Arrependimento" in content, "Should explain repentance"
        assert "Reconciliação" in content, "Should explain reconciliation"

    def test_part_slides_have_icons(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Part slides should have visual emoji icons."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "👤" in content, "Parte 1 should have person icon"
        assert "⚠️" in content, "Parte 2 should have warning icon"
        assert "✝️" in content, "Parte 3 should have cross icon"
        assert "🙏" in content, "Parte 4 should have prayer icon"

    def test_part_slides_have_descriptions(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Part slides should have contextual descriptions."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "quem Jesus é" in content, "Parte 1 should have description"
        assert "realidade do pecado" in content, "Parte 2 should have description"
        assert "solução definitiva" in content, "Parte 3 should have description"
        assert "Arrependimento, fé" in content, "Parte 4 should have description"

    def test_part_slides_have_vertical_subslides(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Part slides should use nested sections for vertical navigation."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        # Check for nested section structure (vertical slides)
        assert "Teses Principais" in content, "Should have thesis sub-slides"
        # Verify nested sections exist (parent <section> containing child <section>s)
        import re
        nested_pattern = r'<section>\s*\n\s*<section>'
        assert re.search(nested_pattern, content), "Part slides should have nested sections for vertical navigation"

    def test_accessibility_css_present(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Accessibility CSS should include focus states and media queries."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "*:focus" in content, "Should have focus styles"
        assert "prefers-reduced-motion" in content, "Should support reduced motion"
        assert "prefers-contrast" in content, "Should support high contrast"

    def test_improved_typography_sizes(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Typography should use larger sizes for accessibility."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "font-size: 2.2em" in content, "h1 should be 2.2em"
        assert "font-size: 1.6em" in content, "h2 should be 1.6em"
        # Check for improved contrast colors
        assert "color: #333" in content, "Should use darker subtitle color for contrast"

    def test_reveal_navigation_config(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Reveal.js should have improved navigation configuration."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert "slideNumber: 'c/t'" in content, "Should show current/total slide numbers"
        assert "transition: 'fade'" in content, "Should use fade transition"
        assert "transitionSpeed: 'slow'" in content, "Should use slow transition"
        assert "controls: true" in content, "Should show navigation controls"

    def test_title_slide_has_aria_role(self, tmp_path: Path, sample_book_analysis: BookAnalysis):
        """Title slide should have ARIA role for screen readers."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        path = generate_slides(output_dir, analysis=sample_book_analysis)
        content = path.read_text(encoding="utf-8")

        assert 'role="region"' in content, "Title slide should have ARIA role"
        assert 'aria-label="Slide de título"' in content, "Title slide should have ARIA label"
