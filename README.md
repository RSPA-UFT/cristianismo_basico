# Cristianismo Basico - Analise Teologica com LLM

Pipeline de extracao e analise automatizada de teses teologicas do livro
"Cristianismo Basico" de John Stott, usando argument mining com LLMs.

## Funcionalidades

- Extracao de texto de PDF (3-tier: Docling, PyMuPDF, Tesseract OCR)
- Chunking hierarquico por capitulos e partes do livro
- Extracao de teses, citacoes biblicas e notas com LLMs
- Extracao de citacoes scholarly (teologos, pensadores) com author/work/context
- Deteccao de notas de rodape (footnotes)
- Identificacao de cadeias logicas entre teses
- Correlacao tematica de citacoes biblicas
- Sintese e deduplicacao de teses
- Validacao pos-processamento de citacoes e referencias
- Dashboard interativo (7 abas: visao geral, rede logica, hierarquia, citacoes, fluxo, dados, Sankey)
- Export de graficos como PNG/SVG
- Scrollytelling narrativo (12 secoes com Scrollama.js + D3.js)
- Apresentacao Reveal.js (10 slides auto-contidos)
- Relatorio HTML print-ready (PDF via WeasyPrint ou Ctrl+P)
- Geracao de relatorio em Markdown
- GitHub Pages com 3 paginas navegaveis (scrollytelling, dashboard, slides)

## Estrutura do Livro Analisado

- **Parte 1** (Cap 1-4): A Pessoa de Cristo
- **Parte 2** (Cap 5-6): A Necessidade do Homem
- **Parte 3** (Cap 7-8): A Obra de Cristo
- **Parte 4** (Cap 9-11): A Resposta do Homem

## Requisitos

- Python >= 3.12
- Provedor LLM: Ollama (local) ou OpenAI/Anthropic (cloud)

## Instalacao

```bash
uv sync
cp .env.example .env
# Editar .env com configuracoes do LLM

# Extras opcionais
uv sync --extra ocr    # Tesseract OCR + pdf2image
uv sync --extra pdf    # WeasyPrint para geracao de PDF
uv sync --extra dev    # pytest + pytest-cov
```

## Uso

```bash
uv run python -m src
```

## Configuracao (.env)

| Variavel | Descricao | Padrao |
|----------|-----------|--------|
| `LLM_PROVIDER` | Provedor LLM | `ollama` |
| `OLLAMA_MODEL` | Modelo padrao | `qwen2.5:14b` |
| `OLLAMA_REASONING_MODEL` | Modelo de raciocinio | `deepseek-r1:32b` |
| `OLLAMA_BASE_URL` | URL base Ollama | `http://localhost:11434/v1` |
| `OPENAI_API_KEY` | Chave API OpenAI | (vazio) |
| `ANTHROPIC_API_KEY` | Chave API Anthropic | (vazio) |
| `LLM_TEMPERATURE` | Temperatura do modelo | `0.3` |
| `LLM_MAX_RETRIES` | Max tentativas por chamada | `3` |

## Output

| Arquivo | Descricao |
|---------|-----------|
| `output/theses.json` | 52 teses finais consolidadas |
| `output/chains.json` | 57 cadeias logicas entre teses |
| `output/citations.json` | 186 citacoes (169 biblicas + 17 scholarly) |
| `output/citation_groups.json` | 8 grupos tematicos de citacoes |
| `output/report.md` | Relatorio completo em Markdown (com secao scholarly) |
| `output/visualizacao.html` | Dashboard interativo (7 abas, D3.js + Chart.js + d3-sankey) |
| `output/apresentacao.html` | Apresentacao Reveal.js (10 slides auto-contidos) |
| `output/relatorio.html` | Relatorio HTML print-ready para PDF |
| `output/scrollytelling.html` | Scrollytelling narrativo (12 secoes, Scrollama.js + D3.js) |

## Testes

```bash
uv sync --extra dev
uv run pytest tests/ -v              # 160 testes
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```

## Arquitetura

```
src/
  __main__.py      - Entry point CLI
  pipeline.py      - Orquestrador 4 estagios
  extractor.py     - Extracao PDF (3-tier)
  chunker.py       - Chunking hierarquico
  analyzer.py      - Analise LLM (4 fases)
  scholarly.py     - Extracao de citacoes scholarly e footnotes
  validators.py    - Validacao pos-processamento + detect_footnotes
  models.py        - Modelos Pydantic (Thesis, Citation, etc.)
  prompts.py       - Templates de prompt para LLM
  output.py        - Geracao de output (JSON, Markdown)
  pdf_report.py    - Geracao de relatorio PDF/HTML print-ready
  slides.py        - Geracao de apresentacao Reveal.js
  scrollytelling.py - Geracao de scrollytelling (Scrollama.js + D3.js)
  config.py        - Configuracao via .env (Pydantic Settings)
```

### Pipeline (4 estagios)

1. **Extracao PDF** - Extrai texto do PDF usando Docling, PyMuPDF ou Tesseract
2. **Chunking** - Divide texto em ~30 chunks por capitulos/secoes
3. **Analise LLM** (5 fases):
   - 3a: Extracao de teses e citacoes por chunk + validacao
   - 3a+: Extracao de citacoes scholarly e footnotes (src/scholarly.py)
   - 3b: Identificacao de cadeias logicas entre teses
   - 3c: Correlacao tematica de citacoes biblicas
   - 3d: Deduplicacao e sintese final
4. **Output** - Gera JSON estruturado, relatorio Markdown, PDF, slides e scrollytelling

## GitHub Pages

O diretorio `docs/` contem as paginas para publicacao via GitHub Pages:

| Pagina | URL relativa | Conteudo |
|--------|-------------|----------|
| `docs/index.html` | `/` | Scrollytelling (pagina principal) |
| `docs/visualizacao.html` | `/visualizacao.html` | Dashboard interativo |
| `docs/apresentacao.html` | `/apresentacao.html` | Slides Reveal.js |

Todas as paginas incluem navegacao entre si. Para configurar:
Settings > Pages > Source: `master` branch, `/docs` folder.

## Versionamento

Este projeto segue [Semantic Versioning](https://semver.org/).
Mudancas documentadas em [CHANGELOG.md](CHANGELOG.md).

### Estrategia de branches

- **`master`** — branch principal, sempre deployavel via GitHub Pages
- **Tags** — cada release recebe tag `vX.Y.Z` (ex: `v0.6.0`)
- **Feature branches** — para novas funcionalidades, prefixo `feat/`
- **Fix branches** — para correcoes, prefixo `fix/`

```
master ─── v0.1.0 ─── v0.3.0 ─── v0.4.0 ─── v0.5.0 ─── v0.6.0
```
