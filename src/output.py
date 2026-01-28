"""JSON and Markdown formatters for saving results."""

import json
import logging
from collections import defaultdict
from pathlib import Path

from .config import Settings
from .models import BookAnalysis, ChapterAnalysis, ChunkInfo, ExtractionResult

logger = logging.getLogger(__name__)


class OutputWriter:
    """Saves intermediary and final results to output/."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        settings.ensure_output_dirs()

    def save_extracted_text(self, result: ExtractionResult) -> Path:
        path = self.settings.output_dir / "extracted_text.md"
        header = (
            f"# Texto Extraido: Cristianismo Basico\n\n"
            f"- **Metodo:** {result.extraction_method}\n"
            f"- **Paginas:** {result.num_pages}\n"
            f"- **Total caracteres:** {result.total_chars:,}\n"
            f"- **Media chars/pagina:** {result.avg_chars_per_page:.0f}\n\n"
            f"---\n\n"
        )
        path.write_text(header + result.text, encoding="utf-8")
        logger.info(f"Saved extracted text to {path}")
        return path

    def save_chunks(self, chunks: list[ChunkInfo]) -> list[Path]:
        paths = []
        for chunk in chunks:
            # Sanitize filename
            safe_name = (
                chunk.title.lower()
                .replace(" ", "_")
                .replace("/", "_")
                .replace("\\", "_")
            )
            safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-.")
            filename = f"chunk_{chunk.index:02d}_{safe_name[:50]}.md"
            path = self.settings.chunks_dir / filename

            header = (
                f"# {chunk.title}\n\n"
                f"- **Indice:** {chunk.index}\n"
                f"- **Parte:** {chunk.part or 'N/A'}\n"
                f"- **Capitulo:** {chunk.chapter or 'N/A'}\n"
                f"- **Caracteres:** {chunk.char_count:,}\n"
                f"- **Fonte:** {chunk.source}\n\n"
                f"---\n\n"
            )
            path.write_text(header + chunk.text, encoding="utf-8")
            paths.append(path)

        logger.info(f"Saved {len(paths)} chunks to {self.settings.chunks_dir}")
        return paths

    def save_chapter_analysis(self, analysis: ChapterAnalysis, index: int) -> Path:
        filename = f"chapter_{index:02d}_theses.json"
        path = self.settings.per_chapter_dir / filename
        data = analysis.model_dump(mode="json")
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"Saved chapter analysis to {path}")
        return path

    def save_book_analysis(self, analysis: BookAnalysis) -> dict[str, Path]:
        """Save all final analysis files and return their paths."""
        paths = {}

        # theses.json
        theses_path = self.settings.output_dir / "theses.json"
        theses_data = [t.model_dump(mode="json") for t in analysis.theses]
        theses_path.write_text(
            json.dumps(theses_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["theses"] = theses_path

        # chains.json
        chains_path = self.settings.output_dir / "chains.json"
        chains_data = [c.model_dump(mode="json") for c in analysis.chains]
        chains_path.write_text(
            json.dumps(chains_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["chains"] = chains_path

        # citations.json
        citations_path = self.settings.output_dir / "citations.json"
        citations_data = [c.model_dump(mode="json") for c in analysis.citations]
        citations_path.write_text(
            json.dumps(citations_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        paths["citations"] = citations_path

        # report.md
        report_path = self.settings.output_dir / "report.md"
        report_path.write_text(
            self._generate_report(analysis), encoding="utf-8"
        )
        paths["report"] = report_path

        logger.info(f"Saved final analysis to {self.settings.output_dir}")
        return paths

    def save_citation_correlation(self, correlation: dict) -> Path:
        path = self.settings.output_dir / "citation_groups.json"
        path.write_text(
            json.dumps(correlation, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"Saved citation correlation to {path}")
        return path

    def _generate_report(self, analysis: BookAnalysis) -> str:
        """Generate a human-readable Markdown report."""
        lines = [
            "# Relatorio de Analise: Cristianismo Basico",
            "",
            "**Autor:** John Stott",
            f"**Teses identificadas:** {len(analysis.theses)}",
            f"**Cadeias logicas:** {len(analysis.chains)}",
            f"**Citacoes biblicas:** {len(analysis.citations)}",
            "",
            "---",
            "",
            "## Resumo Executivo",
            "",
            analysis.summary or "(Resumo nao disponivel)",
            "",
            "---",
            "",
            "## Fluxo Argumentativo",
            "",
            analysis.argument_flow or "(Fluxo nao disponivel)",
            "",
            "---",
            "",
            "## Teses por Capitulo",
            "",
        ]

        # Group theses by chapter
        by_chapter: dict[str, list] = defaultdict(list)
        for t in analysis.theses:
            key = t.chapter or t.part or "Geral"
            by_chapter[key].append(t)

        for chapter, theses in by_chapter.items():
            lines.append(f"### {chapter}")
            lines.append("")
            for t in theses:
                type_badge = f"[{t.thesis_type.upper()}]"
                confidence_pct = f"{t.confidence * 100:.0f}%"
                lines.append(f"- **{t.id}** {type_badge} {t.title} (confianca: {confidence_pct})")
                lines.append(f"  > {t.description}")
                if t.supporting_text:
                    lines.append(f'  > _"{t.supporting_text}"_')
                if t.citations:
                    refs = ", ".join(c.reference for c in t.citations)
                    lines.append(f"  > Citacoes: {refs}")
                lines.append("")

        # Chain graph (textual)
        if analysis.chains:
            lines.extend([
                "---",
                "",
                "## Grafo de Encadeamento",
                "",
            ])
            for chain in analysis.chains:
                arrow = "→" if chain.relationship != "contradicts" else "⇌"
                lines.append(
                    f"- **{chain.from_thesis_id}** {arrow} **{chain.to_thesis_id}** "
                    f"({chain.relationship}, {chain.reasoning_type}): "
                    f"{chain.explanation}"
                )
            lines.append("")

        # Citation index by biblical book
        if analysis.citations:
            lines.extend([
                "---",
                "",
                "## Indice de Citacoes por Livro Biblico",
                "",
            ])
            by_book: dict[str, list[str]] = defaultdict(list)
            for c in analysis.citations:
                if c.citation_type == "biblical":
                    # Extract book name (first word/abbreviation)
                    parts = c.reference.split()
                    book = parts[0] if parts else c.reference
                    # Handle "1Jo", "2Co" etc.
                    if len(parts) > 1 and parts[0] in ("1", "2", "3"):
                        book = parts[0] + parts[1]
                    by_book[book].append(c.reference)

            for book in sorted(by_book.keys()):
                refs = ", ".join(sorted(set(by_book[book])))
                lines.append(f"- **{book}:** {refs}")
            lines.append("")

        # Scholarly citations section
        scholarly_citations = [
            c for c in analysis.citations if c.citation_type == "scholarly"
        ]
        if scholarly_citations:
            lines.extend([
                "---",
                "",
                "## Citacoes Academicas",
                "",
            ])
            # Group by author
            by_author: dict[str, list] = defaultdict(list)
            for c in scholarly_citations:
                author_key = c.author or c.reference
                by_author[author_key].append(c)

            for author in sorted(by_author.keys()):
                refs = by_author[author]
                first = refs[0]
                work_str = f" — *{first.work}*" if first.work else ""
                context_str = f": {first.context}" if first.context else ""
                lines.append(f"- **{author}**{work_str}{context_str}")
                # If multiple entries by same author with different works
                for ref in refs[1:]:
                    w = f" — *{ref.work}*" if ref.work else ""
                    ctx = f": {ref.context}" if ref.context else ""
                    lines.append(f"  - {ref.reference}{w}{ctx}")
            lines.append("")

        # Statistics
        lines.extend([
            "---",
            "",
            "## Estatisticas",
            "",
            f"| Metrica | Valor |",
            f"|---------|-------|",
            f"| Total de teses | {len(analysis.theses)} |",
            f"| Teses principais (main) | {sum(1 for t in analysis.theses if t.thesis_type == 'main')} |",
            f"| Teses de suporte | {sum(1 for t in analysis.theses if t.thesis_type == 'supporting')} |",
            f"| Premissas | {sum(1 for t in analysis.theses if t.thesis_type == 'premise')} |",
            f"| Conclusoes | {sum(1 for t in analysis.theses if t.thesis_type == 'conclusion')} |",
            f"| Cadeias logicas | {len(analysis.chains)} |",
            f"| Citacoes biblicas | {sum(1 for c in analysis.citations if c.citation_type == 'biblical')} |",
            f"| Citacoes academicas | {sum(1 for c in analysis.citations if c.citation_type == 'scholarly')} |",
            f"| Notas de rodape | {sum(1 for c in analysis.citations if c.citation_type == 'footnote')} |",
            "",
        ])

        return "\n".join(lines)
