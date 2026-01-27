# Estado da Sessao - Cristianismo Basico

Data: 2026-01-27
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
| `models.py` | Modelos Pydantic (Thesis, Citation, etc.) | OK |
| `extractor.py` | Extracao PDF 3-tier (Docling/PyMuPDF/Tesseract) | OK |
| `chunker.py` | Chunking hierarquico por capitulos/partes | OK |
| `analyzer.py` | Analise LLM (4 fases: 3a-3d) | OK |
| `prompts.py` | Templates de prompt para LLM | OK |
| `validators.py` | Validacao pos-processamento | OK |
| `output.py` | Geracao de output (JSON, Markdown) | OK |
| `pipeline.py` | Orquestrador dos 4 estagios | OK |

### Testes (tests/)
- **113 testes passando** (pytest, ~68s)
- Cobertura: conftest, models, config, extractor, chunker, analyzer, output, pipeline, validators
- Dependencias dev: pytest>=8.0, pytest-cov>=6.0

### Output Final (output/)
| Arquivo | Tamanho | Conteudo |
|---------|---------|----------|
| `theses.json` | 76 KB | 52 teses com citacoes exatas de Stott |
| `chains.json` | 15 KB | 57 cadeias logicas entre teses |
| `citations.json` | 32 KB | 169 citacoes biblicas unicas |
| `citation_groups.json` | 4 KB | 8 grupos tematicos |
| `report.md` | 55 KB | Relatorio completo em Markdown |
| `visualizacao.html` | 138 KB | Dashboard interativo (6 abas, D3.js + Chart.js) |
| `extracted_text.md` | 265 KB | Texto bruto extraido do PDF |
| `chunks/` | 30 arquivos | Chunks Markdown por capitulo |
| `per_chapter/` | 30 JSONs | Analises por capitulo (cache pipeline) |

### Documentacao
| Arquivo | Conteudo |
|---------|----------|
| `README.md` | Documentacao do projeto (instalacao, uso, arquitetura) |
| `QUALITY_REPORT.md` | Relatorio de qualidade com 3 iteracoes documentadas |
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
- Este e o output final atual

---

## Visualizacao (output/visualizacao.html)

Dashboard HTML auto-contido com 6 abas:
1. **Visao Geral** - Donut charts (distribuicao por parte, raciocinio) + barras (capitulos, confianca)
2. **Rede Logica** - Grafo D3.js force-directed (52 nos, 57 arestas, drag/zoom/hover/click)
3. **Hierarquia** - Arvore colapsavel D3.js (Livro > Parte > Capitulo > Tese)
4. **Citacoes Biblicas** - Barras por livro biblico (AT/NT) e por grupo tematico
5. **Fluxo Argumentativo** - 4 movimentos do argumento em HTML formatado
6. **Dados** - Tabela pesquisavel com todas as 52 teses

Cores por parte: P1=#4682B4 (azul), P2=#DC143C (vermelho), P3=#FF8C00 (laranja), P4=#228B22 (verde)
CDNs: D3.js v7, Chart.js v4

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

### Melhorias na Visualizacao
- Diagrama Sankey (fluxo argumentativo visual entre partes)
- Exportar graficos como PNG/SVG
- Versao em PDF do relatorio com graficos embutidos
- Modo de apresentacao (slides)

### Melhorias no Conteudo
- Extrair citacoes de teologos (C.S. Lewis, etc.) como `citation_type: "scholarly"`
- Identificar notas de rodape (`citation_type: "footnote"`)
- Adicionar provedor Anthropic/OpenAI ao pipeline automatizado (src/analyzer.py)

### Infraestrutura
- Inicializar repositorio git
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
uv run pytest tests/ -q      # 113 passed

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
