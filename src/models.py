"""Pydantic models for thesis extraction and analysis."""

import re

from pydantic import BaseModel, Field

_PART_NAMES = {
    1: "Parte 1",
    2: "Parte 2",
    3: "Parte 3",
    4: "Parte 4",
}

_ID_RE = re.compile(r"^T(\d+)\.(\d+)\.")


def derive_part_from_id(thesis_id: str) -> str:
    """Derive the part name from a thesis ID like ``T1.2.3``.

    Returns e.g. ``"Parte 1"`` or ``""`` if the pattern does not match.
    """
    m = _ID_RE.match(thesis_id)
    if m:
        return _PART_NAMES.get(int(m.group(1)), "")
    return ""


def derive_chapter_from_id(thesis_id: str) -> str:
    """Derive a chapter label from a thesis ID like ``T1.2.3``.

    Returns e.g. ``"Capitulo 2"`` or ``""`` if the pattern does not match.
    """
    m = _ID_RE.match(thesis_id)
    if m:
        return f"Capitulo {m.group(2)}"
    return ""


# --- Extraction models ---

class PageText(BaseModel):
    page_number: int
    text: str


class ExtractionResult(BaseModel):
    text: str
    pages: list[PageText] = Field(default_factory=list)
    num_pages: int = 0
    total_chars: int = 0
    avg_chars_per_page: float = 0.0
    extraction_method: str = ""  # "docling", "pymupdf", "tesseract"
    is_digital_pdf: bool = False


# --- Chunk models ---

class ChunkInfo(BaseModel):
    index: int
    title: str  # e.g. "Capitulo 1 - O Argumento Cristao"
    part: str = ""
    chapter: str = ""
    part_index: int | None = None      # e.g. 1 for "Parte 1"
    chapter_index: int | None = None   # e.g. 2 for "Cap 2"
    text: str
    char_count: int = 0
    page_range: str | None = None
    source: str = ""  # "markdown_heading" or "regex_fallback"


# --- Analysis models ---

class Citation(BaseModel):
    reference: str  # "Jo 3:16"
    text: str | None = None
    page: int | None = None
    citation_type: str = "biblical"  # "biblical", "scholarly", "footnote"
    author: str | None = None    # e.g. "C.S. Lewis" (scholarly citations)
    work: str | None = None      # e.g. "Miracles" (scholarly citations)
    context: str | None = None   # How Stott uses the reference


class Thesis(BaseModel):
    id: str  # "T1.2.3" (Part.Chapter.Number)
    title: str
    description: str
    thesis_type: str = "main"  # "main", "supporting", "premise", "conclusion"
    chapter: str = ""
    part: str = ""
    page_range: str | None = None
    supporting_text: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ThesisChain(BaseModel):
    from_thesis_id: str
    to_thesis_id: str
    relationship: str  # "supports", "derives_from", "elaborates", "precedes", "contradicts"
    reasoning_type: str = "deductive"  # "deductive", "inductive", "abductive"
    explanation: str = ""
    strength: float = Field(default=0.7, ge=0.0, le=1.0)


class ChapterAnalysis(BaseModel):
    """Result of analyzing a single chunk/chapter."""
    chunk_title: str
    theses: list[Thesis] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class BookAnalysis(BaseModel):
    """Complete analysis of the book."""
    theses: list[Thesis] = Field(default_factory=list)
    chains: list[ThesisChain] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    summary: str = ""
    argument_flow: str = ""
