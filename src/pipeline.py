"""Main orchestrator + CLI entry point."""

import json
import logging
import sys
import time
from pathlib import Path

from .analyzer import ThesisAnalyzer
from .chunker import HierarchicalChunker
from .config import Settings, settings
from .extractor import PDFExtractor
from .models import BookAnalysis, ChapterAnalysis, ExtractionResult
from .output import OutputWriter
from .scholarly import extract_footnotes_from_notes, extract_scholarly_citations
from .scrollytelling import generate_scrollytelling
from .validators import (
    detect_footnotes,
    log_quality_report,
    validate_citations,
    validate_theses,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _load_cached_extraction(cfg: Settings) -> ExtractionResult | None:
    """Load previously extracted text from cache to skip re-extraction."""
    cache_path = cfg.output_dir / "extracted_text.md"
    if not cache_path.exists():
        return None

    text = cache_path.read_text(encoding="utf-8")
    # Skip the metadata header (everything before "---\n\n")
    marker = "---\n\n"
    idx = text.find(marker)
    if idx != -1:
        text = text[idx + len(marker):]

    if len(text) < 500:
        return None

    logger.info(f"Loaded cached extraction from {cache_path} ({len(text):,} chars)")

    import fitz
    with fitz.open(str(cfg.pdf_path)) as doc:
        num_pages = len(doc)

    return ExtractionResult(
        text=text,
        num_pages=num_pages,
        total_chars=len(text),
        avg_chars_per_page=len(text) / max(num_pages, 1),
        extraction_method="docling",
        is_digital_pdf=True,
    )


def run_pipeline(cfg: Settings | None = None) -> BookAnalysis:
    """Execute the full 4-stage analysis pipeline."""
    cfg = cfg or settings
    cfg.ensure_output_dirs()

    writer = OutputWriter(cfg)
    t0 = time.time()

    # ── Stage 1: PDF Extraction ──────────────────────────────
    logger.info("=" * 60)
    logger.info("STAGE 1: PDF Extraction")
    logger.info("=" * 60)

    # Try cache first to avoid ~3min re-extraction
    extraction = _load_cached_extraction(cfg)
    if not extraction:
        extractor = PDFExtractor()
        extraction = extractor.extract(cfg.pdf_path)
        writer.save_extracted_text(extraction)

    logger.info(
        f"Extracted {extraction.num_pages} pages, "
        f"{extraction.total_chars:,} chars "
        f"(method: {extraction.extraction_method})"
    )

    # ── Stage 2: Hierarchical Chunking ───────────────────────
    logger.info("=" * 60)
    logger.info("STAGE 2: Hierarchical Chunking")
    logger.info("=" * 60)

    chunker = HierarchicalChunker()
    chunks = chunker.chunk(extraction)
    writer.save_chunks(chunks)

    for chunk in chunks:
        logger.info(
            f"  [{chunk.index:02d}] {chunk.title} "
            f"({chunk.char_count:,} chars, {chunk.source})"
        )

    # ── Stage 3: LLM Analysis ───────────────────────────────
    logger.info("=" * 60)
    logger.info("STAGE 3: LLM Analysis (Argument Mining)")
    logger.info(f"  Provider: {cfg.llm_provider}")
    logger.info("=" * 60)

    analyzer = ThesisAnalyzer(cfg)

    # Phase 3a: Extract theses per chunk (with resume support)
    logger.info("Phase 3a: Extracting theses per chunk...")
    chapter_analyses: list[ChapterAnalysis] = []

    for i, chunk in enumerate(chunks):
        # Check if this chunk was already analyzed
        cached_path = cfg.per_chapter_dir / f"chapter_{i:02d}_theses.json"
        if cached_path.exists():
            try:
                cached_data = json.loads(cached_path.read_text(encoding="utf-8"))
                analysis = ChapterAnalysis(**cached_data)
                logger.info(
                    f"  Cached chunk {i + 1}/{len(chunks)}: {chunk.title} "
                    f"({len(analysis.theses)} theses)"
                )
                chapter_analyses.append(analysis)
                continue
            except Exception:
                pass  # Re-analyze on cache error

        logger.info(f"  Analyzing chunk {i + 1}/{len(chunks)}: {chunk.title}")
        analysis = analyzer.analyze_chunk(chunk)
        chapter_analyses.append(analysis)
        writer.save_chapter_analysis(analysis, i)

    # Post-processing validation
    logger.info("Validating extracted data...")
    log_quality_report(chapter_analyses)
    for ca in chapter_analyses:
        ca.theses = validate_theses(ca.theses)
        ca.citations = validate_citations(ca.citations)

    # Collect all theses and citations
    all_theses = []
    all_citations = []
    for ca in chapter_analyses:
        all_theses.extend(ca.theses)
        all_citations.extend(ca.citations)

    logger.info(
        f"Phase 3a complete: {len(all_theses)} theses, "
        f"{len(all_citations)} citations across {len(chunks)} chunks"
    )

    # Phase 3a+: Scholarly citations & footnotes extraction
    logger.info("Phase 3a+: Extracting scholarly citations and footnotes...")
    scholarly = extract_scholarly_citations(cfg.chunks_dir)
    footnotes = extract_footnotes_from_notes(cfg.chunks_dir)
    all_citations.extend(scholarly)
    all_citations.extend(footnotes)
    all_citations = detect_footnotes(all_citations)
    logger.info(
        f"Phase 3a+ complete: {len(scholarly)} scholarly, "
        f"{len(footnotes)} footnotes added"
    )

    # Phase 3b: Chain extraction
    logger.info("Phase 3b: Extracting logical chains...")
    chains, argument_flow = analyzer.extract_chains(all_theses)
    logger.info(f"Phase 3b complete: {len(chains)} chains identified")

    # Phase 3c: Citation correlation
    logger.info("Phase 3c: Correlating citations...")
    citation_correlation = analyzer.correlate_citations(all_citations, all_theses)
    writer.save_citation_correlation(citation_correlation)
    logger.info("Phase 3c complete")

    # Phase 3d: Synthesis
    logger.info("Phase 3d: Synthesizing final analysis...")
    final_theses, summary = analyzer.synthesize(chapter_analyses)
    logger.info(f"Phase 3d complete: {len(final_theses)} final theses")

    # ── Stage 4: Output ──────────────────────────────────────
    logger.info("=" * 60)
    logger.info("STAGE 4: Output Generation")
    logger.info("=" * 60)

    book_analysis = BookAnalysis(
        theses=final_theses,
        chains=chains,
        citations=all_citations,
        summary=summary,
        argument_flow=argument_flow,
    )

    paths = writer.save_book_analysis(book_analysis)

    generate_scrollytelling(cfg.output_dir, book_analysis)

    elapsed = time.time() - t0

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"  Total time: {elapsed:.1f}s")
    logger.info(f"  Theses: {len(book_analysis.theses)}")
    logger.info(f"  Chains: {len(book_analysis.chains)}")
    logger.info(f"  Citations: {len(book_analysis.citations)}")
    logger.info(f"  Report: {paths.get('report', 'N/A')}")
    logger.info("=" * 60)

    return book_analysis


def main() -> None:
    """CLI entry point."""
    # Allow overriding PDF path via command line
    cfg = settings
    if len(sys.argv) > 1:
        cfg = Settings(pdf_filename=sys.argv[1])

    try:
        run_pipeline(cfg)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
