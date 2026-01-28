# Estado da Sessao - Cristianismo Basico

Data: 2026-01-27
Versao atual: v0.7.0
Ultima sessao encerrada com todos os objetivos cumpridos.

---

## O Que E Este Projeto

Pipeline Python de 4 estagios para extracao e analise automatizada de teses teologicas do livro "Cristianismo Basico" de John Stott, usando argument mining com LLMs.

### Estrutura do Livro
- Parte 1 (Cap 1-4): A Pessoa de Cristo
- Parte 2 (Cap 5-6): A Necessidade do Homem
- Parte 3 (Cap 7-8): A Obra de Cristo
- Parte 4 (Cap 9-11): A Resposta do Homem

---

## Estado Atual: COMPLETO

### Codigo-fonte (src/)
| Modulo | Funcao | Status |
|--------|--------|--------|
| `__main__.py` | Entry point CLI | OK |
| `config.py` | Settings via .env (Pydantic) | OK |
| `models.py` | Modelos Pydantic (Thesis, Citation c/ author/work/context) | OK |
| `extractor.py` | Extracao PDF 3-tier (Docling/PyMuPDF/Tesseract) | OK |
| `chunker.py` | Chunking hierarquico por capitulos/partes | OK |
| `analyzer.py` | Analise LLM (4 fases: 3a-3d) | OK |
| `scholarly.py` | Extracao de citacoes scholarly + footnotes das notas | OK |
| `prompts.py` | Templates de prompt para LLM (com regras scholarly) | OK |
| `validators.py` | Validacao pos-processamento + detect_footnotes() | OK |
| `output.py` | Geracao de output (JSON, Markdown, secao scholarly) | OK |
| `pdf_report.py` | Geracao de relatorio PDF/HTML print-ready | OK |
| `slides.py` | Geracao de apresentacao Reveal.js (10+ slides, sub-slides, grid) | OK |
| `scrollytelling.py` | Scrollytelling (Scrollama.js + D3.js, 12 secoes) | OK |
| `pipeline.py` | Orquestrador dos 4 estagios (com fase 3a+ e scrollytelling) | OK |

### Testes (tests/)
- **199 testes passando** (pytest)
- Cobertura: conftest, models, config, extractor, chunker, analyzer, output, pipeline, validators, scholarly, pdf_report, slides, scrollytelling, html_audit
- Arquivos de teste: `test_scholarly.py` (9), `test_pdf_report.py` (4), `test_slides.py` (12), `test_scrollytelling.py` (17), `test_html_audit.py` (18)
- Testes atualizados: test_models (+3), test_validators (+3), test_output (+2), test_pipeline (+2)
- Dependencias dev: pytest>=8.0, pytest-cov>=6.0

### Output Final (output/)
| Arquivo | Tamanho | Conteudo |
|---------|---------|----------|
| `theses.json` | 76 KB | 52 teses com citacoes exatas de Stott |
| `chains.json` | 15 KB | 57 cadeias logicas entre teses |
| `citations.json` | 36 KB | 186 citacoes (169 biblicas + 17 scholarly) |
| `citation_groups.json` | 4 KB | 8 grupos tematicos |
| `report.md` | 57 KB | Relatorio completo em Markdown (com secao scholarly) |
| `visualizacao.html` | 150 KB | Dashboard interativo (8 abas, D3.js + Chart.js + d3-sankey) |
| `apresentacao.html` | 13 KB | Apresentacao Reveal.js (10+ slides, sub-slides verticais) |
| `relatorio.html` | 74 KB | Relatorio HTML print-ready para PDF |
| `scrollytelling.html` | 98 KB | Scrollytelling narrativo (Scrollama.js + D3.js, 12 secoes) |
| `extracted_text.md` | 265 KB | Texto bruto extraido do PDF |
| `chunks/` | 30 arquivos | Chunks Markdown por capitulo |
| `per_chapter/` | 30 JSONs | Analises por capitulo (cache pipeline) |

### GitHub Pages (docs/)
| Arquivo | Conteudo |
|---------|----------|
| `docs/index.html` | Scrollytelling (pagina principal do site) |
| `docs/visualizacao.html` | Dashboard interativo |
| `docs/apresentacao.html` | Slides Reveal.js |

### Documentacao
| Arquivo | Conteudo |
|---------|----------|
| `README.md` | Documentacao do projeto (instalacao, uso, arquitetura) |
| `QUALITY_REPORT.md` | Relatorio de qualidade com 5 iteracoes documentadas |
| `SESSION_STATE.md` | Este arquivo |

### Configuracao
| Arquivo | Conteudo |
|---------|----------|
| `pyproject.toml` | Dependencias (docling, pymupdf, pydantic, etc.) |
| `.env` | LLM_PROVIDER=ollama, modelos, caminhos |
| `.venv/` | Python 3.12, gerenciado por uv |

---

## Historico de Iteracoes

### Iteracao 1: Pipeline automatizado (qwen2.5:14b + deepseek-r1:32b)
- 117 teses, 27% refs vazias, teses genericas, resumo/fluxo vazios
- Limitacao: modelos locais nao seguiram instrucoes complexas

### Iteracao 2: Sintese Claude v1 (sobre dados qwen2.5)
- 37 teses selecionadas, IDs corrigidos, resumo/fluxo escritos
- Limitacao: supporting_text eram parafrases, nao citacoes de Stott

### Iteracao 3: Re-extracao Claude v2 (diretamente dos textos originais)
- **52 teses** com citacoes exatas de Stott
- **169 citacoes** biblicas unicas (5.6x mais que v1)
- **57 chains** logicas (2x mais que v1)
- **8 grupos** tematicos

### Iteracao 4: Citacoes Scholarly + Footnotes + Visualizacao + PDF/Slides
- **17 citacoes scholarly** extraidas com `author`, `work`, `context`
- **detect_footnotes()** para reclassificacao de refs numericas
- **Sankey diagram** (7a aba do dashboard, d3-sankey)
- **Export PNG/SVG** em todos os paineis
- **Apresentacao Reveal.js** (10 slides auto-contidos)
- **Relatorio HTML print-ready** (PDF via WeasyPrint ou Ctrl+P)
- **143 testes** (30 novos, 0 falhas)

### Iteracao 5: Scrollytelling + GitHub Pages
- **Scrollytelling** (`output/scrollytelling.html`) — 12 secoes narrativas com scroll progressivo
  - Scrollama.js v3.2 + D3.js v7 (sticky graphic + scrolling text)
  - Grafo force-directed, barras de citacoes, contadores animados
  - Mobile stacked, `prefers-reduced-motion`, `aria-label`
- **GitHub Pages** (`docs/`) — 3 paginas com navegacao inter-paginas
- **src/scrollytelling.py** — modulo gerador (507 linhas)
- **160 testes** (17 novos, 0 falhas)

### Iteracao 6: Identidade visual ICE + derivacao de IDs (v0.6.0)
- Identidade visual ICE Metropolitana (`#048fcc`), tipografia sans-serif
- `derive_part_from_id()` / `derive_chapter_from_id()` para backfill
- Navegacao Narrativa / Painel / Apresentacao
- Paleta harmonizada: `#048fcc`, `#dc3545`, `#fd7e14`, `#28a745`
- **176 testes** (16 novos, 0 falhas)

### Iteracao 7: Correcoes de painel, slides e confianca (v0.7.0)
- Unicode escapes `\u00XX` substituidos por UTF-8 real em `docs/visualizacao.html`
- Diacriticos portugueses completos em todo o texto user-facing
- `TYPE_LABELS` traduzidos: principal, suporte, conclusao, premissa
- Aba "Confianca" separada da Visao Geral (8 abas total no dashboard)
- Paleta consistente: `#3498db` eliminado, `#048fcc` em todos os graficos
- Contraste WCAG nos slides: headings escurecidos (`#036c9a`, `#b02a37`, `#c96209`, `#1e7b34`)
- Fluxo argumentativo em sub-slides verticais (nested sections)
- Citacoes academicas em grid 2 colunas
- Resumo executivo truncado (600 chars) + overflow-y fallback
- `tests/test_html_audit.py` — 18 testes de auditoria HTML automatizada
- **199 testes** (23 novos, 0 falhas)
- Este e o output final atual

---

## Visualizacao (output/visualizacao.html)

Dashboard HTML auto-contido com 8 abas:
1. **Visao Geral** - Donut charts (distribuicao por tipo, raciocinio) + barras (capitulos)
2. **Rede Logica** - Grafo D3.js force-directed (52 nos, 57 arestas, drag/zoom/hover/click)
3. **Hierarquia** - Arvore colapsavel D3.js (Livro > Parte > Capitulo > Tese)
4. **Citacoes Biblicas** - Barras por livro biblico (AT/NT) e por grupo tematico
5. **Fluxo Argumentativo** - 4 movimentos do argumento em HTML formatado
6. **Fluxo Sankey** - Diagrama Sankey (D3-sankey) com fluxo inter-partes
7. **Confianca** - Grafico de barras com indice de confianca LLM por tese (aba propria desde v0.7.0)
8. **Dados** - Tabela pesquisavel com todas as 52 teses (badges em portugues)

Cores por parte: P1=#048fcc (azul), P2=#dc3545 (vermelho), P3=#fd7e14 (laranja), P4=#28a745 (verde)
Tipos traduzidos: principal, suporte, conclusao, premissa (via TYPE_LABELS)
CDNs: D3.js v7, Chart.js v4, d3-sankey v0.12
Export: Botoes PNG/SVG em todos os paineis

## Scrollytelling (output/scrollytelling.html)

Pagina narrativa auto-contida com scroll progressivo (12 secoes):
1. **Hero** - Titulo, autor, tagline com estatisticas
2. **Visao Geral** - 4 contadores animados + barra de partes proporcional
3. **Parte 1 Intro** - Pilares: Declaracoes, Carater, Ressurreicao
4. **Parte 1 Teses** - Cards com badge ID, titulo, barra de confianca
5. **Parte 2 Intro** - Pilares: Separacao, Escravidao, Conflito
6. **Parte 2 Teses** - Cards com accent vermelho
7. **Parte 3 Intro** - Pilares: Perdao, Transformacao, Comunhao
8. **Parte 3 Teses** - Cards com accent laranja
9. **Parte 4 Intro** - Pilares: Arrependimento, Fe, Obediencia
10. **Parte 4 Teses** - Cards com accent verde
11. **Rede Logica** - Grafo D3 force-directed (nos por parte, cross-part dourado)
12. **Citacoes** - Barras horizontais D3 por livro biblico

Layout: sticky graphic (55%) + scrolling text (45%), stacked em mobile (<768px)
CDNs: Scrollama.js v3.2, D3.js v7
Acessibilidade: lang="pt-BR", prefers-reduced-motion, aria-label, formas+cores no grafo

---

## Scripts Auxiliares (scratchpad - temporarios)

Localizacao: `/tmp/claude/-mnt-c-cristianismo-basico/.../scratchpad/`

| Script | Funcao |
|--------|--------|
| `synthesize.py` | Sintese v1 (sobre dados qwen2.5) |
| `synthesize_v2.py` | Sintese v2 (re-extracao) - gerou output final |
| `generate_viz.py` | Gerador do dashboard HTML |
| `part[1-4]_theses.json` | Teses extraidas por parte (input do synthesize_v2) |

**ATENCAO:** Esses arquivos estao em /tmp e podem ser perdidos em reboot. Se precisar recria-los, o codigo esta documentado no historico de conversas.

---

## Possiveis Proximos Passos

### Concluidos nas Iteracoes 4-5
- ~~Diagrama Sankey (fluxo argumentativo visual entre partes)~~ FEITO
- ~~Exportar graficos como PNG/SVG~~ FEITO
- ~~Versao em PDF do relatorio~~ FEITO (HTML print-ready + WeasyPrint opcional)
- ~~Modo de apresentacao (slides)~~ FEITO (Reveal.js)
- ~~Extrair citacoes de teologos como `citation_type: "scholarly"`~~ FEITO (17 citacoes)
- ~~Identificar notas de rodape (`citation_type: "footnote"`)~~ FEITO
- ~~Inicializar repositorio git~~ FEITO
- ~~Scrollytelling (narrativa progressiva via scroll)~~ FEITO (Scrollama.js + D3.js)
- ~~GitHub Pages (docs/ com 3 paginas)~~ FEITO

### Melhorias no Conteudo
- Adicionar provedor Anthropic/OpenAI ao pipeline automatizado (src/analyzer.py)

### Infraestrutura
- CI/CD (GitHub Actions com pytest)
- Aumentar cobertura de testes (pytest-cov)
- Docker para reproducibilidade

### Analise Avancada
- Comparar estrutura argumentativa com outros livros de apologetica
- Gerar perguntas de estudo por capitulo
- Criar indice remissivo de citacoes biblicas
- Timeline interativa dos eventos biblicos mencionados

---

## Como Retomar

```bash
cd /mnt/c/cristianismo_basico

# Verificar ambiente
.venv/bin/python --version   # Python 3.12
uv run pytest tests/ -q      # 199 passed

# Executar pipeline completo (requer Ollama rodando)
uv run python -m src

# Abrir visualizacao
# Abrir output/visualizacao.html no navegador

# Regenerar visualizacao (se scripts disponiveis)
.venv/bin/python /tmp/claude/.../scratchpad/generate_viz.py
```

---

## Decisoes Tecnicas Tomadas

1. **Re-extracao com Claude em vez de confiar nos dados qwen2.5** - qualidade 5x superior
2. **HTML auto-contido** em vez de framework SPA - zero dependencias, abre em qualquer navegador
3. **D3.js para rede/arvore** e **Chart.js para barras/donuts** - libs complementares
4. **Dados embutidos no HTML** em vez de fetch - funciona offline
5. **Validador pos-processamento** em vez de two-pass LLM - mais rapido e determinista
6. **52 teses (4-5 por capitulo)** em vez das 117 originais - equilibrio granularidade/legibilidade
7. **Scholarly como modulo separado** (src/scholarly.py) em vez de inline no analyzer - dados hardcoded + regex para maxima precisao
8. **Reveal.js CDN** em vez de framework local - apresentacao auto-contida, zero build
9. **HTML print-ready como fallback** para PDF - WeasyPrint e opcional (deps de sistema), Ctrl+P sempre funciona
10. **Scrollama.js** para scrollytelling em vez de GSAP - 2.7KB vs 30KB, IntersectionObserver, sem scroll events
11. **GitHub Pages via docs/** em vez de output/ - output/ no .gitignore, docs/ versionado com nav entre paginas
