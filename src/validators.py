"""Post-processing validation for extracted theses and citations."""

import logging
import re
from collections import Counter

from .models import ChapterAnalysis, Citation, Thesis

logger = logging.getLogger(__name__)

# Pattern matching biblical references like "Jo 3:16", "1Co 2:2", "Gn 1:1-3"
BIBLICAL_REF_PATTERN = re.compile(
    r"^[1-3]?\s?[A-Za-zÀ-ú]{1,5}\s+\d+[.:]\d+(?:\s*[-–]\s*\d+)?$"
)


def validate_citations(citations: list[Citation]) -> list[Citation]:
    """Filter out citations with empty references and fix classification.

    - Removes citations where reference is empty
    - Reclassifies citations with biblical reference patterns as 'biblical'
    """
    valid = []
    removed = 0
    reclassified = 0

    for c in citations:
        ref = c.reference.strip() if c.reference else ""
        if not ref:
            removed += 1
            continue

        # Reclassify: if reference matches biblical pattern, force biblical type
        if c.citation_type != "biblical" and BIBLICAL_REF_PATTERN.match(ref):
            c.citation_type = "biblical"
            reclassified += 1

        valid.append(c)

    if removed:
        logger.info(f"Validation: removed {removed} citations with empty reference")
    if reclassified:
        logger.info(f"Validation: reclassified {reclassified} citations as biblical")

    return valid


def validate_theses(theses: list[Thesis]) -> list[Thesis]:
    """Validate and clean thesis citations, detect duplicates.

    - Applies validate_citations to each thesis's citation list
    - Logs duplicate supporting_text within same chapter
    """
    duplicates_found = 0
    seen_texts: dict[str, list[str]] = {}  # chapter -> list of supporting_texts

    for t in theses:
        # Clean thesis-level citations
        if t.citations:
            t.citations = validate_citations(t.citations)

        # Detect duplicate supporting_text within same chapter
        key = t.chapter or "unknown"
        st = (t.supporting_text or "").strip()
        if st and len(st) > 30:
            if key not in seen_texts:
                seen_texts[key] = []
            if st in seen_texts[key]:
                duplicates_found += 1
                logger.warning(
                    f"Duplicate supporting_text in '{key}': thesis {t.id} "
                    f"('{st[:60]}...')"
                )
            else:
                seen_texts[key].append(st)

    if duplicates_found:
        logger.info(
            f"Validation: found {duplicates_found} theses with duplicate supporting_text"
        )

    return theses


def log_quality_report(chapter_analyses: list[ChapterAnalysis]) -> None:
    """Log a summary quality report for all chapter analyses."""
    total_theses = 0
    total_citations = 0
    empty_refs = 0
    type_counts: Counter[str] = Counter()
    low_confidence = 0

    for ca in chapter_analyses:
        total_theses += len(ca.theses)
        total_citations += len(ca.citations)

        for t in ca.theses:
            if t.confidence < 0.7:
                low_confidence += 1
            for c in t.citations:
                type_counts[c.citation_type] += 1
                if not c.reference.strip():
                    empty_refs += 1

        for c in ca.citations:
            type_counts[c.citation_type] += 1
            if not c.reference.strip():
                empty_refs += 1

    logger.info("=" * 50)
    logger.info("QUALITY REPORT")
    logger.info(f"  Total theses: {total_theses}")
    logger.info(f"  Total citations: {total_citations}")
    logger.info(f"  Empty references: {empty_refs}")
    logger.info(f"  Low confidence theses (<0.7): {low_confidence}")
    logger.info(f"  Citation types: {dict(type_counts)}")
    logger.info("=" * 50)
