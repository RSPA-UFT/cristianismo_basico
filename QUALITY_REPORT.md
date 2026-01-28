# Relatorio de Qualidade - Analise Teologica

Data da execucao: 2026-01-26
Modelo de extracao: qwen2.5:14b (Ollama local)
Modelo de raciocinio: deepseek-r1:32b (Ollama local)
Modelo de sintese v1 (3b-3d): Claude Opus 4.5 (sobre dados qwen2.5)
Modelo de sintese v2 (re-extracao): Claude Opus 4.5 (diretamente dos textos originais)

---

## Metricas Quantitativas

| Metrica | qwen2.5 raw | deepseek-r1 | Claude v1 (sobre qwen) | Claude v2 (re-extracao) |
|---------|-------------|-------------|----------------------|------------------------|
| Teses extraidas | 117 | 16 (genericas) | 37 (selecionadas) | **52** (4-5/capitulo) |
| Citacoes biblicas | ~65 (+27% vazias) | 43 | 30 (limpas) | **169** (unicas, dedup) |
| Citacoes scholarly | 0 | 0 | 0 | **17** (autores identificados) |
| Notas de rodape | 0 | 0 | 0 | **detectadas** (detect_footnotes) |
| Chains logicas | — | 20 (IDs placeholder) | 29 (IDs reais) | **57** (IDs reais) |
| Grupos tematicos | — | 5 | 6 | **8** |
| Resumo executivo | — | VAZIO | 1.273 chars | **1.183 chars** |
| Fluxo argumentativo | — | VAZIO | 2.797 chars | **2.811 chars** |
| Supporting text | Parafrases LLM | Genericas | Parafrases Claude | **Citacoes exatas de Stott** |
| Refs vazias | ~32 (27%) | 0 | 0 | **0** |
| Artefatos OCR | 1 presente | — | Removido | **Nao presente** (re-extracao) |

---

## Issues de Qualidade Identificadas

### ALTA PRIORIDADE

#### 1. Sintese (3d-ii) produziu teses genericas
- **Problema:** O modelo deepseek-r1:32b gerou 16 teses genericas em vez de selecionar 25-40 das 115 teses deduplicadas
- **Evidencia:** Todas as 16 teses finais tem `supporting_text` identico a `description`, sem citacoes do texto original
- **Impacto:** As teses finais nao refletem os argumentos especificos de Stott
- **IDs afetados:** T1.1-T1.4, T2.1-T2.4, T3.1-T3.4, T4.1-T4.4 (IDs simplificados, nao hierarquicos)
- **Causa raiz:** O modelo nao seguiu a instrucao "COPIE as teses do input sem alteracao"
- **Sugestao:** Usar modelo mais capaz (gpt-4o, claude) ou implementar selecao em Python sem LLM

#### 2. Resumo executivo e fluxo argumentativo vazios
- **Problema:** `summary` e `argument_flow` retornaram strings vazias na sintese final
- **Evidencia:** report.md mostra "(Resumo nao disponivel)" e "(Fluxo nao disponivel)"
- **Causa raiz:** O modelo retornou JSON sem os campos `summary`/`argument_flow`, ou retornou string vazia
- **Sugestao:** Adicionar fallback que use o `argument_flow` de phase 3b (que foi extraido com sucesso)

#### 3. Chains usam IDs placeholder (T1.2.X)
- **Problema:** As 20 chains usam IDs como "T1.2.X" em vez de IDs reais de teses (ex: "T1.2.3")
- **Evidencia:** chains.json tem `from_thesis_id: "T1.2.X"` em todas as entradas
- **Causa raiz:** O modelo deepseek-r1 generalizou os IDs em vez de referenciar teses especificas
- **Sugestao:** Pos-processar chains para mapear IDs genericos aos IDs reais mais proximos

### MEDIA PRIORIDADE

#### 4. Referencias biblicas vazias na extracao (corrigido pela validacao)
- **Problema:** 27% das citacoes extraidas (phase 3a) tinham `reference: ""`
- **Status:** MITIGADO — validacao pos-processamento remove essas citacoes
- **Residual:** ~22 citacoes potencialmente validas foram descartadas por falta de referencia
- **Sugestao:** Melhorar prompt ou usar two-pass extraction (extrair + validar com LLM)

#### 5. Classificacao errada de citation_type
- **Problema:** Alguns versiculos biblicos classificados como "scholarly"
- **Evidencia:** citations.json contem `reference: "Mc"` com `citation_type: "scholarly"`
- **Status:** PARCIALMENTE MITIGADO — regex reclassifica referencias no formato "Livro N:N"
- **Residual:** Referencias incompletas (ex: "Mc" sem capitulo:versiculo) nao sao reclassificadas
- **Sugestao:** Ampliar regex ou usar lista de abreviacoes biblicas para reclassificacao

#### 6. Zero notas de rodape identificadas
- **Problema:** O livro tem notas de rodape, mas nenhuma foi classificada como `citation_type: "footnote"`
- **Evidencia:** Estatisticas do report.md: "Notas de rodape: 0"
- **Causa raiz:** O modelo nao distingue notas de rodape de citacoes no corpo do texto
- **Sugestao:** Pre-processar texto para marcar notas de rodape antes da extracao LLM

### BAIXA PRIORIDADE

#### 7. Artefatos OCR em citacoes
- **Problema:** 1 citacao contem texto ilegivel de OCR
- **Evidencia:** `reference: "-ne sunae anb onbe rsenn sood sdsoda..."`
- **Localizacao:** chunk_16 (Cap 7 - A Morte de Cristo, parte 1)
- **Sugestao:** Adicionar filtro de artefatos OCR no validador (detectar strings sem palavras validas)

#### 8. Referencias biblicas incompletas ou invalidas
- **Problema:** Algumas referencias nao seguem formato padrao
- **Exemplos:** `"Genesis"` (sem capitulo:versiculo), `"Cordeiro de Deus"` (nao e referencia), `"Co 5:7"` (deveria ser "1Co 5:7")
- **Sugestao:** Validar contra lista de abreviacoes biblicas canonicas

#### 9. Teses com supporting_text duplicado intra-chunk
- **Problema:** 4 pares de teses compartilham o mesmo supporting_text dentro do mesmo capitulo
- **Chunks afetados:** Cap 5 (T2.5.3), Cap 7 (T3.7.3, T3.7.4), Notas (T0.99.4)
- **Status:** DETECTADO e logado pelo validador, mas nao corrigido automaticamente
- **Sugestao:** Remover automaticamente a tese duplicada com menor confidence

---

## Comparacao: Antes vs Depois das Melhorias

| Aspecto | Antes (sem validacao) | Depois (com validacao) | Apos sintese Claude |
|---------|----------------------|----------------------|---------------------|
| Citacoes com ref vazia | ~32 (27%) | 0 (removidas) | 0 |
| Citacoes reclassificadas | 0 | Parcial (regex) | Total (manual) |
| Duplicatas detectadas | Nao verificado | 4 logadas | 80 removidas |
| Cache chapter_00 | Re-analisava toda vez | Cacheado corretamente | — |
| Prompt de extracao | Sem instrucoes de qualidade | 5 regras adicionadas | — |
| Teses finais | — | 117 (com duplicatas) | 37 (deduplicadas) |
| Resumo executivo | — | — | Substantivo (1.273 chars) |
| Fluxo argumentativo | — | — | 4 movimentos (2.797 chars) |
| Chain IDs | — | — | Reais (T1.2.2, etc.) |
| "Co 5:7" | Nao corrigido | Nao corrigido | Corrigido para "1Co 5:7" |
| Artefato OCR | Presente | Presente | Removido |
| "Mc" (incompleta) | Presente | Presente | Removida |

---

## Issues Resolvidas pela Sintese Claude

| Issue | Status |
|-------|--------|
| 1. Teses genericas (deepseek) | **RESOLVIDO** — 37 teses selecionadas das 117 originais |
| 2. Resumo/fluxo vazios | **RESOLVIDO** — resumo + fluxo argumentativo substantivos |
| 3. Chain IDs placeholder | **RESOLVIDO** — 29 chains com IDs reais |
| 4. Refs vazias | Ja mitigado (validador) |
| 5. Classificacao errada | **RESOLVIDO** — todas reclassificadas manualmente |
| 6. Zero notas de rodape | **RESOLVIDO** — detect_footnotes() + extract_footnotes_from_notes() |
| 7. Artefatos OCR | **RESOLVIDO** — removidos |
| 8. Refs incompletas | **RESOLVIDO** — corrigidas ("Co" → "1Co") |
| 9. Duplicatas intra-chunk | **RESOLVIDO** — deduplicacao global |

---

## Evolucao das Iteracoes

### Iteracao 1: Pipeline automatizado (qwen2.5 + deepseek-r1)
- Extracao por qwen2.5:14b produziu 117 teses com 27% de refs vazias
- Sintese por deepseek-r1:32b produziu 16 teses genericas, resumo/fluxo vazios, IDs placeholder
- **Limitacao fundamental:** modelos locais nao seguiram instrucoes complexas

### Iteracao 2: Sintese Claude v1 (sobre dados qwen2.5)
- Claude selecionou 37 das 117 teses, corrigiu IDs, escreveu resumo/fluxo
- **Limitacao:** trabalhou sobre dados ja comprometidos pela extracao qwen2.5
- Supporting text eram parafrases de Claude, nao citacoes de Stott

### Iteracao 3: Re-extracao Claude v2 (diretamente dos textos originais)
- Claude leu todos os 30 chunks originais e extraiu 52 teses com citacoes exatas
- 169 citacoes biblicas unicas (5.6x mais que v1)
- 57 chains logicas (2x mais que v1)
- 8 grupos tematicos de citacoes
- **Todas as teses tem supporting_text com citacoes diretas do texto de Stott**

### Iteracao 4: Citacoes Scholarly + Footnotes + Visualizacao + PDF/Slides
- **17 citacoes scholarly** extraidas (10 de notas de rodape, 7 inline)
- **Autores identificados:** Forsyth, Lewis, Thomas, Simpson, Denney, Orr, Machen, Latham, Studdert Kennedy, Archbishop Temple, John Stuart Mill, Carnegie Simpson, Charles Lamb, Emerson, Thomas Arnold, Sir Edward Clarke
- **detect_footnotes()** reclassifica refs numericas como `citation_type: "footnote"`
- **Modelo Citation ampliado** com campos `author`, `work`, `context` (backward-compatible)
- **Sankey diagram** (7a aba no dashboard) com fluxo inter-partes via d3-sankey
- **Export PNG/SVG** em todos os paineis do dashboard
- **Apresentacao Reveal.js** (`output/apresentacao.html`) com 10 slides
- **Relatorio HTML print-ready** (`output/relatorio.html`) para impressao/PDF
- **143 testes passando** (30 novos: scholarly, footnotes, slides, PDF, output, pipeline)

### Iteracao 5: Scrollytelling + GitHub Pages
- **Scrollytelling** (`output/scrollytelling.html`) — pagina narrativa com scroll progressivo
  - 12 secoes: Hero, Visao Geral, 4x(Intro+Teses por Parte), Rede Logica, Citacoes, Conclusao
  - Scrollama.js v3.2 (IntersectionObserver, 2.7KB) + D3.js v7
  - Layout sticky graphic + scrolling text (padrao NYT/The Pudding)
  - Mobile: layout stacked abaixo de 768px
  - Acessibilidade: `lang="pt-BR"`, `prefers-reduced-motion`, `aria-label`, formas+cores no grafo
  - Dados embutidos como JS constants (funciona offline)
  - Grafo D3 force-directed anima parte a parte, cross-part chains em dourado
  - Barras horizontais D3 por livro biblico com grupos tematicos
- **GitHub Pages** (`docs/`) — site publico com 3 paginas navegaveis
  - `docs/index.html` — scrollytelling (pagina principal)
  - `docs/visualizacao.html` — dashboard interativo
  - `docs/apresentacao.html` — slides Reveal.js
  - Navegacao `<nav>` entre as 3 paginas em cada HTML
- **src/scrollytelling.py** — modulo gerador (mesmo padrao de slides.py)
- **pipeline.py** atualizado com chamada `generate_scrollytelling()`
- **160 testes passando** (17 novos: criacao, estrutura, dados, secoes, acessibilidade, load)

### Iteracao 6: Identidade visual ICE + derivacao de IDs (v0.6.0)
- **Identidade visual ICE Metropolitana**: cor brand `#048fcc`, tipografia sans-serif, botoes arredondados
- **`derive_part_from_id()` / `derive_chapter_from_id()`** em models.py — preenchimento automatico de part/chapter via ID
- **Backfill** de campos `part` e `chapter` em `OutputWriter.save_book_analysis()`
- **Navegacao** Narrativa / Painel / Apresentacao em todas as paginas
- **Paleta de cores harmonizada**: `#048fcc`, `#dc3545`, `#fd7e14`, `#28a745`
- **176 testes passando** (16 novos)

### Iteracao 7: Correcoes de painel, slides e confianca (v0.7.0)
- **Unicode escapes corrigidos**: substituicao de `\u00XX` literal por caracteres UTF-8 reais em `docs/visualizacao.html`
- **Diacriticos portugueses completos**: todos os textos user-facing corrigidos (Analise→Análise, Citacoes→Citações, etc.)
- **TYPE_LABELS em portugues**: badges, tooltips e tabela traduzidos (main→principal, supporting→suporte, conclusion→conclusão, premise→premissa)
- **Aba "Confianca" separada**: grafico de confianca movido da Visao Geral para aba propria com texto explicativo
- **Paleta consistente**: `#3498db` substituido por `#048fcc` em todos os graficos
- **Contraste WCAG nos slides**: headings das partes usam cores escurecidas (`#036c9a`, `#b02a37`, `#c96209`, `#1e7b34`)
- **Overflow corrigido nos slides**: fluxo argumentativo dividido em sub-slides verticais (Reveal.js nested sections)
- **Citacoes academicas em 2 colunas** (grid layout) para caber em 1 slide
- **Resumo executivo truncado** (600 chars) com `max-height`/`overflow-y` como fallback
- **18 testes de auditoria HTML** (`tests/test_html_audit.py`): unicode escapes, diacriticos, labels ingleses, paleta, TYPE_LABELS, aba confianca, contraste, overflow, navegacao, lang/charset
- **199 testes passando** (23 novos: 18 auditoria + 5 slides)

### Iteracao 8: Slides, referencias biblicas, simplificacao do painel (v0.8.0)
- **Efeito "marca-texto" removido**: slides de partes usam `border-top` accent em vez de background tintado
- **Resumo executivo completo**: distribuido em multiplos sub-slides (sem truncamento)
- **Selo ICEB 125 anos**: logo embutido como base64 no slide de titulo
- **Aba "Referencias"**: nova aba no dashboard (tese → citacoes biblicas com busca/filtro)
- **Simplificacao**: abas "Fluxo Sankey" e "Confianca" removidas (7 abas total)
- **d3-sankey CDN removido**
- **206 testes passando** (7 novos)

### Iteracao 9: Acessibilidade da apresentacao para publicos variados (v0.9.0)
- **Tipografia aumentada**: h1 (2.2em), h2 (1.6em), body (0.9-1.0em) para WCAG compliance
- **Contraste melhorado**: subtitles/counts de #666/#888 para #333 (WCAG AA)
- **Slide de glossario**: 6 termos teologicos explicados (Impecabilidade, Pecado, Salvacao, Substituicao, Arrependimento, Reconciliacao)
- **Bullet points estruturados**: fluxo argumentativo com 5 sub-slides (overview + 4 movimentos com 3 bullets cada)
- **Icones visuais**: emojis nas 4 partes (👤⚠️✝️🙏)
- **Descricoes contextuais**: cada parte tem explicacao do seu proposito
- **ARIA semantico**: `role="region"`, `aria-label` no slide de titulo, alt text melhorado no logo
- **CSS acessivel**: `prefers-reduced-motion`, `prefers-contrast: more`, focus states
- **Responsividade**: media queries para mobile (<768px) e zoom alto (>1600px)
- **Reveal.js otimizado**: transicao `fade`, velocidade `slow`, slideNumber `c/t`
- **Backup preservado**: branch `backup/v0.8.0-presentation-original` mantem versao anterior
- **213 testes passando** (7 novos de acessibilidade)

---

## Recomendacoes Restantes

### Futura melhoria (se necessario)
1. ~~**Notas de rodape:**~~ **RESOLVIDO** — `detect_footnotes()` e `extract_footnotes_from_notes()` em src/validators.py e src/scholarly.py
2. **Integrar Claude como provedor LLM no pipeline** (adicionar suporte Anthropic API em analyzer.py para automatizar re-extracao)
3. ~~**Citacoes scholarly:**~~ **RESOLVIDO** — `extract_scholarly_citations()` em src/scholarly.py (17 citacoes com author/work/context)

---

## Arquivos de Referencia

### Output final (v2 + scholarly + scrollytelling + correcoes v0.7.0)
- Teses finais (52): `output/theses.json`
- Chains logicas (57): `output/chains.json`
- Citacoes (186 = 169 biblicas + 17 scholarly): `output/citations.json`
- Grupos de citacoes (8): `output/citation_groups.json`
- Relatorio Markdown: `output/report.md`
- Dashboard interativo (8 abas): `output/visualizacao.html`
- Apresentacao Reveal.js (10+ slides, com sub-slides verticais): `output/apresentacao.html`
- Relatorio HTML print-ready: `output/relatorio.html`
- Scrollytelling (12 secoes): `output/scrollytelling.html`

### GitHub Pages (docs/)
- Pagina principal (scrollytelling): `docs/index.html`
- Dashboard interativo: `docs/visualizacao.html`
- Apresentacao Reveal.js: `docs/apresentacao.html`

### Scripts e dados intermediarios
- Script de sintese v1: scratchpad `synthesize.py`
- Script de sintese v2: scratchpad `synthesize_v2.py`
- Teses por parte (v2): scratchpad `part[1-4]_theses.json`
- Teses por chunk (v1/qwen2.5): `output/per_chapter/chapter_*.json`

### Codigo-fonte
- Scholarly: `src/scholarly.py`
- Validador: `src/validators.py`
- Prompts: `src/prompts.py`
- Pipeline: `src/pipeline.py`
- PDF report: `src/pdf_report.py`
- Slides: `src/slides.py`
- Scrollytelling: `src/scrollytelling.py`
- Output: `src/output.py`
