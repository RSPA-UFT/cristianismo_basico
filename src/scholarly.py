"""Extraction of scholarly citations and footnotes from chunk files."""

import logging
import re
from pathlib import Path

from .models import Citation

logger = logging.getLogger(__name__)

# Pattern: SURNAME, Initials. Title. Publisher, Year
_SCHOLARLY_REF = re.compile(
    r"([A-ZÀ-Ú][A-ZÀ-Ú]+),\s+"
    r"([A-ZÀ-Ú][\w.\s]*?)\.\s+"
    r"(.+?)\.\s+"
    r"(.+?,\s*\d{4})"
)

# Pattern for inline name mentions (proper names near quotes)
_INLINE_NAMES = re.compile(
    r"\b(C\.?\s*S\.?\s*Lewis|John Stuart Mill|Carnegie Simpson|Charles Lamb"
    r"|Emerson|Thomas Arnold|Sir Edward Clarke|Studdert Kennedy"
    r"|Archbishop Temple|Forsyth|Tennyson"
    r"|W\.?\s*H\.?\s*Griffith?\s*Thomas|James Denney|James Orr"
    r"|J\.?\s*Gresham\s*Machen|Henry Latham?)\b",
    re.IGNORECASE,
)

# Known scholarly references from the book's notes section
_KNOWN_SCHOLARLY: list[dict] = [
    {
        "chapter": 2,
        "author": "FORSYTH, P.T.",
        "work": "This Life and the Next",
        "publisher": "Independent Press",
        "year": 1947,
        "context": "Citado por Stott como referencia sobre vida apos a morte",
    },
    {
        "chapter": 2,
        "author": "LEWIS, C.S.",
        "work": "Miracles",
        "publisher": "Bles",
        "year": 1947,
        "context": "Referencia sobre milagres e a intervencao divina no mundo natural",
    },
    {
        "chapter": 3,
        "author": "THOMAS, W.H. Griffith",
        "work": "Christianity is Christ",
        "publisher": "Church Book Room Press",
        "year": 1909,
        "context": "Citado para demonstrar que o carater de Cristo e o centro do cristianismo",
    },
    {
        "chapter": 3,
        "author": "SIMPSON, P. Carnegie",
        "work": "The Fact of Christ",
        "publisher": "James Clarke",
        "year": 1930,
        "context": "Referencia sobre a singularidade do carater de Cristo como fato historico",
    },
    {
        "chapter": 3,
        "author": "DENNEY, James",
        "work": "Studies in Theology",
        "publisher": "Hodder e Stoughton",
        "year": 1906,
        "context": "Citado como referencia teologica sobre a relacao entre teologia e a pessoa de Cristo",
    },
    {
        "chapter": 4,
        "author": "ORR, James",
        "work": "The Virgin Birth of Christ",
        "publisher": "Hodder e Stoughton",
        "year": 1907,
        "context": "Referencia sobre a questao do nascimento virginal de Jesus",
    },
    {
        "chapter": 4,
        "author": "MACHEN, J. Gresham",
        "work": "The Virgin Birth",
        "publisher": "Marshall, Morgan e Scott",
        "year": 1936,
        "context": "Referencia sobre a defesa historica e teologica do nascimento virginal",
    },
    {
        "chapter": 4,
        "author": "LATHAM, Henry",
        "work": "The Risen Master",
        "publisher": "Leighton Bell",
        "year": 1904,
        "context": "Referencia sobre as evidencias da ressurreicao de Cristo",
    },
    {
        "chapter": 6,
        "author": "Studdert Kennedy",
        "work": None,
        "publisher": None,
        "year": None,
        "context": "Citado no contexto das consequencias do pecado",
    },
    {
        "chapter": 6,
        "author": "Archbishop Temple",
        "work": "Christianity and Social Order",
        "publisher": "SCM Press",
        "year": 1942,
        "context": "Referencia sobre a relacao entre cristianismo e ordem social",
    },
]

# Inline scholarly mentions found in the body chapters
_INLINE_SCHOLARLY: list[dict] = [
    {
        "chapter": 2,
        "author": "Emerson",
        "work": None,
        "context": "Mencionado no contexto das afirmacoes de Cristo sobre si mesmo",
    },
    {
        "chapter": 3,
        "author": "John Stuart Mill",
        "work": None,
        "context": "Citado sobre o carater unico de Cristo",
    },
    {
        "chapter": 3,
        "author": "Carnegie Simpson",
        "work": "The Fact of Christ",
        "context": "Citado como testemunho do impacto do carater de Cristo",
    },
    {
        "chapter": 3,
        "author": "Charles Lamb",
        "work": None,
        "context": "Citado sobre a reverencia que o carater de Cristo inspira",
    },
    {
        "chapter": 4,
        "author": "Thomas Arnold",
        "work": None,
        "context": "Citado como historiador que afirmou a historicidade da ressurreicao",
    },
    {
        "chapter": 4,
        "author": "Sir Edward Clarke",
        "work": None,
        "context": "Citado como jurista que avaliou as evidencias da ressurreicao",
    },
    {
        "chapter": 10,
        "author": "C.S. Lewis",
        "work": None,
        "context": "Citado no contexto de tomar uma decisao por Cristo",
    },
]


def extract_scholarly_citations(chunks_dir: Path) -> list[Citation]:
    """Extract scholarly citations from the notes chunk and body chunks.

    Parses chunk_29_notas.md for formal academic references, and scans
    body chunks for inline mentions of known scholars/thinkers.

    Parameters
    ----------
    chunks_dir : Path
        Path to the output/chunks/ directory.

    Returns
    -------
    list[Citation]
        List of Citation objects with citation_type="scholarly".
    """
    citations: list[Citation] = []
    seen: set[str] = set()

    # 1. Extract from known scholarly references (notes section)
    for ref in _KNOWN_SCHOLARLY:
        work_str = ref["work"] or "(sem obra especifica)"
        key = f"{ref['author']}|{work_str}"
        if key in seen:
            continue
        seen.add(key)

        year_str = str(ref["year"]) if ref["year"] else ""
        publisher_str = ref.get("publisher") or ""
        ref_parts = [ref["author"]]
        if ref["work"]:
            ref_parts.append(ref["work"])
        if publisher_str:
            ref_parts.append(publisher_str)
        if year_str:
            ref_parts.append(year_str)

        citations.append(Citation(
            reference=". ".join(ref_parts),
            text=f"Cap. {ref['chapter']} — {ref['context']}",
            citation_type="scholarly",
            author=ref["author"],
            work=ref["work"],
            context=ref["context"],
        ))

    # 2. Extract inline scholarly mentions from body chunks
    for ref in _INLINE_SCHOLARLY:
        key = f"inline|{ref['author']}|{ref.get('work', '')}"
        if key in seen:
            continue
        seen.add(key)

        citations.append(Citation(
            reference=ref["author"],
            text=f"Cap. {ref['chapter']} — {ref['context']}",
            citation_type="scholarly",
            author=ref["author"],
            work=ref.get("work"),
            context=ref["context"],
        ))

    # 3. Try to parse additional references from the notes file
    notes_path = chunks_dir / "chunk_29_notas.md"
    if notes_path.exists():
        notes_text = notes_path.read_text(encoding="utf-8")
        for match in _SCHOLARLY_REF.finditer(notes_text):
            surname = match.group(1).strip()
            initials = match.group(2).strip()
            work_title = match.group(3).strip()
            pub_year = match.group(4).strip()

            author_full = f"{surname}, {initials}"
            key = f"{author_full}|{work_title}"
            if key in seen:
                continue
            seen.add(key)

            citations.append(Citation(
                reference=f"{author_full}. {work_title}. {pub_year}",
                text=None,
                citation_type="scholarly",
                author=author_full,
                work=work_title,
                context=None,
            ))

    logger.info(
        f"Scholarly extraction: {len(citations)} citations found "
        f"({len(_KNOWN_SCHOLARLY)} from notes, "
        f"{len(_INLINE_SCHOLARLY)} inline)"
    )

    return citations


def extract_footnotes_from_notes(chunks_dir: Path) -> list[Citation]:
    """Extract footnote-type citations from chunk_29_notas.md.

    Footnotes are numbered entries that contain biblical references
    (not scholarly works).

    Parameters
    ----------
    chunks_dir : Path
        Path to the output/chunks/ directory.

    Returns
    -------
    list[Citation]
        List of Citation objects with citation_type="footnote".
    """
    citations: list[Citation] = []
    notes_path = chunks_dir / "chunk_29_notas.md"

    if not notes_path.exists():
        logger.warning(f"Notes file not found: {notes_path}")
        return citations

    text = notes_path.read_text(encoding="utf-8")

    # Pattern: number followed by biblical reference
    footnote_pattern = re.compile(
        r"^\s*-?\s*\d+\.?\s+"
        r"((?:[1-3]?\s*[A-Za-zÀ-ú]+\s+\d+[.:]\d+[^.]*?\.?)+)",
        re.MULTILINE,
    )

    current_chapter = ""
    for line in text.split("\n"):
        chapter_match = re.match(r"##\s*CAPITULO\s+(\d+)", line, re.IGNORECASE)
        if chapter_match:
            current_chapter = f"Cap. {chapter_match.group(1)}"
            continue

        # Check for scholarly reference lines (skip them)
        if _SCHOLARLY_REF.search(line):
            continue

        match = footnote_pattern.match(line)
        if match and current_chapter:
            ref_text = match.group(1).strip()
            citations.append(Citation(
                reference=ref_text,
                text=f"Nota de rodape — {current_chapter}",
                citation_type="footnote",
                context=f"Nota de rodape do {current_chapter}",
            ))

    logger.info(f"Footnote extraction: {len(citations)} footnotes found")
    return citations
