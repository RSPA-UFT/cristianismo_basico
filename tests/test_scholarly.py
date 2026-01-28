"""Tests for src.scholarly -- scholarly citation extraction.

Covers:
- extract_scholarly_citations: extraction from known references and inline mentions
- extract_footnotes_from_notes: extraction of footnote-style citations
- Integration with notes chunk file
"""

from pathlib import Path

import pytest

from src.scholarly import (
    extract_footnotes_from_notes,
    extract_scholarly_citations,
)


class TestExtractScholarlyCitations:
    """Tests for the extract_scholarly_citations function."""

    def test_returns_citations(self, sample_notes_chunk: Path):
        """Should return a non-empty list of scholarly citations."""
        result = extract_scholarly_citations(sample_notes_chunk)

        assert len(result) > 0, "Should extract at least one scholarly citation"
        for c in result:
            assert c.citation_type == "scholarly"

    def test_known_authors_included(self, sample_notes_chunk: Path):
        """Should include the known authors from the book's notes."""
        result = extract_scholarly_citations(sample_notes_chunk)
        authors = [c.author for c in result if c.author]

        assert any("FORSYTH" in a for a in authors), "FORSYTH should be found"
        assert any("LEWIS" in a for a in authors), "LEWIS should be found"

    def test_inline_mentions_included(self, sample_notes_chunk: Path):
        """Should include inline scholarly mentions from body chapters."""
        result = extract_scholarly_citations(sample_notes_chunk)
        authors = [c.author for c in result if c.author]

        assert any("Emerson" in a for a in authors), "Emerson should be in inline mentions"
        assert any("John Stuart Mill" in a for a in authors), "Mill should be in inline mentions"

    def test_no_duplicates(self, sample_notes_chunk: Path):
        """Should not have duplicate author+work combinations."""
        result = extract_scholarly_citations(sample_notes_chunk)
        keys = set()
        for c in result:
            key = f"{c.author}|{c.work}"
            assert key not in keys, f"Duplicate found: {key}"
            keys.add(key)

    def test_work_and_context_populated(self, sample_notes_chunk: Path):
        """Known scholarly refs should have work and/or context fields."""
        result = extract_scholarly_citations(sample_notes_chunk)
        lewis_refs = [c for c in result if c.author and "LEWIS" in c.author and c.work]

        assert len(lewis_refs) > 0, "C.S. Lewis should have a work field"
        assert lewis_refs[0].work == "Miracles"

    def test_missing_chunks_dir(self, tmp_path: Path):
        """Should still return results (from known data) even if notes file is missing."""
        empty_dir = tmp_path / "empty_chunks"
        empty_dir.mkdir()

        result = extract_scholarly_citations(empty_dir)

        # Should still have the known + inline refs
        assert len(result) > 0


class TestExtractFootnotes:
    """Tests for the extract_footnotes_from_notes function."""

    def test_extracts_footnotes(self, sample_notes_chunk: Path):
        """Should extract footnote-type citations from the notes file."""
        result = extract_footnotes_from_notes(sample_notes_chunk)

        # Should find at least the biblical-reference footnotes
        assert isinstance(result, list)
        for c in result:
            assert c.citation_type == "footnote"

    def test_missing_file_returns_empty(self, tmp_path: Path):
        """When the notes file doesn't exist, return empty list."""
        empty_dir = tmp_path / "no_chunks"
        empty_dir.mkdir()

        result = extract_footnotes_from_notes(empty_dir)

        assert result == []

    def test_footnotes_have_context(self, sample_notes_chunk: Path):
        """Footnotes should include chapter context."""
        result = extract_footnotes_from_notes(sample_notes_chunk)

        for c in result:
            if c.context:
                assert "Cap." in c.context or "Nota" in c.context
