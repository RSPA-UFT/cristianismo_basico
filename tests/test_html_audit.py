"""Automated HTML audit tests for docs/*.html files.

Verifies:
- No literal Unicode escapes (\\u00XX)
- Proper Portuguese diacritics in visible text
- No English labels in visible text
- Consistent color palette
- TYPE_LABELS in Portuguese
- References tab present with search
- No removed tabs (Sankey, Confidence)
- Slide heading contrast colors
- Slide overflow protections
- Consistent navigation
- lang="pt-BR" and charset
"""

import re
from pathlib import Path

import pytest

DOCS_DIR = Path("docs")


def _get_html_files():
    """Return all HTML files in docs/."""
    return sorted(DOCS_DIR.glob("*.html"))


def _extract_visible_text(html: str) -> str:
    """Extract visible text from HTML, excluding <script> and <style> blocks."""
    # Remove script and style blocks
    text = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode common HTML entities
    text = text.replace("&mdash;", " ").replace("&bull;", " ").replace("&rarr;", " ")
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    return text


class TestNoLiteralUnicodeEscapes:
    """E1: No docs/*.html should contain \\u00XX literal."""

    def test_no_literal_unicode_escapes(self):
        for html_file in _get_html_files():
            content = html_file.read_text(encoding="utf-8")
            assert "\\u00" not in content, (
                f"{html_file.name}: contains literal \\u00XX escape"
            )


class TestDiacriticsInPortuguese:
    """E2: Common Portuguese words should appear with diacritics, not ASCII."""

    # Pairs of (ASCII form that should NOT appear, correct form)
    DIACRITIC_PAIRS = [
        ("Analise", "Análise"),
        ("Visao Geral", "Visão Geral"),
        ("Citacoes", "Citações"),
        ("Confianca", "Confiança"),
        ("Titulo", "Título"),
        ("Distribuicao", "Distribuição"),
        ("Raciocinio", "Raciocínio"),
        ("Conexao", "Conexão"),
        ("Tematicos", "Temáticos"),
        ("Apresentacao", "Apresentação"),
    ]

    # Only check these on visualizacao.html (the panel with UI labels)
    VIZ_ONLY_PAIRS = [
        ("Capitulo", "Capítulo"),
        ("Logica", "Lógica"),
    ]

    def test_diacritics_in_visualizacao(self):
        viz_file = DOCS_DIR / "visualizacao.html"
        if not viz_file.exists():
            pytest.skip("visualizacao.html not found")

        content = viz_file.read_text(encoding="utf-8")
        visible = _extract_visible_text(content)

        for ascii_form, correct_form in self.DIACRITIC_PAIRS + self.VIZ_ONLY_PAIRS:
            if ascii_form in visible:
                pytest.fail(
                    f"visualizacao.html: found ASCII '{ascii_form}' in visible text "
                    f"(should be '{correct_form}')"
                )

    def test_diacritics_in_index(self):
        index_file = DOCS_DIR / "index.html"
        if not index_file.exists():
            pytest.skip("index.html not found")

        content = index_file.read_text(encoding="utf-8")
        visible = _extract_visible_text(content)

        for ascii_form, correct_form in self.DIACRITIC_PAIRS:
            if ascii_form in visible:
                pytest.fail(
                    f"index.html: found ASCII '{ascii_form}' in visible text "
                    f"(should be '{correct_form}')"
                )

    def test_diacritics_in_apresentacao_chrome(self):
        """Check slide chrome (nav, headings) but not data content.

        Note: Data from JSON (summary, argument_flow) may contain ASCII
        because it comes from LLM output. This is out of scope for v0.7.0.
        """
        slides_file = DOCS_DIR / "apresentacao.html"
        if not slides_file.exists():
            pytest.skip("apresentacao.html not found")

        content = slides_file.read_text(encoding="utf-8")
        # Only check the nav bar area (first ~500 chars of visible text)
        nav_match = re.search(r"<nav.*?</nav>", content, re.DOTALL)
        if nav_match:
            nav_text = _extract_visible_text(nav_match.group(0))
            assert "Apresentacao" not in nav_text, (
                "apresentacao.html nav: 'Apresentacao' should be 'Apresentação'"
            )


class TestNoEnglishLabels:
    """E3: No English UI labels in visible text."""

    # These English words should not appear in user-facing text
    # Note: "Export" is excluded because "Exportar" (Portuguese) contains it as substring
    ENGLISH_LABELS = ["Overview", "Network", "Dashboard", "Scrollytelling"]

    def test_no_english_labels_in_visible_text(self):
        for html_file in _get_html_files():
            content = html_file.read_text(encoding="utf-8")
            visible = _extract_visible_text(content)

            for label in self.ENGLISH_LABELS:
                if label in visible:
                    pytest.fail(
                        f"{html_file.name}: found English label '{label}' in visible text"
                    )


class TestColorPalette:
    """E4: Only approved colors should appear."""

    # Colors that should NOT appear (old palette)
    FORBIDDEN_COLORS = [
        "#4682B4",  # SteelBlue
        "#DC143C",  # Crimson
        "#FF8C00",  # DarkOrange
        "#228B22",  # ForestGreen
        "#2c3e50",  # old dark
        "#1a1a2e",  # old navy
    ]

    def test_no_old_palette_colors(self):
        for html_file in _get_html_files():
            content = html_file.read_text(encoding="utf-8")
            for color in self.FORBIDDEN_COLORS:
                assert color.lower() not in content.lower(), (
                    f"{html_file.name}: contains forbidden color {color}"
                )

    def test_no_3498db_in_visualizacao(self):
        """The old blue #3498db should not appear in visualizacao.html."""
        viz_file = DOCS_DIR / "visualizacao.html"
        if viz_file.exists():
            content = viz_file.read_text(encoding="utf-8")
            assert "#3498db" not in content.lower(), (
                "visualizacao.html: contains old blue #3498db"
            )


class TestTypeLabelsPortuguese:
    """E5: TYPE_LABELS should render Portuguese type names."""

    def test_type_labels_defined(self):
        """TYPE_LABELS map should exist in visualizacao.html."""
        viz_file = DOCS_DIR / "visualizacao.html"
        if not viz_file.exists():
            pytest.skip("visualizacao.html not found")

        content = viz_file.read_text(encoding="utf-8")
        assert "TYPE_LABELS" in content, "TYPE_LABELS map should be defined"
        assert "'principal'" in content, "Should contain Portuguese label 'principal'"
        assert "'suporte'" in content, "Should contain Portuguese label 'suporte'"
        assert "'conclusão'" in content or "'conclus\\u00e3o'" in content, (
            "Should contain Portuguese label 'conclusão'"
        )
        assert "'premissa'" in content, "Should contain Portuguese label 'premissa'"


class TestReferencesTab:
    """E6: References tab should exist with search."""

    def test_references_tab_exists(self):
        viz_file = DOCS_DIR / "visualizacao.html"
        if not viz_file.exists():
            pytest.skip("visualizacao.html not found")

        content = viz_file.read_text(encoding="utf-8")
        assert 'data-tab="references"' in content, "References tab should exist"
        assert 'id="panel-references"' in content, "References panel should exist"

    def test_references_has_search(self):
        viz_file = DOCS_DIR / "visualizacao.html"
        if not viz_file.exists():
            pytest.skip("visualizacao.html not found")

        content = viz_file.read_text(encoding="utf-8")
        assert 'id="ref-search"' in content, "References panel should have search input"


class TestNoRemovedTabs:
    """E6b: Removed tabs (Sankey, Confidence) should not exist."""

    def test_no_sankey_tab(self):
        viz_file = DOCS_DIR / "visualizacao.html"
        if not viz_file.exists():
            pytest.skip("visualizacao.html not found")

        content = viz_file.read_text(encoding="utf-8")
        assert 'data-tab="sankey"' not in content, "Sankey tab should be removed"

    def test_no_confidence_tab(self):
        viz_file = DOCS_DIR / "visualizacao.html"
        if not viz_file.exists():
            pytest.skip("visualizacao.html not found")

        content = viz_file.read_text(encoding="utf-8")
        assert 'data-tab="confidence"' not in content, "Confidence tab should be removed"

    def test_no_d3_sankey_cdn(self):
        viz_file = DOCS_DIR / "visualizacao.html"
        if not viz_file.exists():
            pytest.skip("visualizacao.html not found")

        content = viz_file.read_text(encoding="utf-8")
        assert "d3-sankey" not in content, "d3-sankey CDN should be removed"


class TestSlideContrast:
    """E7: Slide headings should use darkened colors for contrast."""

    DARKENED_COLORS = ["#036c9a", "#b02a37", "#c96209", "#1e7b34"]

    def test_darkened_heading_colors(self):
        slides_file = DOCS_DIR / "apresentacao.html"
        if not slides_file.exists():
            pytest.skip("apresentacao.html not found")

        content = slides_file.read_text(encoding="utf-8")
        for color in self.DARKENED_COLORS:
            assert color in content, (
                f"apresentacao.html: missing darkened color {color} for headings"
            )


class TestSlideOverflow:
    """E8: Slides should have overflow protections."""

    def test_flow_slide_has_sub_sections(self):
        slides_file = DOCS_DIR / "apresentacao.html"
        if not slides_file.exists():
            pytest.skip("apresentacao.html not found")

        content = slides_file.read_text(encoding="utf-8")
        assert "Fluxo Argumentativo" in content
        # Flow slides use nested sections for vertical navigation (4 movements)
        # Check for individual movement slides instead of (cont.) suffix
        assert "Movimento 1:" in content, (
            "Flow slide should have movement 1 sub-slide"
        )
        assert "Movimento 4:" in content, (
            "Flow slide should have movement 4 sub-slide"
        )

    def test_scholarly_grid_layout(self):
        slides_file = DOCS_DIR / "apresentacao.html"
        if not slides_file.exists():
            pytest.skip("apresentacao.html not found")

        content = slides_file.read_text(encoding="utf-8")
        assert "scholarly-grid" in content, (
            "Scholarly citations should use grid layout"
        )

    def test_flow_card_overflow_protection(self):
        slides_file = DOCS_DIR / "apresentacao.html"
        if not slides_file.exists():
            pytest.skip("apresentacao.html not found")

        content = slides_file.read_text(encoding="utf-8")
        assert "max-height" in content, "flow-card should have max-height"
        assert "overflow-y" in content, "flow-card should have overflow-y"


class TestNavigation:
    """E9: All HTML pages should have consistent navigation."""

    NAV_LINKS = ["Narrativa", "Painel"]

    def test_navigation_present(self):
        for html_file in _get_html_files():
            content = html_file.read_text(encoding="utf-8")
            for link in self.NAV_LINKS:
                assert link in content, (
                    f"{html_file.name}: missing navigation link '{link}'"
                )

    def test_apresentacao_link(self):
        for html_file in _get_html_files():
            content = html_file.read_text(encoding="utf-8")
            # Check for Apresentação with proper diacritics
            assert "Apresentação" in content or "apresentacao.html" in content, (
                f"{html_file.name}: missing Apresentação navigation link"
            )


class TestLangAndCharset:
    """E10: All docs should have lang='pt-BR' and charset UTF-8."""

    def test_lang_pt_br(self):
        for html_file in _get_html_files():
            content = html_file.read_text(encoding="utf-8")
            assert 'lang="pt-BR"' in content, (
                f"{html_file.name}: missing lang=\"pt-BR\""
            )

    def test_charset_utf8(self):
        for html_file in _get_html_files():
            content = html_file.read_text(encoding="utf-8")
            assert 'charset="UTF-8"' in content or "charset=UTF-8" in content, (
                f"{html_file.name}: missing charset UTF-8"
            )
