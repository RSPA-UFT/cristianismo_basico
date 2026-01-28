"""Scrollytelling page generator using Scrollama.js + D3.js.

Generates a self-contained HTML file that narrates John Stott's argument
progressively via scroll. Uses a sticky graphic + scrolling text layout
(canonical scrollytelling pattern).
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

_PART_INFO = [
    (
        "Parte 1 - A Pessoa de Cristo",
        "#048fcc",
        "Quem \u00e9 Jesus Cristo?",
        "Stott examina tr\u00eas linhas de evid\u00eancia: as declara\u00e7\u00f5es de Cristo, "
        "seu car\u00e1ter e sua ressurrei\u00e7\u00e3o.",
        ["Declara\u00e7\u00f5es", "Car\u00e1ter", "Ressurrei\u00e7\u00e3o"],
    ),
    (
        "Parte 2 - A Necessidade do Homem",
        "#dc3545",
        "O pecado \u00e9 universal",
        "Tr\u00eas consequ\u00eancias do pecado: separa\u00e7\u00e3o de Deus, escravid\u00e3o moral "
        "e conflito interior.",
        ["Separa\u00e7\u00e3o", "Escravid\u00e3o", "Conflito"],
    ),
    (
        "Parte 3 - A Obra de Cristo",
        "#fd7e14",
        "A cruz: sacrif\u00edcio redentor",
        "A morte de Cristo n\u00e3o foi exemplo moral, mas sacrif\u00edcio substitutivo. "
        "Do Antigo Testamento \u00e0 cruz, o plano redentor se revela.",
        ["Perd\u00e3o", "Transforma\u00e7\u00e3o", "Comunh\u00e3o"],
    ),
    (
        "Parte 4 - A Resposta do Homem",
        "#28a745",
        "O custo do discipulado",
        "Eis que estou \u00e0 porta e bato (Ap 3:20). "
        "A resposta exigida: arrependimento, f\u00e9 e obedi\u00eancia.",
        ["Arrependimento", "F\u00e9", "Obedi\u00eancia"],
    ),
]


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def generate_scrollytelling(
    output_dir: Path,
    analysis: BookAnalysis | None = None,
) -> Path:
    """Generate a scrollytelling HTML page from analysis data.

    Parameters
    ----------
    output_dir : Path
        Directory to write the page to.
    analysis : BookAnalysis | None
        If provided, uses this data. Otherwise loads from JSON files in output_dir.

    Returns
    -------
    Path
        Path to the generated scrollytelling.html file.
    """
    if analysis is None:
        analysis = _load_analysis(output_dir)

    groups = _load_citation_groups(output_dir)
    html = _build_scrollytelling(analysis, groups)
    path = output_dir / "scrollytelling.html"
    path.write_text(html, encoding="utf-8")
    logger.info(f"Scrollytelling generated: {path}")
    return path


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


def _load_citation_groups(output_dir: Path) -> list[dict]:
    """Load citation groups from citation_groups.json."""
    groups_path = output_dir / "citation_groups.json"
    if groups_path.exists():
        data = json.loads(groups_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "groups" in data:
            return data["groups"]
        if isinstance(data, list):
            return data
    return []


def _build_scrollytelling(analysis: BookAnalysis, groups: list[dict]) -> str:
    """Build the complete scrollytelling HTML page."""
    css = _build_css()
    hero = _build_hero(analysis)
    overview = _build_overview(analysis)

    # Build part sections (intro + theses for each of 4 parts)
    part_sections = ""
    for i, (part_name, color, subtitle, desc, pillars) in enumerate(_PART_INFO, 1):
        part_theses = [
            t for t in analysis.theses
            if f"Parte {i}" in (t.part or derive_part_from_id(t.id))
        ]
        part_sections += _build_part_intro(i, part_theses, color, subtitle, desc, pillars)
        part_sections += _build_part_theses(i, part_theses, color)

    network = _build_network()
    citations_section = _build_citations(groups)
    conclusion = _build_conclusion(analysis)
    embedded_data = _embed_data(analysis, groups)
    javascript = _build_javascript(analysis)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cristianismo B\u00e1sico - John Stott | Narrativa</title>
<style>
{css}
</style>
</head>
<body>
<nav class="site-nav" style="background:#036c9a;padding:8px 16px;display:flex;gap:16px;justify-content:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:0.9rem;">
  <a href="index.html" style="color:#e0f0ff;text-decoration:none;">Narrativa</a>
  <a href="visualizacao.html" style="color:#e0f0ff;text-decoration:none;">Painel</a>
  <a href="apresentacao.html" style="color:#e0f0ff;text-decoration:none;">Apresenta\u00e7\u00e3o</a>
</nav>

{hero}

<div id="scrolly">
  <div class="scroll-graphic" id="graphic">
    <div id="viz-container" aria-label="Area de visualizacao interativa">
      <div id="viz-overview" class="viz-panel"></div>
      <div id="viz-part-intro" class="viz-panel"></div>
      <div id="viz-part-theses" class="viz-panel"></div>
      <div id="viz-network" class="viz-panel"><svg id="network-svg" aria-label="Rede logica de teses"></svg></div>
      <div id="viz-citations" class="viz-panel"><svg id="citations-svg" aria-label="Grafico de citacoes biblicas"></svg></div>
    </div>
  </div>
  <div class="scroll-text">
    {overview}
    {part_sections}
    {network}
    {citations_section}
  </div>
</div>

{conclusion}

<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script src="https://unpkg.com/scrollama@3.2.0/build/scrollama.min.js"></script>
<script>
{embedded_data}
{javascript}
</script>
</body>
</html>"""


def _build_css() -> str:
    """Build all CSS styles for the scrollytelling page."""
    return """/* Reset */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #343a40;
  background: #fafafa;
  line-height: 1.7;
  font-size: 18px;
}

/* Hero */
.scroll-hero {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #03618b 0%, #036c9a 50%, #048fcc 100%);
  color: #fff;
  text-align: center;
  padding: 2rem;
  position: relative;
}

.scroll-hero h1 {
  font-size: 3.2rem;
  margin-bottom: 0.3rem;
  animation: fadeInUp 1s ease-out;
}

.scroll-hero .author {
  font-size: 1.4rem;
  color: #b0c4de;
  margin-bottom: 1.5rem;
  animation: fadeInUp 1s ease-out 0.3s both;
}

.scroll-hero .tagline {
  font-size: 1.1rem;
  color: #8899aa;
  max-width: 600px;
  animation: fadeInUp 1s ease-out 0.6s both;
}

.scroll-hero .scroll-hint {
  position: absolute;
  bottom: 2rem;
  font-size: 0.85rem;
  color: #556;
  animation: bounce 2s infinite 2s;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

/* Scrolly container */
#scrolly {
  position: relative;
  display: flex;
}

.scroll-graphic {
  position: sticky;
  top: 0;
  width: 55%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-right: 1px solid #e0e0e0;
  z-index: 1;
}

#viz-container {
  width: 90%;
  height: 80%;
  position: relative;
}

.viz-panel {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.5s ease;
  pointer-events: none;
}

.viz-panel.active {
  opacity: 1;
  pointer-events: auto;
}

.scroll-text {
  width: 45%;
  padding: 0 2rem;
}

/* Steps */
.step {
  min-height: 80vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 2rem 1rem;
  opacity: 0.3;
  transition: opacity 0.4s ease;
}

.step.is-active {
  opacity: 1;
}

.step h2 {
  font-size: 1.6rem;
  margin-bottom: 0.8rem;
  line-height: 1.3;
}

.step h3 {
  font-size: 1.2rem;
  color: #555;
  margin-bottom: 0.5rem;
}

.step p {
  font-size: 1rem;
  color: #444;
  margin-bottom: 0.8rem;
}

.step .step-meta {
  font-size: 0.85rem;
  color: #888;
  margin-top: 0.5rem;
}

/* Part accent bars */
.step[data-part="1"] h2 { border-left: 4px solid #048fcc; padding-left: 12px; }
.step[data-part="2"] h2 { border-left: 4px solid #dc3545; padding-left: 12px; }
.step[data-part="3"] h2 { border-left: 4px solid #fd7e14; padding-left: 12px; }
.step[data-part="4"] h2 { border-left: 4px solid #28a745; padding-left: 12px; }

/* Overview counters */
.counter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  width: 100%;
  max-width: 500px;
}

.counter-box {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 24px 16px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.counter-num {
  font-size: 2.8rem;
  font-weight: bold;
  color: #048fcc;
  display: block;
}

.counter-label {
  font-size: 0.85rem;
  color: #666;
  margin-top: 4px;
}

/* Part bar */
.part-bar {
  display: flex;
  width: 100%;
  max-width: 500px;
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
  margin-top: 24px;
}

.part-bar-seg {
  transition: width 0.8s ease;
}

/* Intro viz */
.intro-viz {
  text-align: center;
  width: 100%;
}

.intro-viz .part-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  display: block;
}

.intro-viz .pillars {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 1.5rem;
  flex-wrap: wrap;
}

.intro-viz .pillar {
  background: rgba(255,255,255,0.15);
  border-radius: 8px;
  padding: 12px 20px;
  font-size: 0.95rem;
  font-weight: bold;
  color: #fff;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.viz-panel.active .pillar {
  opacity: 1;
  transform: translateY(0);
}

.viz-panel.active .pillar:nth-child(2) { transition-delay: 0.15s; }
.viz-panel.active .pillar:nth-child(3) { transition-delay: 0.3s; }

/* Thesis cards in viz */
.thesis-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  max-width: 500px;
  max-height: 80%;
  overflow-y: auto;
}

.thesis-card {
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
  border-left: 4px solid #ccc;
  opacity: 0;
  transform: translateX(-20px);
  transition: opacity 0.4s ease, transform 0.4s ease;
}

.viz-panel.active .thesis-card {
  opacity: 1;
  transform: translateX(0);
}

.viz-panel.active .thesis-card:nth-child(2) { transition-delay: 0.1s; }
.viz-panel.active .thesis-card:nth-child(3) { transition-delay: 0.2s; }
.viz-panel.active .thesis-card:nth-child(4) { transition-delay: 0.3s; }
.viz-panel.active .thesis-card:nth-child(5) { transition-delay: 0.4s; }

.thesis-card .badge {
  display: inline-block;
  background: #eee;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.75rem;
  font-weight: bold;
  color: #555;
  margin-bottom: 4px;
}

.thesis-card .card-title {
  font-size: 0.9rem;
  font-weight: bold;
  margin-bottom: 4px;
}

.thesis-card .confidence-bar {
  height: 4px;
  border-radius: 2px;
  background: #e0e0e0;
  margin-top: 6px;
}

.thesis-card .confidence-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}

/* Network SVG */
#network-svg, #citations-svg {
  width: 100%;
  height: 100%;
}

/* Conclusion */
.scroll-conclusion {
  min-height: 80vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #036c9a 0%, #03618b 100%);
  color: #fff;
  text-align: center;
  padding: 3rem 2rem;
}

.scroll-conclusion h2 {
  font-size: 2rem;
  margin-bottom: 1.5rem;
}

.scroll-conclusion .final-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  justify-content: center;
}

.scroll-conclusion .final-stat {
  text-align: center;
}

.scroll-conclusion .final-stat .num {
  font-size: 2.2rem;
  font-weight: bold;
  display: block;
}

.scroll-conclusion .final-stat .label {
  font-size: 0.8rem;
  color: #8899aa;
}

.scroll-conclusion .convergence {
  display: flex;
  gap: 12px;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  justify-content: center;
}

.scroll-conclusion .conv-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.85rem;
  color: #fff;
  transition: transform 0.5s ease;
}

.scroll-conclusion .summary-text {
  max-width: 700px;
  font-size: 1rem;
  line-height: 1.8;
  color: #b0c4de;
}

/* Prefers reduced motion */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .step { opacity: 1; }
  .viz-panel { opacity: 1; pointer-events: auto; }
  .thesis-card { opacity: 1; transform: none; }
  .pillar { opacity: 1; transform: none; }
}

/* Mobile: stacked layout */
@media (max-width: 768px) {
  body { font-size: 16px; }

  .scroll-hero h1 { font-size: 2rem; }
  .scroll-hero .author { font-size: 1.1rem; }

  #scrolly { flex-direction: column; }

  .scroll-graphic {
    position: relative;
    width: 100%;
    height: 50vh;
    border-right: none;
    border-bottom: 1px solid #e0e0e0;
  }

  .scroll-text {
    width: 100%;
    padding: 0 1rem;
  }

  .step { min-height: 60vh; }

  .counter-grid { grid-template-columns: 1fr 1fr; gap: 12px; }
  .counter-num { font-size: 2rem; }
}"""


def _embed_data(analysis: BookAnalysis, groups: list[dict]) -> str:
    """Embed analysis data as JavaScript constants."""
    theses_data = []
    for t in analysis.theses:
        theses_data.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "thesis_type": t.thesis_type,
            "part": t.part,
            "chapter": t.chapter,
            "confidence": t.confidence,
            "citations": [
                {"reference": c.reference, "citation_type": c.citation_type}
                for c in t.citations
            ],
        })

    chains_data = []
    for c in analysis.chains:
        chains_data.append({
            "from_thesis_id": c.from_thesis_id,
            "to_thesis_id": c.to_thesis_id,
            "relationship": c.relationship,
            "strength": c.strength,
        })

    citations_data = []
    for c in analysis.citations:
        citations_data.append({
            "reference": c.reference,
            "citation_type": c.citation_type,
            "text": c.text or "",
        })

    groups_data = groups if groups else []
    summary_text = analysis.summary or ""

    return (
        f"const THESES = {json.dumps(theses_data, ensure_ascii=False)};\n"
        f"const CHAINS = {json.dumps(chains_data, ensure_ascii=False)};\n"
        f"const CITATIONS = {json.dumps(citations_data, ensure_ascii=False)};\n"
        f"const GROUPS = {json.dumps(groups_data, ensure_ascii=False)};\n"
        f"const SUMMARY = {json.dumps(summary_text, ensure_ascii=False)};\n"
    )


def _build_hero(analysis: BookAnalysis) -> str:
    """Build S0: Hero section."""
    n_theses = len(analysis.theses)
    n_citations = len(analysis.citations)
    n_chains = len(analysis.chains)
    return f"""<section class="scroll-hero" id="hero" aria-label="Introdu\u00e7\u00e3o">
  <h1>Cristianismo B\u00e1sico</h1>
  <div class="author">John Stott</div>
  <div class="tagline">Uma jornada pelo argumento central da f\u00e9 crist\u00e3 &mdash;
    {n_theses} teses, {n_citations} cita\u00e7\u00f5es, 4 partes</div>
  <div class="scroll-hint" aria-hidden="true">&#8595; Role para explorar</div>
</section>"""


def _build_overview(analysis: BookAnalysis) -> str:
    """Build S1: Overview step."""
    biblical = sum(1 for c in analysis.citations if c.citation_type == "biblical")
    scholarly = sum(1 for c in analysis.citations if c.citation_type == "scholarly")
    return f"""<div class="step" data-step="1" aria-label="Vis\u00e3o geral">
  <h2>Vis\u00e3o Geral</h2>
  <p>O argumento de Stott se desdobra em 4 partes progressivas,
    construindo um caso cumulativo pela f\u00e9 crist\u00e3.</p>
  <p class="step-meta">{len(analysis.theses)} teses &bull;
    {len(analysis.chains)} cadeias l\u00f3gicas &bull;
    {biblical} cita\u00e7\u00f5es b\u00edblicas &bull;
    {scholarly} cita\u00e7\u00f5es acad\u00eamicas</p>
</div>"""


def _build_part_intro(
    part_num: int,
    theses: list[Thesis],
    color: str,
    subtitle: str,
    description: str,
    pillars: list[str],
) -> str:
    """Build part intro step (S2, S4, S6, S8)."""
    step_num = part_num * 2  # 2, 4, 6, 8
    main_count = sum(1 for t in theses if t.thesis_type == "main")
    pillar_items = "".join(
        f'<span class="pillar-tag">{_esc(p)}</span>' for p in pillars
    )
    return f"""<div class="step" data-step="{step_num}" data-part="{part_num}"
     aria-label="Parte {part_num} introdu\u00e7\u00e3o">
  <h2>{_esc(subtitle)}</h2>
  <p>{_esc(description)}</p>
  <p class="step-meta">{len(theses)} teses ({main_count} principais) &bull;
    Parte {part_num} de 4</p>
</div>"""


def _build_part_theses(
    part_num: int,
    theses: list[Thesis],
    color: str,
) -> str:
    """Build part theses step (S3, S5, S7, S9)."""
    step_num = part_num * 2 + 1  # 3, 5, 7, 9
    main_theses = [t for t in theses if t.thesis_type == "main"]
    items = ""
    for t in main_theses[:5]:
        citation_ref = ""
        if t.citations:
            citation_ref = f' ({_esc(t.citations[0].reference)})'
        items += (
            f'<div class="thesis-item">'
            f'<strong>{_esc(t.id)}</strong>: {_esc(t.title)}{citation_ref}'
            f'</div>'
        )

    if not items:
        items = "<p>Teses desta parte ser\u00e3o reveladas ao explorar os dados completos.</p>"

    return f"""<div class="step" data-step="{step_num}" data-part="{part_num}"
     aria-label="Parte {part_num} teses">
  <h3>Teses Principais &mdash; Parte {part_num}</h3>
  {items}
  <p class="step-meta">{len(main_theses)} teses principais exibidas</p>
</div>"""


def _build_network() -> str:
    """Build S10: Network visualization step."""
    return """<div class="step" data-step="10" aria-label="Rede l\u00f3gica completa">
  <h2>Rede L\u00f3gica Completa</h2>
  <p>As teses se conectam por cadeias l\u00f3gicas, formando uma rede
    argumentativa coerente. Conex\u00f5es entre partes aparecem em dourado.</p>
  <p class="step-meta">Visualiza\u00e7\u00e3o interativa com D3.js force-directed graph</p>
</div>"""


def _build_citations(groups: list[dict]) -> str:
    """Build S11: Citations visualization step."""
    group_list = ""
    for g in groups[:8]:
        theme = g.get("theme", "")
        count = len(g.get("citations", g.get("references", [])))
        group_list += f'<div class="group-tag">{_esc(theme)} ({count})</div>'

    if not group_list:
        group_list = "<p>Grupos tem\u00e1ticos ser\u00e3o exibidos com dados completos.</p>"

    return f"""<div class="step" data-step="11" aria-label="Cita\u00e7\u00f5es b\u00edblicas">
  <h2>Cita\u00e7\u00f5es B\u00edblicas</h2>
  <p>As cita\u00e7\u00f5es se distribuem por livros da B\u00edblia, agrupadas em temas teol\u00f3gicos.</p>
  {group_list}
  <p class="step-meta">Barras horizontais D3 por livro b\u00edblico</p>
</div>"""


def _build_conclusion(analysis: BookAnalysis) -> str:
    """Build S12: Conclusion section."""
    n_theses = len(analysis.theses)
    n_citations = len(analysis.citations)
    n_chains = len(analysis.chains)
    summary = _esc(analysis.summary) if analysis.summary else ""
    return f"""<section class="scroll-conclusion" id="conclusion" aria-label="Conclus\u00e3o">
  <h2>Um Argumento Coerente</h2>
  <div class="convergence">
    <div class="conv-icon" style="background:#048fcc;">P1</div>
    <div class="conv-icon" style="background:#dc3545;">P2</div>
    <div class="conv-icon" style="background:#fd7e14;">P3</div>
    <div class="conv-icon" style="background:#28a745;">P4</div>
  </div>
  <div class="final-stats">
    <div class="final-stat"><span class="num">{n_theses}</span><span class="label">teses</span></div>
    <div class="final-stat"><span class="num">{n_citations}</span><span class="label">cita\u00e7\u00f5es</span></div>
    <div class="final-stat"><span class="num">{n_chains}</span><span class="label">cadeias</span></div>
  </div>
  <p class="summary-text">{summary}</p>
</section>"""


def _build_javascript(analysis: BookAnalysis) -> str:
    """Build the Scrollama + D3 JavaScript code."""
    # Compute part counts for the overview bar
    part_counts = defaultdict(int)
    for t in analysis.theses:
        effective = t.part or derive_part_from_id(t.id)
        for i in range(1, 5):
            if f"Parte {i}" in effective:
                part_counts[i] += 1
                break

    total = max(sum(part_counts.values()), 1)
    pct = {i: round(part_counts[i] / total * 100, 1) for i in range(1, 5)}

    n_biblical = sum(1 for c in analysis.citations if c.citation_type == "biblical")
    n_scholarly = sum(1 for c in analysis.citations if c.citation_type == "scholarly")

    return f"""
// ── Visualization update logic ──────────────────────────────
const panels = document.querySelectorAll('.viz-panel');
const PART_COLORS = {json.dumps({f"Parte {i}": c for i, (_, c, *_) in enumerate(_PART_INFO, 1)}, ensure_ascii=False)};

function hideAllPanels() {{
  panels.forEach(p => p.classList.remove('active'));
}}

function showPanel(id) {{
  hideAllPanels();
  const el = document.getElementById(id);
  if (el) el.classList.add('active');
}}

// ── S1: Overview viz ────────────────────────────────────────
function renderOverview() {{
  const container = document.getElementById('viz-overview');
  container.innerHTML = `
    <div class="counter-grid">
      <div class="counter-box"><span class="counter-num" data-target="{len(analysis.theses)}">0</span><div class="counter-label">Teses</div></div>
      <div class="counter-box"><span class="counter-num" data-target="{len(analysis.chains)}">0</span><div class="counter-label">Cadeias</div></div>
      <div class="counter-box"><span class="counter-num" data-target="{n_biblical}">0</span><div class="counter-label">Cita\u00e7\u00f5es B\u00edblicas</div></div>
      <div class="counter-box"><span class="counter-num" data-target="{n_scholarly}">0</span><div class="counter-label">Cita\u00e7\u00f5es Acad\u00eamicas</div></div>
    </div>
    <div class="part-bar">
      <div class="part-bar-seg" style="width:{pct[1]}%;background:#048fcc;" title="Parte 1"></div>
      <div class="part-bar-seg" style="width:{pct[2]}%;background:#dc3545;" title="Parte 2"></div>
      <div class="part-bar-seg" style="width:{pct[3]}%;background:#fd7e14;" title="Parte 3"></div>
      <div class="part-bar-seg" style="width:{pct[4]}%;background:#28a745;" title="Parte 4"></div>
    </div>`;
  animateCounters();
}}

function animateCounters() {{
  document.querySelectorAll('.counter-num[data-target]').forEach(el => {{
    const target = parseInt(el.dataset.target);
    const duration = 1200;
    const start = performance.now();
    function update(now) {{
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      el.textContent = Math.round(progress * target);
      if (progress < 1) requestAnimationFrame(update);
    }}
    requestAnimationFrame(update);
  }});
}}

// ── S2/4/6/8: Part intro viz ────────────────────────────────
const PART_PILLARS = {{
  1: {{ icon: "?", pillars: ["Declara\u00e7\u00f5es", "Car\u00e1ter", "Ressurrei\u00e7\u00e3o"], color: "#048fcc" }},
  2: {{ icon: "!", pillars: ["Separa\u00e7\u00e3o", "Escravid\u00e3o", "Conflito"], color: "#dc3545" }},
  3: {{ icon: "+", pillars: ["Perd\u00e3o", "Transforma\u00e7\u00e3o", "Comunh\u00e3o"], color: "#fd7e14" }},
  4: {{ icon: "\\u2764", pillars: ["Arrependimento", "F\u00e9", "Obedi\u00eancia"], color: "#28a745" }}
}};

function renderPartIntro(partNum) {{
  const info = PART_PILLARS[partNum];
  if (!info) return;
  const container = document.getElementById('viz-part-intro');
  container.style.background = info.color + '15';
  container.innerHTML = `
    <div class="intro-viz" style="color:${{info.color}};">
      <span class="part-icon">${{info.icon}}</span>
      <div class="pillars">
        ${{info.pillars.map(p => `<div class="pillar" style="background:${{info.color}};">${{p}}</div>`).join('')}}
      </div>
    </div>`;
}}

// ── S3/5/7/9: Part theses viz ───────────────────────────────
function renderPartTheses(partNum) {{
  const color = PART_PILLARS[partNum]?.color || '#999';
  const partTheses = THESES.filter(t => {{
    if (t.part && t.part.includes('Parte ' + partNum)) return true;
    const m = t.id.match(/^T(\\d+)\\./);
    return m && parseInt(m[1]) === partNum;
  }});
  const mainTheses = partTheses.filter(t => t.thesis_type === 'main').slice(0, 5);

  const container = document.getElementById('viz-part-theses');
  container.innerHTML = `<div class="thesis-cards">
    ${{mainTheses.map(t => `
      <div class="thesis-card" style="border-left-color:${{color}};">
        <span class="badge">${{t.id}}</span>
        <div class="card-title">${{t.title}}</div>
        <div class="confidence-bar">
          <div class="confidence-fill" style="width:${{Math.round(t.confidence*100)}}%;background:${{color}};"></div>
        </div>
      </div>`).join('')}}
  </div>`;
}}

// ── S10: Network viz (D3 force) ─────────────────────────────
let networkRendered = false;
function renderNetwork() {{
  if (networkRendered) return;
  networkRendered = true;

  const svg = d3.select('#network-svg');
  const container = document.getElementById('viz-network');
  const width = container.clientWidth || 500;
  const height = container.clientHeight || 400;

  svg.attr('viewBox', `0 0 ${{width}} ${{height}}`);

  const nodes = THESES.map(t => {{
    let group = 0;
    if (t.part) {{
      const pm = t.part.match(/Parte (\\d)/);
      if (pm) group = parseInt(pm[1]);
    }}
    if (!group) {{
      const im = t.id.match(/^T(\\d+)\\./);
      if (im) group = parseInt(im[1]);
    }}
    return {{ id: t.id, title: t.title, part: t.part, group }};
  }});

  const nodeIds = new Set(nodes.map(n => n.id));
  const links = CHAINS
    .filter(c => nodeIds.has(c.from_thesis_id) && nodeIds.has(c.to_thesis_id))
    .map(c => ({{ source: c.from_thesis_id, target: c.to_thesis_id, strength: c.strength }}));

  const groupColors = {{ 1: '#048fcc', 2: '#dc3545', 3: '#fd7e14', 4: '#28a745' }};
  const shapes = {{ 1: 'circle', 2: 'rect', 3: 'diamond', 4: 'triangle' }};

  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(60))
    .force('charge', d3.forceManyBody().strength(-120))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(18));

  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', d => {{
      const s = nodes.find(n => n.id === (d.source.id || d.source));
      const t = nodes.find(n => n.id === (d.target.id || d.target));
      return (s && t && s.group !== t.group) ? '#DAA520' : '#ccc';
    }})
    .attr('stroke-width', d => Math.max(1, d.strength * 3))
    .attr('stroke-opacity', 0.6);

  const node = svg.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .call(d3.drag()
      .on('start', (e,d) => {{ if(!e.active) simulation.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
      .on('drag', (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
      .on('end', (e,d) => {{ if(!e.active) simulation.alphaTarget(0); d.fx=null; d.fy=null; }}));

  node.each(function(d) {{
    const g = d3.select(this);
    const color = groupColors[d.group] || '#999';
    const shape = shapes[d.group] || 'circle';
    if (shape === 'circle') g.append('circle').attr('r', 8).attr('fill', color);
    else if (shape === 'rect') g.append('rect').attr('x',-7).attr('y',-7).attr('width',14).attr('height',14).attr('fill', color);
    else if (shape === 'diamond') g.append('rect').attr('x',-7).attr('y',-7).attr('width',14).attr('height',14).attr('fill', color).attr('transform','rotate(45)');
    else if (shape === 'triangle') g.append('polygon').attr('points','0,-9 8,7 -8,7').attr('fill', color);
  }});

  node.append('title').text(d => d.id + ': ' + d.title);

  simulation.on('tick', () => {{
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
  }});
}}

// ── S11: Citations viz (D3 bars) ────────────────────────────
let citationsRendered = false;
function renderCitations() {{
  if (citationsRendered) return;
  citationsRendered = true;

  const biblical = CITATIONS.filter(c => c.citation_type === 'biblical');
  const byBook = {{}};
  biblical.forEach(c => {{
    const book = c.reference.split(/\\s+\\d/)[0].trim();
    byBook[book] = (byBook[book] || 0) + 1;
  }});

  const data = Object.entries(byBook)
    .map(([book, count]) => ({{ book, count }}))
    .sort((a, b) => b.count - a.count)
    .slice(0, 15);

  const svg = d3.select('#citations-svg');
  const container = document.getElementById('viz-citations');
  const width = container.clientWidth || 500;
  const height = container.clientHeight || 400;
  const margin = {{ top: 20, right: 30, bottom: 20, left: 80 }};

  svg.attr('viewBox', `0 0 ${{width}} ${{height}}`);

  const y = d3.scaleBand()
    .domain(data.map(d => d.book))
    .range([margin.top, height - margin.bottom])
    .padding(0.2);

  const x = d3.scaleLinear()
    .domain([0, d3.max(data, d => d.count)])
    .range([margin.left, width - margin.right]);

  svg.append('g')
    .attr('transform', `translate(${{margin.left}},0)`)
    .call(d3.axisLeft(y))
    .selectAll('text').style('font-size', '11px');

  svg.selectAll('.bar')
    .data(data)
    .join('rect')
    .attr('class', 'bar')
    .attr('x', margin.left)
    .attr('y', d => y(d.book))
    .attr('height', y.bandwidth())
    .attr('fill', '#048fcc')
    .attr('width', 0)
    .transition().duration(800)
    .attr('width', d => x(d.count) - margin.left);

  svg.selectAll('.bar-label')
    .data(data)
    .join('text')
    .attr('class', 'bar-label')
    .attr('x', d => x(d.count) + 4)
    .attr('y', d => y(d.book) + y.bandwidth() / 2 + 4)
    .text(d => d.count)
    .style('font-size', '11px')
    .style('fill', '#555');
}}

// ── Scrollama setup ─────────────────────────────────────────
const scroller = scrollama();

function handleStepEnter(response) {{
  // Mark active step
  document.querySelectorAll('.step').forEach(s => s.classList.remove('is-active'));
  response.element.classList.add('is-active');

  const step = parseInt(response.element.dataset.step);

  // Show appropriate visualization
  if (step === 1) {{
    showPanel('viz-overview');
    renderOverview();
  }} else if (step % 2 === 0 && step >= 2 && step <= 8) {{
    showPanel('viz-part-intro');
    renderPartIntro(step / 2);
  }} else if (step % 2 === 1 && step >= 3 && step <= 9) {{
    showPanel('viz-part-theses');
    renderPartTheses((step - 1) / 2);
  }} else if (step === 10) {{
    showPanel('viz-network');
    renderNetwork();
  }} else if (step === 11) {{
    showPanel('viz-citations');
    renderCitations();
  }}
}}

scroller
  .setup({{ step: '.step', offset: 0.5, progress: true }})
  .onStepEnter(handleStepEnter);

window.addEventListener('resize', scroller.resize);

// Show first panel on load
if (document.querySelectorAll('.step').length > 0) {{
  showPanel('viz-overview');
  renderOverview();
}}
"""
