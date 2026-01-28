"""Presentation slides generator using Reveal.js.

Generates a self-contained HTML file with Reveal.js CDN v5 for presenting
the theological analysis results.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from .models import BookAnalysis, Citation, Thesis, ThesisChain, derive_part_from_id

logger = logging.getLogger(__name__)

_PART_COLORS = {
    "Parte 1": "#048fcc",
    "Parte 2": "#dc3545",
    "Parte 3": "#fd7e14",
    "Parte 4": "#28a745",
}

_PART_TEXT_COLORS = {
    "Parte 1": "#036c9a",
    "Parte 2": "#b02a37",
    "Parte 3": "#c96209",
    "Parte 4": "#1e7b34",
}


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def generate_slides(
    output_dir: Path,
    analysis: BookAnalysis | None = None,
) -> Path:
    """Generate a Reveal.js slide presentation from analysis data.

    Parameters
    ----------
    output_dir : Path
        Directory to write the presentation to.
    analysis : BookAnalysis | None
        If provided, uses this data. Otherwise loads from JSON files in output_dir.

    Returns
    -------
    Path
        Path to the generated apresentacao.html file.
    """
    if analysis is None:
        analysis = _load_analysis(output_dir)

    html = _build_slides(analysis)
    path = output_dir / "apresentacao.html"
    path.write_text(html, encoding="utf-8")
    logger.info(f"Presentation generated: {path}")
    return path


def _build_flow_slides(argument_flow: str | None) -> str:
    """Build vertical sub-slides for the Argument Flow section.

    Splits flow text into paragraphs and distributes across sub-slides
    to prevent overflow on the 1100x700 viewport.
    """
    flow_text = argument_flow or "(Não disponível)"
    paragraphs = [p.strip() for p in flow_text.split("\n\n") if p.strip()]

    if len(paragraphs) <= 2:
        # Short text: single slide
        return f"""
  <section>
    <h2>Fluxo Argumentativo</h2>
    <div class="chain-viz">
      <div class="chain-node p1">P1: Pessoa</div>
      <div class="chain-arrow">&rarr;</div>
      <div class="chain-node p2">P2: Pecado</div>
      <div class="chain-arrow">&rarr;</div>
      <div class="chain-node p3">P3: Cruz</div>
      <div class="chain-arrow">&rarr;</div>
      <div class="chain-node p4">P4: Resposta</div>
    </div>
    <div class="flow-card">
      {_esc(flow_text)}
    </div>
  </section>"""

    # Multiple paragraphs: split into vertical sub-slides
    # First sub-slide: title + chain-viz + first paragraph
    # Remaining: pairs of paragraphs
    slides = []

    # Slide 8a: title + chain viz + intro paragraph
    slides.append(f"""
    <section>
      <h2>Fluxo Argumentativo</h2>
      <div class="chain-viz">
        <div class="chain-node p1">P1: Pessoa</div>
        <div class="chain-arrow">&rarr;</div>
        <div class="chain-node p2">P2: Pecado</div>
        <div class="chain-arrow">&rarr;</div>
        <div class="chain-node p3">P3: Cruz</div>
        <div class="chain-arrow">&rarr;</div>
        <div class="chain-node p4">P4: Resposta</div>
      </div>
      <div class="flow-card">
        {_esc(paragraphs[0])}
      </div>
    </section>""")

    # Remaining paragraphs in pairs
    remaining = paragraphs[1:]
    for i in range(0, len(remaining), 2):
        chunk = remaining[i : i + 2]
        body = "<br><br>".join(_esc(p) for p in chunk)
        slides.append(f"""
    <section>
      <h2>Fluxo Argumentativo (cont.)</h2>
      <div class="flow-card">
        {body}
      </div>
    </section>""")

    return "<section>\n" + "\n".join(slides) + "\n  </section>"


def _build_slides(analysis: BookAnalysis) -> str:
    """Build a Reveal.js HTML presentation."""
    # Collect stats
    type_counts: dict[str, int] = defaultdict(int)
    for t in analysis.theses:
        type_counts[t.thesis_type] += 1

    biblical = sum(1 for c in analysis.citations if c.citation_type == "biblical")
    scholarly = [c for c in analysis.citations if c.citation_type == "scholarly"]

    # Group theses by part
    by_part: dict[str, list[Thesis]] = defaultdict(list)
    for t in analysis.theses:
        part_key = t.part or derive_part_from_id(t.id) or "Geral"
        by_part[part_key].append(t)

    # Build part slides (one per part)
    part_slides = []
    part_info = [
        ("Parte 1 - A Pessoa de Cristo", "#048fcc", "#036c9a", "Cap. 1\u20134: Quem \u00e9 Jesus Cristo?"),
        ("Parte 2 - A Necessidade do Homem", "#dc3545", "#b02a37", "Cap. 5\u20136: O problema do pecado"),
        ("Parte 3 - A Obra de Cristo", "#fd7e14", "#c96209", "Cap. 7\u20138: A solu\u00e7\u00e3o na cruz"),
        ("Parte 4 - A Resposta do Homem", "#28a745", "#1e7b34", "Cap. 9\u201311: O que fazer?"),
    ]

    for part_name, color, text_color, subtitle in part_info:
        short = part_name.split(" - ")[0] if " - " in part_name else part_name
        theses = [
            t for t in analysis.theses
            if short in (t.part or derive_part_from_id(t.id))
        ]

        main_theses = [t for t in theses if t.thesis_type == "main"]
        thesis_items = ""
        for t in main_theses[:4]:
            thesis_items += f'<li><strong>{_esc(t.id)}</strong>: {_esc(t.title)}</li>\n'

        part_slides.append(f"""
        <section data-background-color="{color}10">
          <h2 style="color:{text_color};">{_esc(part_name)}</h2>
          <p class="subtitle">{_esc(subtitle)}</p>
          <ul class="thesis-list">
            {thesis_items}
          </ul>
          <p class="count">{len(theses)} teses &bull; {len(main_theses)} principais</p>
        </section>
        """)

    # Scholarly citations slide (2-column grid)
    scholarly_items = ""
    for c in scholarly:
        author = c.author or c.reference
        work = f" &mdash; <em>{_esc(c.work)}</em>" if c.work else ""
        scholarly_items += f'<div class="sg-item"><strong>{_esc(author)}</strong>{work}</div>\n'

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Apresenta\u00e7\u00e3o: Cristianismo B\u00e1sico - John Stott</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/theme/white.css">
<style>
  .reveal {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  .reveal h1 {{ color: #343a40; font-size: 1.8em; }}
  .reveal h2 {{ color: #343a40; font-size: 1.4em; }}
  .reveal h3 {{ color: #555; font-size: 1.1em; }}
  .reveal .subtitle {{ color: #666; font-size: 0.9em; margin-top: -10px; }}
  .reveal .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
  .reveal .stat-box {{ background: #f8f9fa; border-radius: 8px; padding: 16px; text-align: center; }}
  .reveal .stat-box .num {{ font-size: 2.2em; font-weight: bold; color: #048fcc; }}
  .reveal .stat-box .label {{ font-size: 0.8em; color: #666; }}
  .reveal .thesis-list {{ text-align: left; font-size: 0.75em; list-style: none; }}
  .reveal .thesis-list li {{ margin: 8px 0; padding: 6px 12px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #048fcc; }}
  .reveal .count {{ font-size: 0.7em; color: #888; margin-top: 16px; }}
  .reveal .flow-card {{ background: #f8f9fa; padding: 14px; border-radius: 6px; margin: 8px 0; text-align: left; font-size: 0.7em; line-height: 1.5; max-height: 420px; overflow-y: auto; }}
  .reveal .scholarly-list {{ text-align: left; font-size: 0.7em; list-style: none; }}
  .reveal .scholarly-list li {{ margin: 6px 0; padding: 4px 0; border-bottom: 1px solid #eee; }}
  .reveal .scholarly-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; text-align: left; font-size: 0.7em; }}
  .reveal .scholarly-grid .sg-item {{ padding: 4px 0; border-bottom: 1px solid #eee; }}
  .reveal .chain-viz {{ display: flex; justify-content: center; align-items: center; gap: 12px; margin: 20px 0; flex-wrap: wrap; }}
  .reveal .chain-node {{ background: #048fcc; color: white; padding: 8px 14px; border-radius: 2rem; font-size: 0.7em; font-weight: bold; }}
  .reveal .chain-arrow {{ font-size: 1.5em; color: #999; }}
  .reveal .method-list {{ text-align: left; font-size: 0.75em; }}
  .reveal .method-list li {{ margin: 10px 0; }}
  .p1 {{ background: #048fcc; }} .p2 {{ background: #dc3545; }}
  .p3 {{ background: #fd7e14; }} .p4 {{ background: #28a745; }}
</style>
</head>
<body>
<nav class="site-nav" style="background:#036c9a;padding:8px 16px;display:flex;gap:16px;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:0.9rem;">
  <a href="index.html" style="color:#e0f0ff;text-decoration:none;">Narrativa</a>
  <a href="visualizacao.html" style="color:#e0f0ff;text-decoration:none;">Painel</a>
  <a href="apresentacao.html" style="color:#e0f0ff;text-decoration:none;">Apresenta\u00e7\u00e3o</a>
</nav>
<div class="reveal">
<div class="slides">

  <!-- Slide 1: Title -->
  <section>
    <h1>Cristianismo B\u00e1sico</h1>
    <h3>John Stott</h3>
    <p class="subtitle">An\u00e1lise teol\u00f3gica estruturada: teses, cadeias l\u00f3gicas e cita\u00e7\u00f5es</p>
  </section>

  <!-- Slide 2: Summary -->
  <section>
    <h2>Resumo Executivo</h2>
    <div class="flow-card">
      {_esc(_truncate(analysis.summary or '(N\u00e3o dispon\u00edvel)', 600))}
    </div>
  </section>

  <!-- Slide 3: Stats -->
  <section>
    <h2>Vis\u00e3o Geral</h2>
    <div class="stat-grid">
      <div class="stat-box"><div class="num">{len(analysis.theses)}</div><div class="label">Teses</div></div>
      <div class="stat-box"><div class="num">{len(analysis.chains)}</div><div class="label">Cadeias L\u00f3gicas</div></div>
      <div class="stat-box"><div class="num">{biblical}</div><div class="label">Cita\u00e7\u00f5es B\u00edblicas</div></div>
      <div class="stat-box"><div class="num">{len(scholarly)}</div><div class="label">Cita\u00e7\u00f5es Acad\u00eamicas</div></div>
    </div>
    <p class="count">
      {type_counts.get('main', 0)} principais &bull;
      {type_counts.get('supporting', 0)} suporte &bull;
      {type_counts.get('conclusion', 0)} conclus\u00f5es &bull;
      {type_counts.get('premise', 0)} premissas
    </p>
  </section>

  <!-- Slides 4-7: Parts -->
  {''.join(part_slides)}

  <!-- Slide 8: Argument Flow (vertical sub-slides) -->
  {_build_flow_slides(analysis.argument_flow)}

  <!-- Slide 9: Scholarly Citations -->
  <section>
    <h2>Cita\u00e7\u00f5es Acad\u00eamicas</h2>
    <div class="scholarly-grid">
      {scholarly_items if scholarly_items else '<div class="sg-item">(Nenhuma cita\u00e7\u00e3o acad\u00eamica)</div>'}
    </div>
    <p class="count">{len(scholarly)} autores/obras citados(as)</p>
  </section>

  <!-- Slide 10: Methodology -->
  <section>
    <h2>Metodologia</h2>
    <ul class="method-list">
      <li><strong>Extra\u00e7\u00e3o:</strong> PDF &rarr; texto estruturado (Docling/PyMuPDF)</li>
      <li><strong>Chunking:</strong> Divis\u00e3o hier\u00e1rquica por cap\u00edtulos ({len(analysis.theses)} teses)</li>
      <li><strong>An\u00e1lise LLM:</strong> Claude Opus 4.5 para extra\u00e7\u00e3o de argumentos</li>
      <li><strong>Valida\u00e7\u00e3o:</strong> Cross-refer\u00eancia com texto original</li>
      <li><strong>S\u00edntese:</strong> Deduplica\u00e7\u00e3o + sele\u00e7\u00e3o das teses mais relevantes</li>
    </ul>
  </section>

</div>
</div>

<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
<script>
  Reveal.initialize({{
    hash: true,
    slideNumber: true,
    transition: 'slide',
    width: 1100,
    height: 700,
  }});
</script>
</body>
</html>"""

    return html


def _load_analysis(output_dir: Path) -> BookAnalysis:
    """Load BookAnalysis from JSON files in the output directory."""
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

    summary = ""
    argument_flow = ""
    report_path = output_dir / "report.md"
    if report_path.exists():
        import re
        report_text = report_path.read_text(encoding="utf-8")
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
