# Cristianismo Basico - Analise Teologica com LLM

Pipeline de extracao e analise automatizada de teses teologicas do livro
"Cristianismo Basico" de John Stott, usando argument mining com LLMs.

## Funcionalidades

- Extracao de texto de PDF (3-tier: Docling, PyMuPDF, Tesseract OCR)
- Chunking hierarquico por capitulos e partes do livro
- Extracao de teses, citacoes biblicas e notas com LLMs
- Identificacao de cadeias logicas entre teses
- Correlacao tematica de citacoes biblicas
- Sintese e deduplicacao de teses
- Validacao pos-processamento de citacoes e referencias
- Geracao de relatorio em Markdown

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
| `output/theses.json` | Teses finais consolidadas |
| `output/chains.json` | Cadeias logicas entre teses |
| `output/citations.json` | Todas as citacoes |
| `output/citation_groups.json` | Citacoes agrupadas por tema |
| `output/report.md` | Relatorio legivel em Markdown |

## Testes

```bash
uv sync --extra dev
uv run pytest tests/ -v
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```

## Arquitetura

```
src/
  __main__.py    - Entry point CLI
  pipeline.py    - Orquestrador 4 estagios
  extractor.py   - Extracao PDF (3-tier)
  chunker.py     - Chunking hierarquico
  analyzer.py    - Analise LLM (4 fases)
  validators.py  - Validacao pos-processamento
  models.py      - Modelos Pydantic
  prompts.py     - Templates de prompt
  output.py      - Geracao de output
  config.py      - Configuracao via .env
```

### Pipeline (4 estagios)

1. **Extracao PDF** - Extrai texto do PDF usando Docling, PyMuPDF ou Tesseract
2. **Chunking** - Divide texto em ~30 chunks por capitulos/secoes
3. **Analise LLM** (4 fases):
   - 3a: Extracao de teses e citacoes por chunk
   - 3b: Identificacao de cadeias logicas entre teses
   - 3c: Correlacao tematica de citacoes biblicas
   - 3d: Deduplicacao e sintese final
4. **Output** - Gera JSON estruturado e relatorio Markdown
