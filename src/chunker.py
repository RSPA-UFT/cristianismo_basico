"""Hierarchical chunking by chapter/section with metadata."""

import logging
import re

from .models import ChunkInfo, ExtractionResult

logger = logging.getLogger(__name__)

# Markdown heading pattern (from Docling output — all are ##)
MARKDOWN_HEADING_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)

# Known chapter-level headings from the book's SUMARIO (table of contents).
# These are the primary split points — everything else is a sub-section.
CHAPTER_TITLES = [
    "PREFACIO",
    "A ABORDAGEM CORRETA",               # Cap 1
    "AS AFIRMACOES DE CRISTO",            # Cap 2
    "O CARATER DE CRISTO",                # Cap 3
    "A RESSURREICAO DE CRISTO",           # Cap 4
    "A REALIDADE E A NATUREZA DO PECADO", # Cap 5
    "AS CONSEQUENCIAS DOPECADO",          # Cap 6 (OCR artifact: no space)
    "AS CONSEQUENCIAS DO PECADO",         # Cap 6 (clean)
    "A MORTE DE CRISTO",                  # Cap 7
    "A SALVACAO EM CRISTO",               # Cap 8
    "CALCULANDO O CUSTO",                 # Cap 9
    "TOMANDO UMA DECISAO",                # Cap 10
    "SENDO UM CRISTAO",                   # Cap 11
    "NoTAS",                              # Notes section (OCR artifact)
    "NOTAS",                              # Notes section (clean)
]

# Part headings (these mark part boundaries but are merged into the next chapter)
PART_PATTERNS = [
    re.compile(r"(?i)^PARTE\s+(UM|DOIS|TRES|TR[EÊ]S|QUATRO|[1-4IVX]+)\b"),
]

# Regex fallback patterns (for PyMuPDF/OCR raw text)
FALLBACK_CHAPTER_PATTERNS = [
    re.compile(r"(?i)(PARTE\s+[1-4IVX]+[^\n]*)"),
    re.compile(r"(?i)(CAP[IÍ]TULO\s+\d+[^\n]*)"),
    re.compile(r"(?i)(PREF[AÁ]CIO[^\n]*)"),
    re.compile(r"(?i)(INTRODU[CÇ][AÃ]O[^\n]*)"),
    re.compile(r"(?i)(CONCLUS[AÃ]O[^\n]*)"),
    re.compile(r"(?i)(AP[EÊ]NDICE[^\n]*)"),
]

MAX_CHUNK_SIZE = 12000
OVERLAP_CHARS = 500

# Map chapter titles to (part_name, chapter_name, part_index, chapter_index)
CHAPTER_MAP = {
    "PREFACIO": ("", "Prefacio", 0, 0),
    "A ABORDAGEM CORRETA": ("Parte 1 - A Pessoa de Cristo", "Cap 1 - A Abordagem Correta", 1, 1),
    "AS AFIRMACOES DE CRISTO": ("Parte 1 - A Pessoa de Cristo", "Cap 2 - As Afirmacoes de Cristo", 1, 2),
    "O CARATER DE CRISTO": ("Parte 1 - A Pessoa de Cristo", "Cap 3 - O Carater de Cristo", 1, 3),
    "A RESSURREICAO DE CRISTO": ("Parte 1 - A Pessoa de Cristo", "Cap 4 - A Ressurreicao de Cristo", 1, 4),
    "A REALIDADE E A NATUREZA DO PECADO": ("Parte 2 - A Necessidade do Homem", "Cap 5 - A Realidade e a Natureza do Pecado", 2, 5),
    "AS CONSEQUENCIAS DOPECADO": ("Parte 2 - A Necessidade do Homem", "Cap 6 - As Consequencias do Pecado", 2, 6),
    "AS CONSEQUENCIAS DO PECADO": ("Parte 2 - A Necessidade do Homem", "Cap 6 - As Consequencias do Pecado", 2, 6),
    "A MORTE DE CRISTO": ("Parte 3 - A Obra de Cristo", "Cap 7 - A Morte de Cristo", 3, 7),
    "A SALVACAO EM CRISTO": ("Parte 3 - A Obra de Cristo", "Cap 8 - A Salvacao em Cristo", 3, 8),
    "CALCULANDO O CUSTO": ("Parte 4 - A Resposta do Homem", "Cap 9 - Calculando o Custo", 4, 9),
    "TOMANDO UMA DECISAO": ("Parte 4 - A Resposta do Homem", "Cap 10 - Tomando uma Decisao", 4, 10),
    "SENDO UM CRISTAO": ("Parte 4 - A Resposta do Homem", "Cap 11 - Sendo um Cristao", 4, 11),
    "NoTAS": ("", "Notas", 0, 99),
    "NOTAS": ("", "Notas", 0, 99),
}


def _normalize_title(title: str) -> str:
    """Normalize a heading for comparison: uppercase, strip spaces, remove OCR artifacts."""
    return re.sub(r"\s+", " ", title.strip().upper())


def _is_chapter_heading(title: str) -> bool:
    """Check if a heading is a chapter-level boundary."""
    normalized = _normalize_title(title)
    for ch_title in CHAPTER_TITLES:
        if _normalize_title(ch_title) == normalized:
            return True
    # Also match "PARTE ..." headings
    for pat in PART_PATTERNS:
        if pat.match(title.strip()):
            return True
    return False


class HierarchicalChunker:
    """Splits extracted text into chapter/section chunks."""

    def chunk(self, extraction: ExtractionResult) -> list[ChunkInfo]:
        if extraction.extraction_method == "docling":
            chunks = self._chunk_by_markdown(extraction.text)
        else:
            chunks = self._chunk_by_regex(extraction.text)

        if not chunks:
            logger.warning("No chapters detected, treating entire text as single chunk")
            chunks = [
                ChunkInfo(
                    index=0,
                    title="Texto Completo",
                    text=extraction.text,
                    char_count=len(extraction.text),
                    source="single_chunk",
                )
            ]

        # Sub-divide oversized chunks
        final_chunks = []
        for chunk in chunks:
            if chunk.char_count > MAX_CHUNK_SIZE:
                sub_chunks = self._subdivide(chunk)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        # Re-index
        for i, c in enumerate(final_chunks):
            c.index = i

        logger.info(f"Created {len(final_chunks)} chunks from text")
        return final_chunks

    def _chunk_by_markdown(self, text: str) -> list[ChunkInfo]:
        """Split by known chapter headings in Markdown, grouping sub-sections."""
        headings = list(MARKDOWN_HEADING_PATTERN.finditer(text))

        if not headings:
            logger.info("No Markdown headings found, falling back to regex")
            return self._chunk_by_regex(text)

        # Find chapter-level boundaries
        chapter_boundaries: list[tuple[int, str]] = []
        front_matter_end = 0

        for match in headings:
            title = match.group(1).strip()

            if _is_chapter_heading(title):
                chapter_boundaries.append((match.start(), title))
            elif not chapter_boundaries:
                # Track end of front matter (before first chapter heading)
                front_matter_end = match.start()

        if not chapter_boundaries:
            logger.info("No chapter headings matched, falling back to regex")
            return self._chunk_by_regex(text)

        chunks: list[ChunkInfo] = []

        # Front matter (before first chapter): skip or include as intro
        if chapter_boundaries[0][0] > 500:
            front_text = text[: chapter_boundaries[0][0]].strip()
            if len(front_text) > 200:
                chunks.append(
                    ChunkInfo(
                        index=0,
                        title="Material Introdutorio",
                        part="",
                        chapter="Introducao",
                        text=front_text,
                        char_count=len(front_text),
                        source="markdown_heading",
                    )
                )

        # Build chapter chunks
        current_part = ""
        for i, (start, title) in enumerate(chapter_boundaries):
            end = (
                chapter_boundaries[i + 1][0]
                if i + 1 < len(chapter_boundaries)
                else len(text)
            )
            chunk_text = text[start:end].strip()

            # Check if this is a PARTE heading — merge into next chapter
            is_part = any(pat.match(title.strip()) for pat in PART_PATTERNS)
            if is_part:
                current_part = title.strip()
                # Don't create a separate chunk for PARTE headings;
                # their text will be included in the next chapter chunk
                continue

            # Look up structured metadata
            normalized = _normalize_title(title)
            part_name = current_part
            chapter_name = title
            p_idx: int | None = None
            c_idx: int | None = None

            for ch_title, (p, c, pi, ci) in CHAPTER_MAP.items():
                if _normalize_title(ch_title) == normalized:
                    if p:
                        part_name = p
                    chapter_name = c
                    p_idx = pi
                    c_idx = ci
                    break

            chunks.append(
                ChunkInfo(
                    index=len(chunks),
                    title=chapter_name,
                    part=part_name,
                    chapter=chapter_name,
                    part_index=p_idx,
                    chapter_index=c_idx,
                    text=chunk_text,
                    char_count=len(chunk_text),
                    source="markdown_heading",
                )
            )

        return chunks

    def _chunk_by_regex(self, text: str) -> list[ChunkInfo]:
        """Split by chapter/part regex patterns (PyMuPDF/OCR fallback)."""
        boundaries: list[tuple[int, str]] = []

        for pattern in FALLBACK_CHAPTER_PATTERNS:
            for match in pattern.finditer(text):
                boundaries.append((match.start(), match.group(1).strip()))

        if not boundaries:
            return []

        boundaries.sort(key=lambda x: x[0])

        # Deduplicate boundaries that are too close together (< 50 chars apart)
        deduped: list[tuple[int, str]] = [boundaries[0]]
        for pos, title in boundaries[1:]:
            if pos - deduped[-1][0] > 50:
                deduped.append((pos, title))
        boundaries = deduped

        chunks: list[ChunkInfo] = []
        current_part = ""

        for i, (start, title) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            chunk_text = text[start:end].strip()

            title_upper = title.upper()
            if "PARTE" in title_upper:
                current_part = title

            chunks.append(
                ChunkInfo(
                    index=i,
                    title=title,
                    part=current_part,
                    chapter=title if "PARTE" not in title_upper else "",
                    text=chunk_text,
                    char_count=len(chunk_text),
                    source="regex_fallback",
                )
            )

        return chunks

    def _subdivide(self, chunk: ChunkInfo) -> list[ChunkInfo]:
        """Split an oversized chunk into sub-chunks with overlap."""
        paragraphs = chunk.text.split("\n\n")
        sub_chunks: list[ChunkInfo] = []
        current_text = ""
        sub_index = 0

        for para in paragraphs:
            if len(current_text) + len(para) > MAX_CHUNK_SIZE and current_text:
                sub_chunks.append(
                    ChunkInfo(
                        index=0,
                        title=f"{chunk.title} (parte {sub_index + 1})",
                        part=chunk.part,
                        chapter=chunk.chapter,
                        part_index=chunk.part_index,
                        chapter_index=chunk.chapter_index,
                        text=current_text.strip(),
                        char_count=len(current_text.strip()),
                        source=chunk.source,
                    )
                )
                overlap = (
                    current_text[-OVERLAP_CHARS:]
                    if len(current_text) > OVERLAP_CHARS
                    else ""
                )
                current_text = overlap + "\n\n" + para
                sub_index += 1
            else:
                current_text += "\n\n" + para if current_text else para

        if current_text.strip():
            sub_chunks.append(
                ChunkInfo(
                    index=0,
                    title=(
                        f"{chunk.title} (parte {sub_index + 1})"
                        if sub_index > 0
                        else chunk.title
                    ),
                    part=chunk.part,
                    chapter=chunk.chapter,
                    part_index=chunk.part_index,
                    chapter_index=chunk.chapter_index,
                    text=current_text.strip(),
                    char_count=len(current_text.strip()),
                    source=chunk.source,
                )
            )

        return sub_chunks
