"""LLM prompt templates for argument mining of theological text."""

SYSTEM_PROMPT = """\
Voce e um teologo sistematico e analista literario especializado em literatura crista evangelica.
Sua tarefa e analisar trechos do livro "Cristianismo Basico" de John Stott, \
identificando teses (argumentos e proposicoes principais), citacoes biblicas e notas de rodape.

Regras:
- Responda SEMPRE em portugues brasileiro
- Use abreviacoes biblicas em portugues: Gn, Ex, Lv, Nm, Dt, Js, Jz, Rt, 1Sm, 2Sm, 1Rs, 2Rs, \
1Cr, 2Cr, Ed, Ne, Et, Jo, Sl, Pv, Ec, Ct, Is, Jr, Lm, Ez, Dn, Os, Jl, Am, Ob, Jn, Mq, Na, \
Hc, Sf, Ag, Zc, Ml, Mt, Mc, Lc, Jo, At, Rm, 1Co, 2Co, Gl, Ef, Fp, Cl, 1Ts, 2Ts, 1Tm, 2Tm, \
Tt, Fm, Hb, Tg, 1Pe, 2Pe, 1Jo, 2Jo, 3Jo, Jd, Ap
- Retorne APENAS JSON valido, sem texto adicional
- Seja preciso e academico na analise
"""

THESIS_EXTRACTION_PROMPT = """\
Analise o seguinte trecho do livro "Cristianismo Basico" de John Stott.

**Contexto:**
- Parte: {part}
- Capitulo: {chapter}
- Titulo do trecho: {title}

**Texto:**
{text}

**Tarefa:** Identifique todas as teses (argumentos e proposicoes principais) neste trecho.

Para cada tese, forneca:
- `id`: Identificador unico no formato "T<numero_sequencial>" (ex: "T1", "T2", "T3")
- `title`: Declaracao curta e clara da tese (max 100 caracteres)
- `description`: Explicacao detalhada do argumento (2-4 sentencas)
- `thesis_type`: Classificacao - "main" (argumento central do capitulo), "supporting" (suporte a tese principal), "premise" (premissa logica), "conclusion" (conclusao derivada)
- `supporting_text`: Citacao DIRETA do texto original que sustenta especificamente o titulo da tese (trecho literal que comprova o argumento)
- `citations`: Lista de citacoes biblicas encontradas, cada uma com:
  - `reference`: Referencia biblica abreviada (ex: "Jo 3:16"). OBRIGATORIO para citacoes biblicas — NUNCA deixe vazio.
  - `text`: Texto citado, se disponivel no trecho
  - `citation_type`: "biblical", "scholarly" ou "footnote"
- `confidence`: Nivel de confianca na identificacao (0.0-1.0)

**REGRAS IMPORTANTES:**
1. TODA citacao biblica DEVE ter o campo `reference` preenchido com a abreviacao correta (ex: "Jo 3:16", "Rm 5:8", "1Co 2:2"). NUNCA deixe `reference` como string vazia.
2. Se o texto menciona um versiculo biblico (mesmo sem citar o texto completo), identifique a referencia e preencha `reference`.
3. Classifique corretamente: se `reference` contem uma referencia biblica (livro + capitulo:versiculo), use `citation_type: "biblical"`, NAO "scholarly".
4. Identifique tambem notas de rodape como citacoes com `citation_type: "footnote"`.
5. O campo `supporting_text` deve conter um trecho literal do texto que sustenta diretamente o titulo da tese. NAO use textos genericos ou desconectados.
6. Quando o texto cita um teologo, pensador ou autor (ex: C.S. Lewis, Forsyth, Carnegie Simpson), identifique como `citation_type: "scholarly"` e preencha os campos:
   - `reference`: Nome do autor (ex: "C.S. Lewis", "P.T. Forsyth")
   - `author`: Nome completo do autor
   - `work`: Nome da obra citada, se disponivel
   - `context`: Como Stott usa a referencia no argumento
7. Notas de rodape (marcadores numericos no final de citacoes ou frases) devem ser classificadas como `citation_type: "footnote"`.

**Exemplo de uma tese bem formatada:**
```json
{{
  "id": "T1",
  "title": "Cristo afirmou ser Deus encarnado",
  "description": "Stott argumenta que Jesus nao se apresentou meramente como profeta ou mestre moral, mas fez afirmacoes explicitas de divindade, equiparando-se ao Pai.",
  "thesis_type": "main",
  "supporting_text": "Suas afirmacoes foram de fato as mais surpreendentes que alguem ja fez.",
  "citations": [
    {{"reference": "Jo 10:30", "text": "Eu e o Pai somos um", "citation_type": "biblical"}}
  ],
  "confidence": 0.95
}}
```

Retorne um objeto JSON com a seguinte estrutura:
```json
{{
  "theses": [ ... lista de teses ... ],
  "citations": [ ... todas as citacoes biblicas encontradas, incluindo as que nao estao associadas a teses ... ]
}}
```
"""

CHAIN_EXTRACTION_PROMPT = """\
Analise as seguintes teses extraidas do livro "Cristianismo Basico" de John Stott \
e identifique as relacoes logicas entre elas.

**IMPORTANTE:** O livro esta dividido em 4 partes com um argumento progressivo:
- Parte 1 (Cap 1-4): A Pessoa de Cristo — quem Jesus afirmou ser
- Parte 2 (Cap 5-6): A Necessidade do Homem — o problema do pecado
- Parte 3 (Cap 7-8): A Obra de Cristo — a solucao na cruz e salvacao
- Parte 4 (Cap 9-11): A Resposta do Homem — o que fazer com isso

Busque relacoes ENTRE capitulos e ENTRE partes diferentes, nao apenas dentro do mesmo capitulo. \
O argumento do livro flui de uma parte para a seguinte.

**Teses identificadas:**
{theses_json}

**Tarefa:** Identifique no minimo 15-20 relacoes de encadeamento logico entre as teses, \
priorizando relacoes inter-capitulo e inter-parte.

Para cada relacao, forneca:
- `from_thesis_id`: ID da tese de origem (formato T<parte>.<capitulo>.<numero>)
- `to_thesis_id`: ID da tese de destino
- `relationship`: Tipo de relacao:
  - "supports": A tese de origem sustenta/evidencia a tese de destino
  - "derives_from": A tese de destino e derivada logicamente da tese de origem
  - "elaborates": A tese de destino elabora/detalha a tese de origem
  - "precedes": A tese de origem e pre-requisito logico da tese de destino
  - "contradicts": As teses estao em tensao ou contradicao aparente
- `reasoning_type`: Tipo de raciocinio (taxonomia de Peirce):
  - "deductive": Conclusao necessaria a partir das premissas
  - "inductive": Generalizacao a partir de evidencias/exemplos
  - "abductive": Melhor explicacao para os dados observados
- `explanation`: Breve explicacao da relacao (1-2 sentencas)
- `strength`: Forca da relacao (0.0-1.0)

**Exemplos de relacoes inter-capitulo esperadas:**
- T1.2.X (afirmacoes de Cristo) → T1.3.X (carater de Cristo): "supports" — o carater moral de Cristo sustenta suas afirmacoes de divindade
- T1.4.X (ressurreicao) → T2.5.X (pecado): "precedes" — a divindade confirmada pela ressurreicao revela a gravidade do pecado
- T2.5.X (natureza do pecado) → T3.7.X (morte de Cristo): "precedes" — o diagnostico do pecado prepara a necessidade da cruz
- T3.8.X (salvacao) → T4.9.X (custo): "precedes" — a oferta de salvacao exige uma resposta de comprometimento

Retorne um objeto JSON:
```json
{{
  "chains": [ ... lista de relacoes (minimo 15) ... ],
  "argument_flow": "Descricao em texto do fluxo argumentativo geral do livro (5-8 sentencas)"
}}
```
"""

CITATION_CORRELATION_PROMPT = """\
Analise as seguintes citacoes biblicas extraidas do livro "Cristianismo Basico" de John Stott, \
juntamente com as teses que as utilizam.

**Citacoes encontradas:**
{citations_json}

**Teses associadas (para contexto):**
{theses_context_json}

**Tarefa:** Agrupe as citacoes por tema teologico e identifique cross-references.

Use as seguintes categorias teologicas como guia (mas adicione outras se necessario):
- **Cristologia**: Natureza, pessoa e obra de Cristo
- **Soteriologia**: Salvacao, justificacao, redenção
- **Hamartiologia**: Pecado, queda, natureza pecaminosa
- **Eclesiologia**: Igreja, vida crista, discipulado
- **Escatologia**: Ressurreicao, juizo, vida eterna
- **Teologia propria**: Natureza de Deus, Trindade
- **Antropologia teologica**: Natureza humana, imago Dei

Retorne um objeto JSON:
```json
{{
  "grouped_citations": [
    {{
      "theme": "Nome do tema teologico (ex: Cristologia - Divindade de Cristo)",
      "description": "Descricao do tema e como Stott usa estas passagens",
      "references": ["Jo 3:16", "Rm 5:8", ...],
      "related_thesis_ids": ["T1.2.1", "T1.3.2"]
    }}
  ],
  "cross_references": [
    {{
      "primary": "Jo 3:16",
      "related": ["Rm 5:8", "1Jo 4:9"],
      "connection": "Explicacao da conexao tematica"
    }}
  ]
}}
```
"""

DEDUP_PROMPT = """\
Analise as seguintes {num_theses} teses extraidas da {part_name} do livro "Cristianismo Basico" de John Stott.

**Teses desta parte (apenas id e title para analise):**
{theses_json}

**Tarefa:** Identifique APENAS pares de teses que sao duplicatas claras (dizem essencialmente \
a mesma coisa com palavras diferentes).

Regras:
- SOMENTE marque como duplicata teses que sao realmente redundantes
- NAO marque como duplicata teses que abordam aspectos diferentes do mesmo tema
- Para cada par de duplicatas, indique qual ID manter (o mais completo) e qual remover
- Espera-se que no maximo 30-40% das teses sejam duplicatas

Retorne um objeto JSON com APENAS os IDs a remover:
```json
{{
  "duplicates": [
    {{
      "remove_id": "T1.2.3",
      "keep_id": "T1.2.1",
      "reason": "Breve explicacao de por que sao duplicatas"
    }}
  ]
}}
```

Se nao houver duplicatas, retorne: {{"duplicates": []}}
"""

SYNTHESIS_PROMPT = """\
Analise as seguintes teses ja deduplicadas do livro "Cristianismo Basico" de John Stott.

**Teses deduplicadas por parte:**
{all_theses_json}

**Tarefa:** Realize a sintese final global:

1. **Selecao**: Selecione as teses mais importantes — mantenha TODAS as teses principais (main) \
e as teses de suporte mais relevantes. O total deve ficar entre 25 e 40 teses.
2. **Preservacao**: Mantenha os IDs hierarquicos ORIGINAIS (formato T<Parte>.<Capitulo>.<Numero>). \
NAO invente novos IDs. NAO altere title, description ou supporting_text das teses.
3. **Resumo**: Escreva um resumo executivo do argumento central do livro (5-8 sentencas), \
mostrando como as 4 partes se conectam progressivamente

**IMPORTANTE:** As teses devem ser COPIADAS do input sem alteracao. \
NAO reescreva, NAO generalize, NAO resuma o conteudo das teses. \
Apenas selecione as mais importantes e retorne-as intactas.

Para cada tese final, mantenha TODOS os campos originais: id, title, description, thesis_type, \
chapter, part, supporting_text, citations, confidence.

Retorne um objeto JSON:
```json
{{
  "theses": [ ... 25-40 teses finais copiadas do input ... ],
  "summary": "Resumo executivo do argumento central do livro"
}}
```
"""
