"""Tests for Pydantic models in src.models."""

import pytest
from pydantic import ValidationError

from src.models import (
    BookAnalysis,
    ChapterAnalysis,
    ChunkInfo,
    Citation,
    ExtractionResult,
    PageText,
    Thesis,
    ThesisChain,
    derive_chapter_from_id,
    derive_part_from_id,
)


# ---------------------------------------------------------------------------
# 1. PageText basic validation
# ---------------------------------------------------------------------------

class TestPageText:
    def test_basic_creation(self):
        """PageText requires page_number (int) and text (str)."""
        pt = PageText(page_number=1, text="Hello world")
        assert pt.page_number == 1
        assert pt.text == "Hello world"

    def test_missing_required_fields_raises(self):
        """Omitting either required field must raise ValidationError."""
        with pytest.raises(ValidationError):
            PageText(page_number=1)  # missing text
        with pytest.raises(ValidationError):
            PageText(text="abc")  # missing page_number


# ---------------------------------------------------------------------------
# 2. ExtractionResult defaults and pages list
# ---------------------------------------------------------------------------

class TestExtractionResult:
    def test_defaults(self):
        """All optional fields should fall back to their declared defaults."""
        er = ExtractionResult(text="content")
        assert er.pages == []
        assert er.num_pages == 0
        assert er.total_chars == 0
        assert er.avg_chars_per_page == 0.0
        assert er.extraction_method == ""
        assert er.is_digital_pdf is False

    def test_with_pages(self):
        """ExtractionResult can hold a list of PageText objects."""
        pages = [
            PageText(page_number=1, text="First page"),
            PageText(page_number=2, text="Second page"),
        ]
        er = ExtractionResult(
            text="full text",
            pages=pages,
            num_pages=2,
            total_chars=20,
            avg_chars_per_page=10.0,
            extraction_method="pymupdf",
            is_digital_pdf=True,
        )
        assert len(er.pages) == 2
        assert er.pages[0].page_number == 1
        assert er.num_pages == 2
        assert er.extraction_method == "pymupdf"
        assert er.is_digital_pdf is True


# ---------------------------------------------------------------------------
# 3. ChunkInfo required fields
# ---------------------------------------------------------------------------

class TestChunkInfo:
    def test_required_fields_only(self):
        """index, title, and text are required; the rest have defaults."""
        ci = ChunkInfo(index=0, title="Chapter 1", text="Lorem ipsum")
        assert ci.index == 0
        assert ci.title == "Chapter 1"
        assert ci.text == "Lorem ipsum"
        assert ci.part == ""
        assert ci.chapter == ""
        assert ci.part_index is None
        assert ci.chapter_index is None
        assert ci.char_count == 0
        assert ci.page_range is None
        assert ci.source == ""

    def test_missing_required_raises(self):
        """Omitting any of the three required fields must raise."""
        with pytest.raises(ValidationError):
            ChunkInfo(title="T", text="T")  # missing index
        with pytest.raises(ValidationError):
            ChunkInfo(index=0, text="T")  # missing title
        with pytest.raises(ValidationError):
            ChunkInfo(index=0, title="T")  # missing text


# ---------------------------------------------------------------------------
# 4. Citation defaults
# ---------------------------------------------------------------------------

class TestCitation:
    def test_defaults(self):
        """Only reference is required; the rest default to None / 'biblical'."""
        c = Citation(reference="Jo 3:16")
        assert c.reference == "Jo 3:16"
        assert c.text is None
        assert c.page is None
        assert c.citation_type == "biblical"
        assert c.author is None
        assert c.work is None
        assert c.context is None

    def test_full_citation(self):
        c = Citation(
            reference="Rm 8:28",
            text="All things work together",
            page=42,
            citation_type="scholarly",
        )
        assert c.page == 42
        assert c.citation_type == "scholarly"

    def test_scholarly_fields(self):
        """Citation with scholarly fields should preserve author, work, and context."""
        c = Citation(
            reference="LEWIS, C.S.. Miracles. Bles. 1947",
            citation_type="scholarly",
            author="LEWIS, C.S.",
            work="Miracles",
            context="Reference about miracles",
        )
        assert c.author == "LEWIS, C.S."
        assert c.work == "Miracles"
        assert c.context == "Reference about miracles"
        assert c.citation_type == "scholarly"

    def test_scholarly_backward_compat(self):
        """Existing citations without author/work/context should still work."""
        c = Citation(reference="Jo 3:16", citation_type="biblical")
        assert c.author is None
        assert c.work is None
        assert c.context is None

    def test_scholarly_round_trip(self):
        """Scholarly Citation should survive serialization."""
        original = Citation(
            reference="FORSYTH, P.T.. This Life and the Next",
            citation_type="scholarly",
            author="FORSYTH, P.T.",
            work="This Life and the Next",
            context="Referenced for afterlife discussion",
        )
        data = original.model_dump()
        restored = Citation.model_validate(data)
        assert restored == original
        assert restored.author == "FORSYTH, P.T."
        assert restored.work == "This Life and the Next"


# ---------------------------------------------------------------------------
# 5. Thesis confidence bounds (0.0 - 1.0)
# ---------------------------------------------------------------------------

class TestThesisConfidence:
    def test_confidence_default(self):
        t = Thesis(id="T1", title="T", description="D")
        assert t.confidence == 0.8

    def test_confidence_at_boundaries(self):
        """Confidence of exactly 0.0 and 1.0 must be accepted."""
        t_low = Thesis(id="T1", title="T", description="D", confidence=0.0)
        t_high = Thesis(id="T2", title="T", description="D", confidence=1.0)
        assert t_low.confidence == 0.0
        assert t_high.confidence == 1.0

    def test_confidence_above_one_raises(self):
        with pytest.raises(ValidationError):
            Thesis(id="T1", title="T", description="D", confidence=1.1)

    def test_confidence_below_zero_raises(self):
        with pytest.raises(ValidationError):
            Thesis(id="T1", title="T", description="D", confidence=-0.01)


# ---------------------------------------------------------------------------
# 6. Thesis with citations list
# ---------------------------------------------------------------------------

class TestThesisWithCitations:
    def test_thesis_with_citations(self):
        """A Thesis can embed a list of Citation objects."""
        citations = [
            Citation(reference="Gn 1:1"),
            Citation(reference="Jo 1:1", text="In the beginning was the Word"),
        ]
        t = Thesis(
            id="T1.1.1",
            title="Creation",
            description="God created the heavens and the earth",
            thesis_type="main",
            chapter="Chapter 1",
            part="Part I",
            page_range="1-5",
            supporting_text="Supporting evidence here",
            citations=citations,
            confidence=0.95,
        )
        assert len(t.citations) == 2
        assert t.citations[0].reference == "Gn 1:1"
        assert t.citations[1].text == "In the beginning was the Word"
        assert t.thesis_type == "main"
        assert t.page_range == "1-5"


# ---------------------------------------------------------------------------
# 7. ThesisChain defaults and strength bounds
# ---------------------------------------------------------------------------

class TestThesisChain:
    def test_defaults(self):
        tc = ThesisChain(
            from_thesis_id="T1",
            to_thesis_id="T2",
            relationship="supports",
        )
        assert tc.reasoning_type == "deductive"
        assert tc.explanation == ""
        assert tc.strength == 0.7

    def test_strength_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            ThesisChain(
                from_thesis_id="T1",
                to_thesis_id="T2",
                relationship="supports",
                strength=1.5,
            )
        with pytest.raises(ValidationError):
            ThesisChain(
                from_thesis_id="T1",
                to_thesis_id="T2",
                relationship="supports",
                strength=-0.1,
            )

    def test_strength_at_boundaries(self):
        tc_low = ThesisChain(
            from_thesis_id="T1",
            to_thesis_id="T2",
            relationship="supports",
            strength=0.0,
        )
        tc_high = ThesisChain(
            from_thesis_id="T1",
            to_thesis_id="T2",
            relationship="derives_from",
            strength=1.0,
        )
        assert tc_low.strength == 0.0
        assert tc_high.strength == 1.0


# ---------------------------------------------------------------------------
# 8. ChapterAnalysis empty lists
# ---------------------------------------------------------------------------

class TestChapterAnalysis:
    def test_empty_lists_by_default(self):
        ca = ChapterAnalysis(chunk_title="Cap 1")
        assert ca.theses == []
        assert ca.citations == []

    def test_with_populated_lists(self):
        thesis = Thesis(id="T1", title="T", description="D")
        citation = Citation(reference="Mt 5:3")
        ca = ChapterAnalysis(
            chunk_title="Cap 2",
            theses=[thesis],
            citations=[citation],
        )
        assert len(ca.theses) == 1
        assert len(ca.citations) == 1


# ---------------------------------------------------------------------------
# 9. BookAnalysis with full nested data
# ---------------------------------------------------------------------------

class TestBookAnalysis:
    def test_empty_defaults(self):
        ba = BookAnalysis()
        assert ba.theses == []
        assert ba.chains == []
        assert ba.citations == []
        assert ba.summary == ""
        assert ba.argument_flow == ""

    def test_full_nested_data(self):
        """BookAnalysis can hold a complete analysis with nested objects."""
        citation = Citation(reference="Rm 1:20", page=10)
        thesis_a = Thesis(
            id="T1.1.1",
            title="Natural revelation",
            description="God is revealed through creation",
            citations=[citation],
            confidence=0.9,
        )
        thesis_b = Thesis(
            id="T1.1.2",
            title="Moral law",
            description="Moral law points to a lawgiver",
            confidence=0.85,
        )
        chain = ThesisChain(
            from_thesis_id="T1.1.1",
            to_thesis_id="T1.1.2",
            relationship="supports",
            reasoning_type="inductive",
            explanation="Natural revelation implies a moral lawgiver",
            strength=0.8,
        )
        ba = BookAnalysis(
            theses=[thesis_a, thesis_b],
            chains=[chain],
            citations=[citation],
            summary="An overview of Christian apologetics",
            argument_flow="From natural theology to moral argument",
        )
        assert len(ba.theses) == 2
        assert len(ba.chains) == 1
        assert ba.chains[0].from_thesis_id == "T1.1.1"
        assert ba.summary == "An overview of Christian apologetics"
        assert ba.theses[0].citations[0].reference == "Rm 1:20"


# ---------------------------------------------------------------------------
# 10. Serialization round-trip (model_dump -> model_validate)
# ---------------------------------------------------------------------------

class TestSerializationRoundTrip:
    def test_thesis_round_trip(self):
        """Dumping a Thesis to a dict and re-validating must reproduce it."""
        original = Thesis(
            id="T2.3.1",
            title="Incarnation",
            description="God became man",
            thesis_type="supporting",
            chapter="Cap 3",
            part="Part II",
            page_range="45-50",
            supporting_text="Key passage here",
            citations=[Citation(reference="Jo 1:14", text="The Word became flesh")],
            confidence=0.92,
        )
        data = original.model_dump()
        restored = Thesis.model_validate(data)
        assert restored == original
        assert restored.citations[0].reference == "Jo 1:14"

    def test_book_analysis_round_trip(self):
        """Full BookAnalysis survives a dump-and-validate cycle."""
        ba = BookAnalysis(
            theses=[
                Thesis(id="T1", title="A", description="B", confidence=0.5),
            ],
            chains=[
                ThesisChain(
                    from_thesis_id="T1",
                    to_thesis_id="T2",
                    relationship="elaborates",
                    strength=0.6,
                ),
            ],
            citations=[Citation(reference="Is 53:5")],
            summary="Summary text",
            argument_flow="Flow text",
        )
        data = ba.model_dump()
        restored = BookAnalysis.model_validate(data)
        assert restored == ba
        assert isinstance(data, dict)
        assert isinstance(data["theses"], list)
        assert data["theses"][0]["confidence"] == 0.5

    def test_extraction_result_round_trip(self):
        """ExtractionResult with pages survives serialization."""
        er = ExtractionResult(
            text="All text",
            pages=[PageText(page_number=1, text="Page one")],
            num_pages=1,
            total_chars=8,
            avg_chars_per_page=8.0,
            extraction_method="docling",
            is_digital_pdf=True,
        )
        data = er.model_dump()
        restored = ExtractionResult.model_validate(data)
        assert restored == er
        assert restored.pages[0].text == "Page one"


# ---------------------------------------------------------------------------
# 11. derive_part_from_id and derive_chapter_from_id
# ---------------------------------------------------------------------------

class TestDeriveFromId:
    """Tests for the derive_part_from_id and derive_chapter_from_id helpers."""

    @pytest.mark.parametrize(
        "thesis_id,expected",
        [
            ("T1.1.1", "Parte 1"),
            ("T2.5.1", "Parte 2"),
            ("T3.7.3", "Parte 3"),
            ("T4.9.2", "Parte 4"),
        ],
    )
    def test_derive_part_from_id(self, thesis_id, expected):
        assert derive_part_from_id(thesis_id) == expected

    @pytest.mark.parametrize(
        "thesis_id,expected",
        [
            ("T1.1.1", "Capitulo 1"),
            ("T2.5.1", "Capitulo 5"),
            ("T3.8.2", "Capitulo 8"),
            ("T4.11.1", "Capitulo 11"),
        ],
    )
    def test_derive_chapter_from_id(self, thesis_id, expected):
        assert derive_chapter_from_id(thesis_id) == expected

    def test_derive_part_unknown_part_number(self):
        """Part numbers outside 1-4 return empty string."""
        assert derive_part_from_id("T5.1.1") == ""

    def test_derive_from_invalid_id(self):
        """Non-matching IDs return empty string."""
        assert derive_part_from_id("invalid") == ""
        assert derive_chapter_from_id("invalid") == ""
        assert derive_part_from_id("") == ""
        assert derive_chapter_from_id("") == ""

    def test_derive_part_used_as_fallback(self):
        """When t.part is empty, derive_part_from_id serves as fallback."""
        t = Thesis(id="T2.5.1", title="Test", description="D", part="")
        effective_part = t.part or derive_part_from_id(t.id)
        assert effective_part == "Parte 2"

    def test_derive_chapter_used_as_fallback(self):
        """When t.chapter is empty, derive_chapter_from_id serves as fallback."""
        t = Thesis(id="T3.8.1", title="Test", description="D", chapter="")
        effective_chapter = t.chapter or derive_chapter_from_id(t.id)
        assert effective_chapter == "Capitulo 8"
