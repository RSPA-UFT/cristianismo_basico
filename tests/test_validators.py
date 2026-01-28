"""Tests for src.validators -- post-processing validation utilities.

Covers:
- validate_citations: removal of empty references, reclassification of
  biblical references, retention of scholarly references.
- validate_theses: delegation to validate_citations per thesis, and
  detection of duplicate supporting_text within the same chapter.
- log_quality_report: smoke test that the function runs without errors.

Strategy: All tests are pure unit tests with no mocking required (the
validators are stateless functions).  ``caplog`` is used to verify logging
side-effects where relevant.
"""

import logging

import pytest

from src.models import ChapterAnalysis, Citation, Thesis
from src.validators import detect_footnotes, log_quality_report, validate_citations, validate_theses


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _citation(
    reference: str = "Jo 3:16",
    text: str = "sample",
    citation_type: str = "biblical",
) -> Citation:
    """Shortcut to build a Citation with sensible defaults."""
    return Citation(reference=reference, text=text, citation_type=citation_type)


def _thesis(
    thesis_id: str = "T1.1.1",
    chapter: str = "Cap 1",
    supporting_text: str = "This is a long enough supporting text for deduplication detection purposes.",
    citations: list[Citation] | None = None,
    confidence: float = 0.9,
) -> Thesis:
    """Shortcut to build a Thesis with sensible defaults."""
    return Thesis(
        id=thesis_id,
        title="Thesis title",
        description="Thesis description",
        chapter=chapter,
        supporting_text=supporting_text,
        citations=citations or [],
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# validate_citations
# ---------------------------------------------------------------------------

class TestValidateCitations:
    """Tests for the validate_citations function."""

    def test_validate_citations_removes_empty_ref(self):
        """A citation whose reference is the empty string must be removed."""
        citations = [_citation(reference="")]
        result = validate_citations(citations)

        assert len(result) == 0, (
            "Citations with empty reference should be filtered out"
        )

    def test_validate_citations_keeps_valid(self):
        """A citation with a valid biblical reference is retained as-is."""
        citations = [_citation(reference="Jo 3:16", citation_type="biblical")]
        result = validate_citations(citations)

        assert len(result) == 1, "Valid citations must be kept"
        assert result[0].reference == "Jo 3:16"
        assert result[0].citation_type == "biblical"

    def test_validate_citations_reclassify_biblical(self):
        """A citation whose reference matches the biblical pattern but is
        tagged as 'scholarly' must be reclassified to 'biblical'."""
        citations = [_citation(reference="Rm 5:8", citation_type="scholarly")]
        result = validate_citations(citations)

        assert len(result) == 1
        assert result[0].citation_type == "biblical", (
            "Citation with biblical-pattern reference must be reclassified "
            "from 'scholarly' to 'biblical'"
        )

    def test_validate_citations_keeps_scholarly(self):
        """A citation with a non-biblical reference (e.g. author-year)
        must keep its 'scholarly' type."""
        citations = [_citation(reference="Stott, 1958", citation_type="scholarly")]
        result = validate_citations(citations)

        assert len(result) == 1
        assert result[0].citation_type == "scholarly", (
            "Scholarly citations whose reference does not match the biblical "
            "pattern must remain 'scholarly'"
        )

    def test_validate_citations_multiple_empty(self):
        """When multiple empty-ref citations are mixed with valid ones,
        only the valid citations survive."""
        citations = [
            _citation(reference=""),
            _citation(reference="Gn 1:1", citation_type="biblical"),
            _citation(reference="  "),
            _citation(reference="1Co 2:2", citation_type="scholarly"),
            _citation(reference=""),
        ]
        result = validate_citations(citations)

        assert len(result) == 2, (
            f"Expected 2 valid citations but got {len(result)}"
        )
        references = [c.reference for c in result]
        assert "Gn 1:1" in references
        assert "1Co 2:2" in references


# ---------------------------------------------------------------------------
# validate_theses
# ---------------------------------------------------------------------------

class TestValidateTheses:
    """Tests for the validate_theses function."""

    def test_validate_theses_cleans_citations(self):
        """Empty-ref citations attached to a thesis must be removed by
        validate_theses (which delegates to validate_citations)."""
        thesis = _thesis(
            citations=[
                _citation(reference=""),
                _citation(reference="Jo 3:16"),
                _citation(reference="  "),
            ]
        )
        result = validate_theses([thesis])

        assert len(result) == 1, "The thesis itself should be retained"
        assert len(result[0].citations) == 1, (
            "Only the citation with a non-empty reference should remain"
        )
        assert result[0].citations[0].reference == "Jo 3:16"

    def test_validate_theses_detects_duplicates(self, caplog):
        """Two theses in the same chapter sharing identical supporting_text
        must produce a warning log entry."""
        shared_text = (
            "This is a duplicated supporting text that is long enough "
            "to trigger the deduplication check in validate_theses."
        )
        thesis_a = _thesis(thesis_id="T1.1.1", chapter="Cap 1", supporting_text=shared_text)
        thesis_b = _thesis(thesis_id="T1.1.2", chapter="Cap 1", supporting_text=shared_text)

        with caplog.at_level(logging.WARNING, logger="src.validators"):
            validate_theses([thesis_a, thesis_b])

        # Check that a duplicate warning was emitted
        duplicate_warnings = [
            rec for rec in caplog.records
            if "Duplicate supporting_text" in rec.message
        ]
        assert len(duplicate_warnings) >= 1, (
            "A warning about duplicate supporting_text should be logged "
            "when two theses in the same chapter share the same text"
        )


# ---------------------------------------------------------------------------
# log_quality_report
# ---------------------------------------------------------------------------

class TestLogQualityReport:
    """Tests for the log_quality_report function."""

    def test_log_quality_report_runs(self, caplog):
        """log_quality_report should execute without errors and produce
        log output when given a list of ChapterAnalysis objects."""
        analyses = [
            ChapterAnalysis(
                chunk_title="Capitulo 1",
                theses=[
                    _thesis(
                        citations=[
                            _citation(reference="Jo 3:16"),
                            _citation(reference=""),
                        ],
                        confidence=0.5,
                    ),
                ],
                citations=[
                    _citation(reference="Rm 5:8"),
                    _citation(reference=""),
                ],
            ),
            ChapterAnalysis(
                chunk_title="Capitulo 2",
                theses=[],
                citations=[],
            ),
        ]

        with caplog.at_level(logging.INFO, logger="src.validators"):
            log_quality_report(analyses)

        # The function should not raise and should produce QUALITY REPORT output
        quality_lines = [
            rec for rec in caplog.records if "QUALITY REPORT" in rec.message
        ]
        assert len(quality_lines) >= 1, (
            "log_quality_report should log a 'QUALITY REPORT' header"
        )


# ---------------------------------------------------------------------------
# detect_footnotes
# ---------------------------------------------------------------------------

class TestDetectFootnotes:
    """Tests for the detect_footnotes function."""

    def test_numeric_reference_reclassified(self):
        """A citation whose reference is a bare number should become 'footnote'."""
        citations = [_citation(reference="5", citation_type="biblical")]
        result = detect_footnotes(citations)

        assert len(result) == 1
        assert result[0].citation_type == "footnote"

    def test_scholarly_not_reclassified(self):
        """Scholarly citations with numeric-looking ref should not be reclassified."""
        citations = [_citation(reference="42", citation_type="scholarly")]
        result = detect_footnotes(citations)

        assert result[0].citation_type == "scholarly"

    def test_biblical_preserved(self):
        """Biblical citations should not be reclassified as footnotes."""
        citations = [_citation(reference="Jo 3:16", citation_type="biblical")]
        result = detect_footnotes(citations)

        assert result[0].citation_type == "biblical"
