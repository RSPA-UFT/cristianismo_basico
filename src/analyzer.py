"""Multi-provider LLM integration with Pydantic validation and retry."""

import json
import logging
import re

from json_repair import repair_json
from openai import OpenAI

from .config import Settings
from .models import (
    BookAnalysis,
    ChapterAnalysis,
    ChunkInfo,
    Citation,
    Thesis,
    ThesisChain,
)
from .prompts import (
    CHAIN_EXTRACTION_PROMPT,
    CITATION_CORRELATION_PROMPT,
    DEDUP_PROMPT,
    SYNTHESIS_PROMPT,
    SYSTEM_PROMPT,
    THESIS_EXTRACTION_PROMPT,
)

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response, repairing common formatting issues."""
    # Try to find JSON in code blocks
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
    else:
        # Try to find raw JSON object/array
        text = text.strip()
        if text.startswith("{") or text.startswith("["):
            candidate = text
        else:
            # Last resort: find first { to last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                candidate = text[start : end + 1]
            else:
                return text

    # Try standard parsing first; if it fails, use json_repair
    try:
        json.loads(candidate)
        return candidate
    except json.JSONDecodeError:
        logger.debug("Standard JSON parse failed, attempting repair")
        repaired = repair_json(candidate, return_objects=False)
        return repaired


def _strip_thinking_tags(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models like DeepSeek-R1."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


class LLMClient:
    """Unified LLM client supporting Ollama, OpenAI, and Anthropic."""

    def __init__(self, settings: Settings, model_override: str | None = None) -> None:
        self.settings = settings
        self.provider = settings.llm_provider.lower()
        self._model_override = model_override
        self._openai_client: OpenAI | None = None
        self._anthropic_client = None

        if self.provider in ("ollama", "openai"):
            self._openai_client = self._create_openai_client()
        elif self.provider == "anthropic":
            import anthropic
            self._anthropic_client = anthropic.Anthropic(
                api_key=self.settings.anthropic_api_key
            )

    def _create_openai_client(self) -> OpenAI:
        if self.provider == "ollama":
            return OpenAI(
                base_url=self.settings.ollama_base_url,
                api_key="ollama",
                timeout=1800.0,  # 30 min — Ollama can be slow on large prompts
                max_retries=2,
            )
        return OpenAI(api_key=self.settings.openai_api_key)

    @property
    def model_name(self) -> str:
        if self._model_override:
            return self._model_override
        if self.provider == "ollama":
            return self.settings.ollama_model
        elif self.provider == "openai":
            return self.settings.openai_model
        elif self.provider == "anthropic":
            return self.settings.anthropic_model
        return ""

    def chat(self, system: str, user: str) -> str:
        """Send a chat completion request and return the response text."""
        if self.provider == "anthropic":
            return self._chat_anthropic(system, user)
        return self._chat_openai(system, user)

    def _chat_openai(self, system: str, user: str) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        kwargs: dict = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.settings.llm_temperature,
        }

        if self.provider == "openai":
            kwargs["response_format"] = {"type": "json_object"}

        response = self._openai_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def _chat_anthropic(self, system: str, user: str) -> str:
        response = self._anthropic_client.messages.create(
            model=self.model_name,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=self.settings.llm_temperature,
        )
        return response.content[0].text


class ThesisAnalyzer:
    """Orchestrates the 4-phase argument mining analysis."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = LLMClient(settings)
        # Reasoning client for phases 3b-3d (uses deepseek-r1 or similar)
        reasoning_model = (
            settings.ollama_reasoning_model
            if settings.llm_provider.lower() == "ollama"
            else None
        )
        self.reasoning_client = LLMClient(settings, model_override=reasoning_model)
        self.max_retries = settings.llm_max_retries
        logger.info(
            f"ThesisAnalyzer: extraction={self.client.model_name}, "
            f"reasoning={self.reasoning_client.model_name}"
        )

    def analyze_chunk(self, chunk: ChunkInfo) -> ChapterAnalysis:
        """Phase 3a: Extract theses and citations from a single chunk."""
        prompt = THESIS_EXTRACTION_PROMPT.format(
            part=chunk.part or "N/A",
            chapter=chunk.chapter or chunk.title,
            title=chunk.title,
            text=chunk.text[:10000],  # Truncate if too long for context
        )

        for attempt in range(self.max_retries):
            try:
                raw = self.client.chat(SYSTEM_PROMPT, prompt)
                data = json.loads(_extract_json(raw))

                # Build hierarchical ID prefix from chunk indices
                p_idx = chunk.part_index if chunk.part_index is not None else 0
                c_idx = chunk.chapter_index if chunk.chapter_index is not None else 0

                theses = [
                    Thesis(
                        id=f"T{p_idx}.{c_idx}.{i+1}",
                        title=t.get("title", ""),
                        description=t.get("description", ""),
                        thesis_type=t.get("thesis_type", "supporting"),
                        chapter=chunk.chapter or chunk.title,
                        part=chunk.part,
                        page_range=chunk.page_range,
                        supporting_text=t.get("supporting_text"),
                        citations=[
                            Citation(**c) for c in t.get("citations", [])
                        ],
                        confidence=float(t.get("confidence", 0.8)),
                    )
                    for i, t in enumerate(data.get("theses", []))
                ]

                citations = [
                    Citation(**c) for c in data.get("citations", [])
                ]

                logger.info(
                    f"Chunk '{chunk.title}': {len(theses)} theses, "
                    f"{len(citations)} citations"
                )
                return ChapterAnalysis(
                    chunk_title=chunk.title,
                    theses=theses,
                    citations=citations,
                )

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed for "
                    f"'{chunk.title}': {e}"
                )
                if attempt == self.max_retries - 1:
                    logger.error(f"All retries failed for chunk '{chunk.title}'")
                    return ChapterAnalysis(chunk_title=chunk.title)

        return ChapterAnalysis(chunk_title=chunk.title)

    def extract_chains(self, all_theses: list[Thesis]) -> tuple[list[ThesisChain], str]:
        """Phase 3b: Identify logical chains between theses."""
        # Build a JSON summary with description and supporting_text for context
        theses_summary = [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "type": t.thesis_type,
                "chapter": t.chapter,
                "part": t.part,
                "supporting_text": (t.supporting_text or "")[:200],
            }
            for t in all_theses
        ]

        prompt = CHAIN_EXTRACTION_PROMPT.format(
            theses_json=json.dumps(theses_summary, ensure_ascii=False, indent=2)
        )

        for attempt in range(self.max_retries):
            try:
                raw = self.reasoning_client.chat(SYSTEM_PROMPT, prompt)
                raw = _strip_thinking_tags(raw)
                data = json.loads(_extract_json(raw))

                chains = [
                    ThesisChain(**c) for c in data.get("chains", [])
                ]
                argument_flow = data.get("argument_flow", "")

                logger.info(f"Extracted {len(chains)} chains")
                return chains, argument_flow

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Chain extraction attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    return [], ""

        return [], ""

    def correlate_citations(
        self, all_citations: list[Citation], all_theses: list[Thesis] | None = None
    ) -> dict:
        """Phase 3c: Group citations by theme and find cross-references."""
        citations_data = [c.model_dump() for c in all_citations]

        # Build thesis context: id, title, and their citation references
        theses_context = []
        if all_theses:
            for t in all_theses:
                refs = [c.reference for c in t.citations] if t.citations else []
                if refs:
                    theses_context.append({
                        "id": t.id, "title": t.title, "part": t.part,
                        "chapter": t.chapter, "citation_refs": refs,
                    })

        prompt = CITATION_CORRELATION_PROMPT.format(
            citations_json=json.dumps(citations_data, ensure_ascii=False, indent=2),
            theses_context_json=json.dumps(
                theses_context, ensure_ascii=False, indent=2
            ),
        )

        for attempt in range(self.max_retries):
            try:
                raw = self.reasoning_client.chat(SYSTEM_PROMPT, prompt)
                raw = _strip_thinking_tags(raw)
                data = json.loads(_extract_json(raw))
                logger.info(
                    f"Citation correlation: {len(data.get('grouped_citations', []))} groups"
                )
                return data
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Citation correlation attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    return {"grouped_citations": [], "cross_references": []}

        return {"grouped_citations": [], "cross_references": []}

    def synthesize(
        self, chapter_analyses: list[ChapterAnalysis]
    ) -> tuple[list[Thesis], str]:
        """Phase 3d: Two-step synthesis — deduplicate per part, then global synthesis."""

        # Step 3d-i: Group theses by part and deduplicate each part separately
        theses_by_part: dict[str, list[dict]] = {}
        for analysis in chapter_analyses:
            for t in analysis.theses:
                part_key = t.part or "Sem parte"
                theses_by_part.setdefault(part_key, []).append(t.model_dump())

        deduped_all: list[dict] = []
        for part_name, part_theses in theses_by_part.items():
            logger.info(
                f"Phase 3d-i: Deduplicating {len(part_theses)} theses "
                f"from '{part_name}'"
            )
            deduped = self._dedup_part(part_name, part_theses)
            logger.info(
                f"  -> {len(deduped)} theses after deduplication"
            )
            deduped_all.extend(deduped)

        logger.info(
            f"Phase 3d-i complete: {len(deduped_all)} theses after per-part dedup"
        )

        # Step 3d-ii: Global synthesis over deduplicated theses
        deduped_by_part: dict[str, list[dict]] = {}
        for t in deduped_all:
            part_key = t.get("part", "Sem parte")
            deduped_by_part.setdefault(part_key, []).append(t)

        prompt = SYNTHESIS_PROMPT.format(
            all_theses_json=json.dumps(
                deduped_by_part, ensure_ascii=False, indent=2
            )
        )

        for attempt in range(self.max_retries):
            try:
                raw = self.reasoning_client.chat(SYSTEM_PROMPT, prompt)
                raw = _strip_thinking_tags(raw)
                data = json.loads(_extract_json(raw))

                theses = []
                for t in data.get("theses", []):
                    citations = [Citation(**c) for c in t.get("citations", [])]
                    theses.append(
                        Thesis(
                            id=t.get("id", ""),
                            title=t.get("title", ""),
                            description=t.get("description", ""),
                            thesis_type=t.get("thesis_type", "supporting"),
                            chapter=t.get("chapter", ""),
                            part=t.get("part", ""),
                            supporting_text=t.get("supporting_text"),
                            citations=citations,
                            confidence=float(t.get("confidence", 0.8)),
                        )
                    )

                summary = data.get("summary", "")
                logger.info(f"Synthesis: {len(theses)} final theses")
                return theses, summary

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Synthesis attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    # Fallback: return deduplicated theses as-is
                    fallback = []
                    for t in deduped_all:
                        citations = [Citation(**c) for c in t.get("citations", [])]
                        fallback.append(
                            Thesis(
                                id=t.get("id", ""),
                                title=t.get("title", ""),
                                description=t.get("description", ""),
                                thesis_type=t.get("thesis_type", "supporting"),
                                chapter=t.get("chapter", ""),
                                part=t.get("part", ""),
                                supporting_text=t.get("supporting_text"),
                                citations=citations,
                                confidence=float(t.get("confidence", 0.8)),
                            )
                        )
                    return fallback, ""

        return [], ""

    def _dedup_part(self, part_name: str, theses: list[dict]) -> list[dict]:
        """Deduplicate theses within a single part using the reasoning model.

        Sends only id+title to the LLM and asks which IDs to remove.
        Filtering is done in Python to preserve original data.
        """
        # Send only compact id+title list to minimize output issues
        compact = [{"id": t["id"], "title": t["title"]} for t in theses]

        prompt = DEDUP_PROMPT.format(
            part_name=part_name,
            num_theses=len(theses),
            theses_json=json.dumps(compact, ensure_ascii=False, indent=2),
        )

        for attempt in range(self.max_retries):
            try:
                raw = self.reasoning_client.chat(SYSTEM_PROMPT, prompt)
                raw = _strip_thinking_tags(raw)
                data = json.loads(_extract_json(raw))

                remove_ids = {
                    d["remove_id"] for d in data.get("duplicates", [])
                }
                if remove_ids:
                    logger.info(
                        f"  Removing {len(remove_ids)} duplicates: {remove_ids}"
                    )
                return [t for t in theses if t["id"] not in remove_ids]

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(
                    f"Dedup attempt {attempt + 1} for '{part_name}' failed: {e}"
                )
                if attempt == self.max_retries - 1:
                    return theses  # Fallback: return as-is

        return theses
