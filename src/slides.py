"""Presentation slides generator using Reveal.js.

Generates a self-contained HTML file with Reveal.js CDN v5 for presenting
the theological analysis results.
"""

import base64
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

_PART_ICONS = {
    "Parte 1": "👤",  # Pessoa
    "Parte 2": "⚠️",  # Perigo/Pecado
    "Parte 3": "✝️",  # Cruz
    "Parte 4": "🙏",  # Resposta
}

_PART_DESCRIPTIONS = {
    "Parte 1": "Os capítulos iniciais estabelecem quem Jesus é e por que podemos confiar nele.",
    "Parte 2": "O livro explora a realidade do pecado e como afeta todos nós.",
    "Parte 3": "A cruz de Cristo é apresentada como a solução definitiva para o problema do pecado.",
    "Parte 4": "Como devemos responder ao evangelho? Arrependimento, fé e vida transformada.",
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
    logo_path: Path | None = None,
) -> Path:
    """Generate a Reveal.js slide presentation from analysis data.

    Parameters
    ----------
    output_dir : Path
        Directory to write the presentation to.
    analysis : BookAnalysis | None
        If provided, uses this data. Otherwise loads from JSON files in output_dir.
    logo_path : Path | None
        If provided, embeds the logo as base64 in the title slide.

    Returns
    -------
    Path
        Path to the generated apresentacao.html file.
    """
    if analysis is None:
        analysis = _load_analysis(output_dir)

    html = _build_slides(analysis, logo_path=logo_path)
    path = output_dir / "apresentacao.html"
    path.write_text(html, encoding="utf-8")
    logger.info(f"Presentation generated: {path}")
    return path


def _build_logo_img(logo_path: Path | None) -> str:
    """Return an <img> tag with base64-encoded logo, or empty string if no logo."""
    if logo_path is None or not logo_path.exists():
        return ""
    data = logo_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'alt="Logotipo: Igreja Cristã Evangélica - 125 Anos de história" '
        f'role="img" '
        f'style="max-width: 140px; margin-bottom: 16px; border-radius: 50%;">'
    )


def _build_flow_slides(argument_flow: str | None) -> str:
    """Build vertical sub-slides for the Argument Flow section.

    Uses structured bullet points for better readability and accessibility.
    """
    slides = []

    # Slide 1: Overview visual
    slides.append("""
    <section>
      <h2>Fluxo Argumentativo: 4 Movimentos</h2>
      <div class="chain-viz">
        <div class="chain-node p1">P1: Pessoa</div>
        <div class="chain-arrow">&rarr;</div>
        <div class="chain-node p2">P2: Pecado</div>
        <div class="chain-arrow">&rarr;</div>
        <div class="chain-node p3">P3: Cruz</div>
        <div class="chain-arrow">&rarr;</div>
        <div class="chain-node p4">P4: Resposta</div>
      </div>
      <p class="subtitle" style="margin-top: 20px;">A estrutura argumentativa do livro segue quatro movimentos principais</p>
    </section>""")

    # Slides 2-5: Um por movimento, com bullets
    movements = [
        {
            "title": "Movimento 1: Quem é Jesus? 👤",
            "subtitle": "Três evidências da identidade de Cristo",
            "bullets": [
                "<strong>Suas afirmações:</strong> Jesus falou de si como nenhum líder religioso (ex: 'Eu Sou', perdoava pecados)",
                "<strong>Seu caráter:</strong> Jesus era impecável (perfeito), combinando autoridade com humildade",
                "<strong>Sua ressurreição:</strong> Testemunhas, túmulo vazio, transformação dos discípulos"
            ]
        },
        {
            "title": "Movimento 2: Qual é o nosso problema? ⚠️",
            "subtitle": "A realidade universal do pecado",
            "bullets": [
                "<strong>Pecado como rebeldia:</strong> Não apenas erros, mas rejeição consciente de Deus",
                "<strong>Consequências:</strong> Separação de Deus, relacionamentos quebrados, culpa real",
                "<strong>Incapacidade humana:</strong> Não podemos nos salvar por esforço próprio"
            ]
        },
        {
            "title": "Movimento 3: O que Jesus fez? ✝️",
            "subtitle": "A solução na cruz de Cristo",
            "bullets": [
                "<strong>Substituição:</strong> Jesus tomou nosso lugar e pagou o preço do pecado",
                "<strong>Satisfação da justiça:</strong> Deus é santo e justo, a cruz satisfaz ambos",
                "<strong>Reconciliação:</strong> A cruz restaura o relacionamento entre Deus e humanidade"
            ]
        },
        {
            "title": "Movimento 4: Como devemos responder? 🙏",
            "subtitle": "A resposta necessária ao evangelho",
            "bullets": [
                "<strong>Arrependimento:</strong> Mudar de direção, reconhecer erros e decidir viver diferente",
                "<strong>Fé:</strong> Confiar em Cristo como Salvador e Senhor pessoal",
                "<strong>Vida transformada:</strong> O Espírito Santo capacita para nova maneira de viver"
            ]
        },
    ]

    for mov in movements:
        bullets_html = "\n".join([f"<li>{bullet}</li>" for bullet in mov["bullets"]])
        slides.append(f"""
    <section>
      <h2>{mov["title"]}</h2>
      <p class="subtitle">{mov["subtitle"]}</p>
      <ul class="content-bullets">
        {bullets_html}
      </ul>
    </section>""")

    return "<section>\n" + "\n".join(slides) + "\n  </section>"


def _build_glossary_slide() -> str:
    """Build a glossary slide explaining technical terms."""
    terms = [
        ("Impecabilidade", "Significa ser perfeito ou sem defeitos. Jesus tinha um caráter sem falhas."),
        ("Pecado", "Quando fazemos escolhas que nos distanciam de Deus e prejudicam relacionamentos."),
        ("Salvação", "Ser resgatado do pecado e restaurado em relacionamento com Deus."),
        ("Substituição", "Jesus tomou nosso lugar e pagou o preço de nossas falhas na cruz."),
        ("Arrependimento", "Mudar de direção: reconhecer erros e decidir viver de forma diferente."),
        ("Reconciliação", "Voltar a estar bem com Deus, restaurando o relacionamento quebrado."),
    ]

    items_html = ""
    for term, definition in terms:
        items_html += f"""
        <div class="glossary-item">
          <strong>{term}</strong>
          <p>{definition}</p>
        </div>"""

    return f"""
  <section>
    <h2>Termos Explicados</h2>
    <div class="glossary-grid">
      {items_html}
    </div>
  </section>"""


def _build_summary_slides(summary: str) -> str:
    """Build one or more slides for the executive summary.

    If summary fits in ~500 chars, returns a single slide.
    Otherwise splits into sentences and distributes across vertical sub-slides.
    """
    text = summary or "(Não disponível)"
    if len(text) <= 500:
        return f"""
  <section>
    <h2>Resumo Executivo</h2>
    <div class="flow-card">
      {_esc(text)}
    </div>
  </section>"""

    # Split into sentences and group into chunks of ~450 chars
    sentences = [s.strip() for s in text.replace(". ", ".\n").split("\n") if s.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        if current_len + len(sentence) > 450 and current:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))

    slides = []
    for i, chunk in enumerate(chunks):
        title = "Resumo Executivo" if i == 0 else "Resumo Executivo (cont.)"
        slides.append(f"""
    <section>
      <h2>{title}</h2>
      <div class="flow-card">
        {_esc(chunk)}
      </div>
    </section>""")

    return "<section>\n" + "\n".join(slides) + "\n  </section>"


def _build_slides(analysis: BookAnalysis, *, logo_path: Path | None = None) -> str:
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
        ("Parte 1", "A Pessoa de Cristo", "#048fcc", "#036c9a", "Cap. 1–4: Quem é Jesus Cristo?"),
        ("Parte 2", "A Necessidade do Homem", "#dc3545", "#b02a37", "Cap. 5–6: O problema do pecado"),
        ("Parte 3", "A Obra de Cristo", "#fd7e14", "#c96209", "Cap. 7–8: A solução na cruz"),
        ("Parte 4", "A Resposta do Homem", "#28a745", "#1e7b34", "Cap. 9–11: O que fazer?"),
    ]

    for short, full_title, color, text_color, subtitle in part_info:
        theses = [
            t for t in analysis.theses
            if short in (t.part or derive_part_from_id(t.id))
        ]

        main_theses = [t for t in theses if t.thesis_type == "main"]
        thesis_items = ""
        for idx, t in enumerate(main_theses[:4], 1):
            thesis_items += f'<li><strong>{idx}.</strong> {_esc(t.title)}</li>\n'

        icon = _PART_ICONS.get(short, "")
        desc = _PART_DESCRIPTIONS.get(short, "")

        part_slides.append(f"""
        <section>
          <div style="border-top: 6px solid {color}; padding-top: 20px;">
            <h2 style="color:{text_color}; font-size: 1.8em;">
              <span style="font-size: 1.2em; margin-right: 8px;">{icon}</span>
              {_esc(short)} - {_esc(full_title)}
            </h2>
            <p class="subtitle" style="font-size: 1.1em; margin-bottom: 16px;">{_esc(subtitle)}</p>
            <p style="font-size: 0.95em; color: #444; line-height: 1.6; max-width: 520px; margin: 0 auto 20px;">{_esc(desc)}</p>
            <ul class="thesis-list">
              {thesis_items}
            </ul>
            <p class="count">Esta seção contém <strong>{len(theses)}</strong> ideias-chave</p>
          </div>
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
  /* Base typography - increased sizes for accessibility */
  .reveal {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  .reveal h1 {{ color: #343a40; font-size: 2.2em; }}
  .reveal h2 {{ color: #343a40; font-size: 1.6em; }}
  .reveal h3 {{ color: #555; font-size: 1.3em; }}
  .reveal .subtitle {{ color: #333; font-size: 1.0em; margin-top: -10px; }}

  /* Stats grid */
  .reveal .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
  .reveal .stat-box {{ background: #f8f9fa; border-radius: 8px; padding: 16px; text-align: center; }}
  .reveal .stat-box .num {{ font-size: 2.2em; font-weight: bold; color: #048fcc; }}
  .reveal .stat-box .label {{ font-size: 0.9em; color: #444; }}

  /* Thesis list - improved readability */
  .reveal .thesis-list {{ text-align: left; font-size: 0.9em; list-style: none; }}
  .reveal .thesis-list li {{ margin: 12px 0; padding: 8px 14px; background: #f8f9fa; border-radius: 4px; border-left: 4px solid #048fcc; }}
  .reveal .count {{ font-size: 0.85em; color: #333; margin-top: 16px; }}

  /* Flow card - improved line height */
  .reveal .flow-card {{ background: #f8f9fa; padding: 16px; border-radius: 6px; margin: 10px 0; text-align: left; font-size: 0.95em; line-height: 1.8; max-height: 420px; overflow-y: auto; }}

  /* Scholarly citations */
  .reveal .scholarly-list {{ text-align: left; font-size: 0.9em; list-style: none; }}
  .reveal .scholarly-list li {{ margin: 8px 0; padding: 6px 0; border-bottom: 1px solid #ddd; }}
  .reveal .scholarly-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; text-align: left; font-size: 0.9em; }}
  .reveal .scholarly-grid .sg-item {{ padding: 6px 0; border-bottom: 1px solid #ddd; }}

  /* Chain visualization */
  .reveal .chain-viz {{ display: flex; justify-content: center; align-items: center; gap: 12px; margin: 20px 0; flex-wrap: wrap; }}
  .reveal .chain-node {{ background: #048fcc; color: white; padding: 12px 18px; border-radius: 2rem; font-size: 0.85em; font-weight: bold; }}
  .reveal .chain-arrow {{ font-size: 1.5em; color: #555; }}

  /* Method list */
  .reveal .method-list {{ text-align: left; font-size: 0.9em; }}
  .reveal .method-list li {{ margin: 12px 0; }}

  /* Part colors */
  .p1 {{ background: #048fcc; }} .p2 {{ background: #dc3545; }}
  .p3 {{ background: #fd7e14; }} .p4 {{ background: #28a745; }}

  /* Content bullets - for flow slides */
  .reveal .content-bullets {{
    text-align: left;
    font-size: 1.0em;
    line-height: 1.9;
    list-style-type: disc;
    margin: 0 auto;
    max-width: 85%;
  }}
  .reveal .content-bullets li {{
    margin: 14px 0;
    padding-left: 12px;
  }}
  .reveal .content-bullets strong {{
    color: #048fcc;
  }}

  /* Glossary grid */
  .reveal .glossary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    text-align: left;
    max-width: 88%;
    margin: 0 auto;
  }}
  .reveal .glossary-item {{
    background: #f0f8ff;
    padding: 14px;
    border-radius: 6px;
    border-left: 4px solid #048fcc;
  }}
  .reveal .glossary-item strong {{
    display: block;
    color: #036c9a;
    font-size: 1.0em;
    margin-bottom: 6px;
  }}
  .reveal .glossary-item p {{
    font-size: 0.9em;
    line-height: 1.6;
    color: #333;
    margin: 0;
  }}

  /* Navigation improvements */
  .reveal .slide-number {{
    font-size: 1.2em;
    color: #048fcc;
    font-weight: 600;
    bottom: 12px;
    right: 12px;
  }}
  .reveal .controls {{
    bottom: 16px;
    right: 16px;
  }}
  .reveal .controls button {{
    color: #048fcc;
  }}
  .reveal .progress {{
    background: rgba(4, 143, 204, 0.3);
    height: 6px;
  }}
  .reveal .progress span {{
    background: #048fcc;
  }}

  /* Accessibility - Focus states */
  .reveal *:focus {{
    outline: 3px solid #048fcc;
    outline-offset: 2px;
  }}

  /* High contrast support */
  @media (prefers-contrast: more) {{
    .reveal h1, .reveal h2 {{
      color: #000;
      font-weight: 700;
    }}
  }}

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {{
    .reveal {{
      transition: none !important;
    }}
  }}

  /* Mobile and tablets responsiveness */
  @media (max-width: 768px) {{
    .reveal .glossary-grid {{
      grid-template-columns: 1fr;
    }}
    .reveal .scholarly-grid {{
      grid-template-columns: 1fr;
    }}
    .reveal h1 {{ font-size: 1.8em; }}
    .reveal h2 {{ font-size: 1.4em; }}
  }}

  /* High zoom support */
  @media (min-width: 1600px) {{
    .reveal .flow-card {{ font-size: 1.1em; }}
    .reveal .subtitle {{ font-size: 1.15em; }}
  }}
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
  <section role="region" aria-label="Slide de título">
    {_build_logo_img(logo_path)}
    <h1>Cristianismo B\u00e1sico</h1>
    <h3>John Stott</h3>
    <p class="subtitle">An\u00e1lise teol\u00f3gica estruturada: teses, cadeias l\u00f3gicas e cita\u00e7\u00f5es</p>
  </section>

  <!-- Slide 2: Summary -->
  {_build_summary_slides(analysis.summary)}

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

  <!-- Slide 4: Glossary -->
  {_build_glossary_slide()}

  <!-- Slides 5-8: Parts -->
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
    slideNumber: 'c/t',
    transition: 'fade',
    transitionSpeed: 'slow',
    width: 1100,
    height: 700,
    margin: 0.15,

    // Visible controls
    controls: true,
    controlsLayout: 'bottom-right',
    controlsBackArrows: 'faded',
    progress: true,

    // Accessibility
    keyboard: true,
    touch: true,
    overview: true,
    center: true,
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
