"""PDF report generator for the theological analysis.

Generates a print-ready HTML file optimized for PDF rendering.
If weasyprint is available, renders directly to PDF A4.
Otherwise, produces an HTML file suitable for Ctrl+P browser printing.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from .models import BookAnalysis, Citation, Thesis

logger = logging.getLogger(__name__)


def _build_html(analysis: BookAnalysis) -> str:
    """Build a print-optimized HTML string from a BookAnalysis."""
    scholarly = [c for c in analysis.citations if c.citation_type == "scholarly"]
    biblical = [c for c in analysis.citations if c.citation_type == "biblical"]

    # Group theses by part then chapter
    by_part: dict[str, dict[str, list[Thesis]]] = defaultdict(lambda: defaultdict(list))
    for t in analysis.theses:
        part_key = t.part or "Geral"
        ch_key = t.chapter or "Geral"
        by_part[part_key][ch_key].append(t)

    # Build thesis sections
    thesis_sections = []
    for part, chapters in by_part.items():
        thesis_sections.append(f'<h2 class="part-title">{_esc(part)}</h2>')
        for chapter, theses in chapters.items():
            thesis_sections.append(f'<h3 class="chapter-title">{_esc(chapter)}</h3>')
            for t in theses:
                badge = t.thesis_type.upper()
                conf = f"{t.confidence * 100:.0f}%"
                refs = ", ".join(c.reference for c in t.citations) if t.citations else ""
                thesis_sections.append(f"""
                <div class="thesis">
                  <div class="thesis-header">
                    <span class="thesis-id">{_esc(t.id)}</span>
                    <span class="badge badge-{t.thesis_type}">{badge}</span>
                    <span class="thesis-title">{_esc(t.title)}</span>
                    <span class="confidence">({conf})</span>
                  </div>
                  <p class="description">{_esc(t.description)}</p>
                  {f'<blockquote>{_esc(t.supporting_text)}</blockquote>' if t.supporting_text else ''}
                  {f'<p class="refs">Citacoes: {_esc(refs)}</p>' if refs else ''}
                </div>
                """)

    # Build citation index
    by_book: dict[str, list[str]] = defaultdict(list)
    for c in biblical:
        parts = c.reference.split()
        book = parts[0] if parts else c.reference
        if len(parts) > 1 and parts[0] in ("1", "2", "3"):
            book = parts[0] + parts[1]
        by_book[book].append(c.reference)

    citation_rows = []
    for book in sorted(by_book.keys()):
        refs = ", ".join(sorted(set(by_book[book])))
        citation_rows.append(f"<tr><td><strong>{_esc(book)}</strong></td><td>{_esc(refs)}</td></tr>")

    # Scholarly section
    scholarly_items = []
    for c in scholarly:
        author = c.author or c.reference
        work = f" &mdash; <em>{_esc(c.work)}</em>" if c.work else ""
        ctx = f": {_esc(c.context)}" if c.context else ""
        scholarly_items.append(f"<li><strong>{_esc(author)}</strong>{work}{ctx}</li>")

    # Statistics
    type_counts = defaultdict(int)
    for t in analysis.theses:
        type_counts[t.thesis_type] += 1

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatorio: Cristianismo Basico - John Stott</title>
<style>
  @page {{ size: A4; margin: 2cm; }}
  @media print {{
    .no-print {{ display: none; }}
    body {{ font-size: 10pt; }}
    h1 {{ font-size: 16pt; }}
    h2 {{ font-size: 13pt; page-break-before: always; }}
    h2:first-of-type {{ page-break-before: avoid; }}
    .thesis {{ page-break-inside: avoid; }}
  }}
  body {{ font-family: 'Georgia', 'Times New Roman', serif; color: #222; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
  h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 8px; }}
  h2.part-title {{ color: #2c3e50; margin-top: 2em; border-left: 4px solid #3498db; padding-left: 12px; }}
  h3.chapter-title {{ color: #555; margin-top: 1.5em; }}
  .thesis {{ margin: 12px 0; padding: 10px; border: 1px solid #e0e0e0; border-radius: 4px; }}
  .thesis-header {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
  .thesis-id {{ font-weight: bold; color: #3498db; }}
  .badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 0.75em; color: white; }}
  .badge-main {{ background: #3498db; }}
  .badge-supporting {{ background: #95a5a6; }}
  .badge-conclusion {{ background: #e67e22; }}
  .badge-premise {{ background: #9b59b6; }}
  .thesis-title {{ font-weight: 600; }}
  .confidence {{ color: #888; font-size: 0.85em; }}
  .description {{ margin: 6px 0; color: #444; }}
  blockquote {{ border-left: 3px solid #3498db; padding: 6px 12px; margin: 6px 0; background: #f8f9fa; font-style: italic; color: #555; }}
  .refs {{ font-size: 0.85em; color: #666; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th, td {{ padding: 6px 10px; text-align: left; border-bottom: 1px solid #ddd; }}
  th {{ background: #f0f0f0; font-weight: 600; }}
  .stats-table {{ max-width: 400px; }}
  .summary {{ background: #f8f9fa; padding: 16px; border-radius: 6px; margin: 16px 0; }}
  .print-btn {{ display: inline-block; padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 1em; margin: 12px 0; }}
  .print-btn:hover {{ background: #2980b9; }}
</style>
</head>
<body>

<h1>Relatorio de Analise Teologica</h1>
<p><strong>Livro:</strong> Cristianismo Basico &mdash; John Stott</p>
<p><strong>Analise:</strong> Extracao de teses, cadeias logicas e citacoes</p>

<button class="print-btn no-print" onclick="window.print()">Imprimir / Salvar como PDF</button>

<h2>Resumo Executivo</h2>
<div class="summary">
  <p>{_esc(analysis.summary or '(Nao disponivel)')}</p>
</div>

<h2>Estatisticas</h2>
<table class="stats-table">
  <tr><th>Metrica</th><th>Valor</th></tr>
  <tr><td>Total de teses</td><td>{len(analysis.theses)}</td></tr>
  <tr><td>Teses principais (main)</td><td>{type_counts.get('main', 0)}</td></tr>
  <tr><td>Teses de suporte</td><td>{type_counts.get('supporting', 0)}</td></tr>
  <tr><td>Premissas</td><td>{type_counts.get('premise', 0)}</td></tr>
  <tr><td>Conclusoes</td><td>{type_counts.get('conclusion', 0)}</td></tr>
  <tr><td>Cadeias logicas</td><td>{len(analysis.chains)}</td></tr>
  <tr><td>Citacoes biblicas</td><td>{len(biblical)}</td></tr>
  <tr><td>Citacoes academicas</td><td>{len(scholarly)}</td></tr>
</table>

<h2>Teses por Capitulo</h2>
{''.join(thesis_sections)}

<h2>Indice de Citacoes Biblicas</h2>
<table>
  <tr><th>Livro</th><th>Referencias</th></tr>
  {''.join(citation_rows)}
</table>

{'<h2>Citacoes Academicas</h2><ul>' + ''.join(scholarly_items) + '</ul>' if scholarly_items else ''}

<h2>Fluxo Argumentativo</h2>
<div class="summary">
  <p>{_esc(analysis.argument_flow or '(Nao disponivel)')}</p>
</div>

</body>
</html>"""

    return html


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_pdf_report(
    output_dir: Path,
    analysis: BookAnalysis | None = None,
) -> Path:
    """Generate a PDF report (or print-ready HTML) from analysis data.

    Parameters
    ----------
    output_dir : Path
        Directory to write the report to.
    analysis : BookAnalysis | None
        If provided, uses this data. Otherwise loads from JSON files in output_dir.

    Returns
    -------
    Path
        Path to the generated file (.pdf if weasyprint available, .html otherwise).
    """
    if analysis is None:
        analysis = _load_analysis_from_files(output_dir)

    html = _build_html(analysis)

    # Try weasyprint for direct PDF
    try:
        import weasyprint
        pdf_path = output_dir / "relatorio.pdf"
        weasyprint.HTML(string=html).write_pdf(str(pdf_path))
        logger.info(f"PDF report generated: {pdf_path}")
        return pdf_path
    except ImportError:
        logger.info("weasyprint not available; generating print-ready HTML instead")
    except Exception as e:
        logger.warning(f"weasyprint failed ({e}); falling back to HTML")

    # Fallback: save as HTML
    html_path = output_dir / "relatorio.html"
    html_path.write_text(html, encoding="utf-8")
    logger.info(f"Print-ready HTML report generated: {html_path}")
    return html_path


def _load_analysis_from_files(output_dir: Path) -> BookAnalysis:
    """Load BookAnalysis from JSON files in the output directory."""
    from .models import ThesisChain

    theses = []
    theses_path = output_dir / "theses.json"
    if theses_path.exists():
        data = json.loads(theses_path.read_text(encoding="utf-8"))
        theses = [Thesis(**t) for t in data]

    chains = []
    chains_path = output_dir / "chains.json"
    if chains_path.exists():
        data = json.loads(chains_path.read_text(encoding="utf-8"))
        chains = [ThesisChain(**c) for c in data]

    citations = []
    citations_path = output_dir / "citations.json"
    if citations_path.exists():
        data = json.loads(citations_path.read_text(encoding="utf-8"))
        citations = [Citation(**c) for c in data]

    # Try to get summary from report.md
    summary = ""
    argument_flow = ""
    report_path = output_dir / "report.md"
    if report_path.exists():
        report_text = report_path.read_text(encoding="utf-8")
        # Extract summary between "## Resumo Executivo" and "---"
        import re
        summary_match = re.search(
            r"## Resumo Executivo\s*\n\s*(.*?)(?=\n---)", report_text, re.DOTALL
        )
        if summary_match:
            summary = summary_match.group(1).strip()
        flow_match = re.search(
            r"## Fluxo Argumentativo\s*\n\s*(.*?)(?=\n---)", report_text, re.DOTALL
        )
        if flow_match:
            argument_flow = flow_match.group(1).strip()

    return BookAnalysis(
        theses=theses,
        chains=chains,
        citations=citations,
        summary=summary,
        argument_flow=argument_flow,
    )
