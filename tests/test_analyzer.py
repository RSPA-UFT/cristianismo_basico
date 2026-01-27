"""Tests for src/analyzer.py -- utility functions, LLMClient, and ThesisAnalyzer.

Testing strategy:
- _extract_json and _strip_thinking_tags: direct unit tests with various inputs.
- LLMClient: mock the OpenAI / Anthropic constructors so no real connection is
  made; test the model_name property logic for each provider + override.
- ThesisAnalyzer: patch LLMClient.__init__ to avoid real connections, then
  patch the chat methods on the client / reasoning_client attributes to
  simulate LLM responses.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer import LLMClient, ThesisAnalyzer, _extract_json, _strip_thinking_tags
from src.config import Settings
from src.models import ChapterAnalysis, ChunkInfo, Citation, Thesis, ThesisChain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(tmp_path, provider="ollama", **overrides):
    """Build a minimal Settings object for tests."""
    defaults = dict(
        llm_provider=provider,
        output_dir=tmp_path / "output",
        ollama_model="qwen2.5:14b",
        ollama_reasoning_model="deepseek-r1:32b",
        ollama_base_url="http://localhost:11434/v1",
        openai_api_key="test-key",
        openai_model="gpt-4o",
        anthropic_api_key="test-key",
        anthropic_model="claude-sonnet-4-20250514",
        llm_temperature=0.3,
        llm_max_retries=3,
    )
    defaults.update(overrides)
    return Settings(**defaults)


def _thesis_response(theses=None, citations=None):
    """Return a JSON string that mimics the LLM thesis-extraction output."""
    payload = {
        "theses": theses or [
            {
                "id": "T1",
                "title": "Cristo afirmou ser Deus",
                "description": "Stott argumenta que Jesus fez afirmacoes de divindade.",
                "thesis_type": "main",
                "supporting_text": "Suas afirmacoes foram surpreendentes.",
                "citations": [
                    {"reference": "Jo 10:30", "text": "Eu e o Pai somos um", "citation_type": "biblical"}
                ],
                "confidence": 0.95,
            }
        ],
        "citations": citations or [
            {"reference": "Jo 10:30", "text": "Eu e o Pai somos um", "citation_type": "biblical"}
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _chain_response():
    """Return a JSON string that mimics the LLM chain-extraction output."""
    payload = {
        "chains": [
            {
                "from_thesis_id": "T1.1.1",
                "to_thesis_id": "T1.2.1",
                "relationship": "supports",
                "reasoning_type": "deductive",
                "explanation": "O carater moral de Cristo sustenta suas afirmacoes.",
                "strength": 0.8,
            }
        ],
        "argument_flow": "O livro segue uma progressao logica em 4 partes.",
    }
    return json.dumps(payload, ensure_ascii=False)


def _dedup_response(duplicates=None):
    """Return a JSON string for the dedup prompt response."""
    payload = {
        "duplicates": duplicates if duplicates is not None else [],
    }
    return json.dumps(payload, ensure_ascii=False)


def _correlation_response():
    """Return a JSON string for citation-correlation output."""
    payload = {
        "grouped_citations": [
            {
                "theme": "Cristologia",
                "description": "Passagens sobre a divindade de Cristo.",
                "references": ["Jo 10:30"],
                "related_thesis_ids": ["T1.1.1"],
            }
        ],
        "cross_references": [
            {
                "primary": "Jo 10:30",
                "related": ["Jo 14:9"],
                "connection": "Ambos atestam a unidade entre Pai e Filho.",
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _make_chunk(**overrides):
    """Build a minimal ChunkInfo for tests."""
    defaults = dict(
        index=0,
        title="Cap 1 - A Pessoa de Cristo",
        part="Parte 1",
        chapter="Capitulo 1",
        part_index=1,
        chapter_index=1,
        text="Texto do capitulo sobre a pessoa de Cristo." * 10,
        char_count=500,
        page_range="10-25",
        source="markdown_heading",
    )
    defaults.update(overrides)
    return ChunkInfo(**defaults)


# ---------------------------------------------------------------------------
# _extract_json tests
# ---------------------------------------------------------------------------


class TestExtractJson:
    """Tests for the _extract_json utility function."""

    def test_extract_json_code_block(self):
        """JSON wrapped in a ```json code block is correctly extracted."""
        inner = '{"key": "value"}'
        text = f"Some preamble\n```json\n{inner}\n```\nSome postamble"
        result = _extract_json(text)
        assert json.loads(result) == {"key": "value"}

    def test_extract_json_raw(self):
        """Raw JSON starting with '{' is returned as-is when valid."""
        text = '{"name": "test", "count": 42}'
        result = _extract_json(text)
        assert result == text
        assert json.loads(result) == {"name": "test", "count": 42}

    def test_extract_json_embedded(self):
        """JSON embedded in surrounding prose is extracted from first '{' to last '}'."""
        text = 'Here is the result: {"a": 1, "b": 2} hope that helps!'
        result = _extract_json(text)
        parsed = json.loads(result)
        assert parsed == {"a": 1, "b": 2}

    def test_extract_json_no_json(self):
        """When no JSON structure is present, the original text is returned."""
        text = "There is no JSON here at all, just plain text."
        result = _extract_json(text)
        assert result == text

    def test_extract_json_repair(self):
        """Malformed JSON (trailing comma) is repaired by json_repair."""
        # Trailing comma after last element is invalid JSON
        text = '{"items": [1, 2, 3,]}'
        result = _extract_json(text)
        parsed = json.loads(result)
        assert parsed["items"] == [1, 2, 3]

    def test_extract_json_code_block_no_lang(self):
        """A code block without the 'json' language tag is still extracted."""
        inner = '{"status": "ok"}'
        text = f"Output:\n```\n{inner}\n```"
        result = _extract_json(text)
        assert json.loads(result) == {"status": "ok"}


# ---------------------------------------------------------------------------
# _strip_thinking_tags tests
# ---------------------------------------------------------------------------


class TestStripThinkingTags:
    """Tests for the _strip_thinking_tags utility function."""

    def test_strip_thinking_simple(self):
        """A single inline <think> block is removed, leaving only the output."""
        text = "<think>reasoning here</think>actual output"
        assert _strip_thinking_tags(text) == "actual output"

    def test_strip_thinking_multiline(self):
        """A multiline <think> block is fully removed."""
        text = (
            "<think>\nStep 1: consider X\nStep 2: consider Y\n</think>\n"
            "Final answer is Z."
        )
        result = _strip_thinking_tags(text)
        assert result == "Final answer is Z."
        assert "<think>" not in result

    def test_strip_thinking_no_tags(self):
        """Text without <think> tags is returned unchanged (after strip)."""
        text = "  Just plain text  "
        assert _strip_thinking_tags(text) == "Just plain text"


# ---------------------------------------------------------------------------
# LLMClient tests (model_name property)
# ---------------------------------------------------------------------------


class TestLLMClientModelName:
    """Tests for LLMClient.model_name with different providers and overrides.

    We patch the OpenAI constructor and the anthropic import to avoid making
    real connections during __init__.
    """

    @patch("src.analyzer.OpenAI")
    def test_llm_client_model_name_ollama(self, mock_openai_cls, tmp_path):
        """With provider='ollama' and no override, model_name returns ollama_model."""
        settings = _make_settings(tmp_path, provider="ollama")
        client = LLMClient(settings)
        assert client.model_name == settings.ollama_model

    @patch("src.analyzer.OpenAI")
    def test_llm_client_model_name_override(self, mock_openai_cls, tmp_path):
        """model_override takes precedence over the provider-specific model."""
        settings = _make_settings(tmp_path, provider="ollama")
        client = LLMClient(settings, model_override="custom-model:7b")
        assert client.model_name == "custom-model:7b"

    @patch("src.analyzer.OpenAI")
    def test_llm_client_model_name_openai(self, mock_openai_cls, tmp_path):
        """With provider='openai', model_name returns openai_model."""
        settings = _make_settings(tmp_path, provider="openai")
        client = LLMClient(settings)
        assert client.model_name == settings.openai_model

    @patch("src.analyzer.OpenAI")
    def test_llm_client_model_name_anthropic(self, mock_openai_cls, tmp_path):
        """With provider='anthropic', model_name returns anthropic_model."""
        import sys

        settings = _make_settings(tmp_path, provider="anthropic")
        mock_anthropic_mod = MagicMock()
        mock_anthropic_mod.Anthropic.return_value = MagicMock()
        with patch.dict(sys.modules, {"anthropic": mock_anthropic_mod}):
            client = LLMClient(settings)
        assert client.model_name == settings.anthropic_model


# ---------------------------------------------------------------------------
# ThesisAnalyzer tests
# ---------------------------------------------------------------------------


class TestThesisAnalyzer:
    """Tests for ThesisAnalyzer methods with mocked LLM clients.

    We patch LLMClient.__init__ to avoid real connections, then replace
    the client and reasoning_client chat methods with mocks.
    """

    @pytest.fixture()
    def analyzer(self, tmp_path):
        """Return a ThesisAnalyzer with fully mocked LLM clients."""
        settings = _make_settings(tmp_path, provider="ollama")
        with patch.object(LLMClient, "__init__", lambda self, *a, **kw: None):
            ta = ThesisAnalyzer.__new__(ThesisAnalyzer)
            ta.settings = settings
            ta.max_retries = settings.llm_max_retries
            ta.client = LLMClient.__new__(LLMClient)
            ta.client.chat = MagicMock()
            ta.reasoning_client = LLMClient.__new__(LLMClient)
            ta.reasoning_client.chat = MagicMock()
        return ta

    # -- analyze_chunk -------------------------------------------------------

    def test_analyze_chunk_success(self, analyzer):
        """analyze_chunk parses a valid LLM response into a ChapterAnalysis."""
        analyzer.client.chat.return_value = _thesis_response()
        chunk = _make_chunk()

        result = analyzer.analyze_chunk(chunk)

        assert isinstance(result, ChapterAnalysis)
        assert result.chunk_title == chunk.title
        assert len(result.theses) == 1
        assert result.theses[0].title == "Cristo afirmou ser Deus"
        assert len(result.citations) == 1
        assert result.citations[0].reference == "Jo 10:30"

    def test_analyze_chunk_retry_on_failure(self, analyzer):
        """analyze_chunk retries and succeeds on the second attempt."""
        # First call returns garbage that fails JSON parsing; second call succeeds
        analyzer.client.chat.side_effect = [
            "this is not valid json at all",
            _thesis_response(),
        ]
        chunk = _make_chunk()

        result = analyzer.analyze_chunk(chunk)

        assert isinstance(result, ChapterAnalysis)
        assert len(result.theses) == 1
        assert analyzer.client.chat.call_count == 2

    def test_analyze_chunk_all_retries_fail(self, analyzer):
        """When all retries fail, analyze_chunk returns an empty ChapterAnalysis."""
        analyzer.client.chat.return_value = "not json {{{"
        chunk = _make_chunk()

        result = analyzer.analyze_chunk(chunk)

        assert isinstance(result, ChapterAnalysis)
        assert result.chunk_title == chunk.title
        assert result.theses == []
        assert result.citations == []
        assert analyzer.client.chat.call_count == analyzer.max_retries

    def test_analyze_chunk_thesis_ids(self, analyzer):
        """Thesis IDs follow the T{part_index}.{chapter_index}.{N} scheme."""
        two_theses = [
            {
                "id": "T1",
                "title": "First thesis",
                "description": "Desc 1",
                "thesis_type": "main",
                "supporting_text": "text1",
                "citations": [],
                "confidence": 0.9,
            },
            {
                "id": "T2",
                "title": "Second thesis",
                "description": "Desc 2",
                "thesis_type": "supporting",
                "supporting_text": "text2",
                "citations": [],
                "confidence": 0.85,
            },
        ]
        analyzer.client.chat.return_value = _thesis_response(theses=two_theses, citations=[])
        chunk = _make_chunk(part_index=2, chapter_index=3)

        result = analyzer.analyze_chunk(chunk)

        assert len(result.theses) == 2
        assert result.theses[0].id == "T2.3.1"
        assert result.theses[1].id == "T2.3.2"

    # -- extract_chains ------------------------------------------------------

    def test_extract_chains_success(self, analyzer):
        """extract_chains returns parsed ThesisChain objects and argument_flow."""
        analyzer.reasoning_client.chat.return_value = _chain_response()

        theses = [
            Thesis(id="T1.1.1", title="Thesis A", description="Desc A", chapter="Cap 1", part="Parte 1"),
            Thesis(id="T1.2.1", title="Thesis B", description="Desc B", chapter="Cap 2", part="Parte 1"),
        ]

        chains, flow = analyzer.extract_chains(theses)

        assert len(chains) == 1
        assert isinstance(chains[0], ThesisChain)
        assert chains[0].from_thesis_id == "T1.1.1"
        assert chains[0].to_thesis_id == "T1.2.1"
        assert chains[0].relationship == "supports"
        assert chains[0].strength == 0.8
        assert "progressao" in flow.lower() or len(flow) > 0

    def test_extract_chains_failure(self, analyzer):
        """When all retries fail, extract_chains returns empty lists."""
        analyzer.reasoning_client.chat.return_value = "completely broken output {{{"

        theses = [
            Thesis(id="T1.1.1", title="Thesis A", description="Desc A"),
        ]

        chains, flow = analyzer.extract_chains(theses)

        assert chains == []
        assert flow == ""
        assert analyzer.reasoning_client.chat.call_count == analyzer.max_retries

    # -- correlate_citations -------------------------------------------------

    def test_correlate_citations_success(self, analyzer):
        """correlate_citations returns grouped citations and cross-references."""
        analyzer.reasoning_client.chat.return_value = _correlation_response()

        citations = [
            Citation(reference="Jo 10:30", text="Eu e o Pai somos um", citation_type="biblical"),
        ]
        theses = [
            Thesis(
                id="T1.1.1",
                title="Divindade de Cristo",
                description="Desc",
                chapter="Cap 1",
                part="Parte 1",
                citations=citations,
            ),
        ]

        result = analyzer.correlate_citations(citations, all_theses=theses)

        assert "grouped_citations" in result
        assert len(result["grouped_citations"]) == 1
        assert result["grouped_citations"][0]["theme"] == "Cristologia"
        assert "cross_references" in result
        assert len(result["cross_references"]) == 1

    def test_correlate_citations_failure(self, analyzer):
        """When all retries fail, correlate_citations returns the empty fallback."""
        analyzer.reasoning_client.chat.return_value = "not parseable"

        citations = [
            Citation(reference="Rm 5:8", citation_type="biblical"),
        ]

        result = analyzer.correlate_citations(citations)

        assert result == {"grouped_citations": [], "cross_references": []}
        assert analyzer.reasoning_client.chat.call_count == analyzer.max_retries

    # -- _dedup_part ---------------------------------------------------------

    def test_dedup_part_removes_duplicates(self, analyzer):
        """_dedup_part filters out theses flagged as duplicates by the LLM."""
        duplicates = [
            {"remove_id": "T1.1.2", "keep_id": "T1.1.1", "reason": "Same thesis restated"}
        ]
        analyzer.reasoning_client.chat.return_value = _dedup_response(duplicates)

        theses = [
            {"id": "T1.1.1", "title": "Original thesis", "description": "Desc 1"},
            {"id": "T1.1.2", "title": "Duplicate thesis", "description": "Desc 2"},
            {"id": "T1.1.3", "title": "Unique thesis", "description": "Desc 3"},
        ]

        result = analyzer._dedup_part("Parte 1", theses)

        assert len(result) == 2
        kept_ids = {t["id"] for t in result}
        assert "T1.1.1" in kept_ids
        assert "T1.1.3" in kept_ids
        assert "T1.1.2" not in kept_ids

    def test_dedup_part_no_duplicates(self, analyzer):
        """When the LLM finds no duplicates, all theses are returned."""
        analyzer.reasoning_client.chat.return_value = _dedup_response(duplicates=[])

        theses = [
            {"id": "T1.1.1", "title": "Thesis A", "description": "Desc A"},
            {"id": "T1.1.2", "title": "Thesis B", "description": "Desc B"},
        ]

        result = analyzer._dedup_part("Parte 1", theses)

        assert len(result) == 2
        assert result == theses
