# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-01-27

### Added
- `derive_part_from_id()` and `derive_chapter_from_id()` in `src/models.py` for extracting part/chapter from thesis IDs
- Backfill of `part` and `chapter` fields in `OutputWriter.save_book_analysis()`
- Navigation bar (Narrativa / Painel / Apresentacao) on all pages
- ICE Metropolitana visual identity: brand color `#048fcc`, sans-serif typography, rounded buttons
- New semantic part colors harmonized with brand: `#048fcc`, `#dc3545`, `#fd7e14`, `#28a745`
- Tests for ID-based derivation (`test_models.py`), filter fallback (`test_slides.py`, `test_scrollytelling.py`)
- `CHANGELOG.md` (this file)
- Git tags v0.1.0 through v0.5.0 on existing commits

### Fixed
- Empty thesis lists in slides (Parte 1-4 showing "0 teses") caused by missing `part` field in `theses.json`
- Empty thesis lists in scrollytelling sections (same root cause)
- JS-side thesis filtering in scrollytelling network and part visualizations
- Scholarly citations limited to 8 in slides (now shows all)

### Changed
- Navigation labels from English to Portuguese: Scrollytelling -> Narrativa, Dashboard -> Painel, Slides -> Apresentacao
- All user-facing text now uses proper Portuguese diacritics (Basico -> Basico, Analise -> Analise, etc.)
- Font family from Georgia serif to system sans-serif stack
- Hero gradient from dark navy (`#1a1a2e`) to ICE brand gradient (`#03618b` -> `#048fcc`)
- Part colors from SteelBlue/Crimson/DarkOrange/ForestGreen to harmonized palette
- Stat box accent color from `#3498db` to `#048fcc`
- `pyproject.toml` version bumped to `0.6.0`

## [0.5.0] - 2026-01-26

### Changed
- Updated documentation for scrollytelling and GitHub Pages (iteration 5)
- Refined README with complete architecture description

## [0.4.0] - 2026-01-26

### Added
- Scrollytelling page with 12 narrative sections (Scrollama.js + D3.js)
- GitHub Pages setup with `docs/` directory
- Navigation between scrollytelling, dashboard, and slides
- Tests for scrollytelling generation

## [0.3.0] - 2026-01-26

### Added
- Scholarly citations extraction with author/work/context fields
- Footnote detection and reclassification
- Sankey diagram for argument flow visualization
- PDF report generation (WeasyPrint / Ctrl+P)
- Reveal.js slide presentation (10 slides)
- Citation model extended with `author`, `work`, `context` fields

## [0.1.0] - 2026-01-25

### Added
- Initial project structure with Pydantic models
- PDF text extraction (3-tier: Docling, PyMuPDF, Tesseract)
- Hierarchical chunking by chapters and parts
- LLM-based thesis extraction, chain detection, and citation correlation
- Deduplication and synthesis pipeline
- Interactive dashboard with 7 tabs (D3.js + Chart.js)
- Markdown report generation
- Configuration via `.env` (Pydantic Settings)
- Comprehensive test suite (160+ tests)
