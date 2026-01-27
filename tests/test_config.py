"""Tests for src.config.Settings.

Covers default values, computed path properties, directory creation,
and environment-variable overrides via monkeypatch.
"""

from pathlib import Path

import pytest

from src.config import Settings


# ---------------------------------------------------------------------------
# 1. Default values
# ---------------------------------------------------------------------------
class TestDefaults:
    """Verify that a freshly constructed Settings object exposes the
    expected default values for every field."""

    def test_default_values(self):
        s = Settings()

        assert s.llm_provider == "ollama"
        assert s.ollama_model == "qwen2.5:14b"
        assert s.ollama_reasoning_model == "deepseek-r1:32b"
        assert s.ollama_base_url == "http://localhost:11434/v1"
        assert s.openai_api_key == ""
        assert s.openai_model == "gpt-4o"
        assert s.anthropic_api_key == ""
        assert s.anthropic_model == "claude-sonnet-4-20250514"
        assert s.llm_temperature == pytest.approx(0.3)
        assert s.llm_max_retries == 3
        assert s.project_dir == Path(".")
        assert s.pdf_filename == "Cristianismo_Basico_John_Stott.pdf"
        assert s.output_dir == Path("output")


# ---------------------------------------------------------------------------
# 2. pdf_path property
# ---------------------------------------------------------------------------
class TestPdfPath:
    """The pdf_path property must combine project_dir and pdf_filename."""

    def test_pdf_path_default(self):
        s = Settings()
        expected = Path(".") / "Cristianismo_Basico_John_Stott.pdf"
        assert s.pdf_path == expected

    def test_pdf_path_with_custom_project_dir(self, tmp_path: Path):
        s = Settings(project_dir=tmp_path, pdf_filename="book.pdf")
        assert s.pdf_path == tmp_path / "book.pdf"


# ---------------------------------------------------------------------------
# 3. chunks_dir property
# ---------------------------------------------------------------------------
class TestChunksDir:
    """chunks_dir must always resolve to output_dir / 'chunks'."""

    def test_chunks_dir_default(self):
        s = Settings()
        assert s.chunks_dir == Path("output") / "chunks"

    def test_chunks_dir_with_custom_output(self, tmp_path: Path):
        s = Settings(output_dir=tmp_path)
        assert s.chunks_dir == tmp_path / "chunks"


# ---------------------------------------------------------------------------
# 4. per_chapter_dir property
# ---------------------------------------------------------------------------
class TestPerChapterDir:
    """per_chapter_dir must always resolve to output_dir / 'per_chapter'."""

    def test_per_chapter_dir_default(self):
        s = Settings()
        assert s.per_chapter_dir == Path("output") / "per_chapter"

    def test_per_chapter_dir_with_custom_output(self, tmp_path: Path):
        s = Settings(output_dir=tmp_path)
        assert s.per_chapter_dir == tmp_path / "per_chapter"


# ---------------------------------------------------------------------------
# 5. ensure_output_dirs creates the directory tree
# ---------------------------------------------------------------------------
class TestEnsureOutputDirs:
    """ensure_output_dirs must create output_dir, chunks, and per_chapter
    sub-directories on disk, and must be safe to call more than once."""

    def test_creates_directories(self, tmp_path: Path):
        out = tmp_path / "generated_output"
        s = Settings(output_dir=out)

        # Directories should not exist yet.
        assert not out.exists()

        s.ensure_output_dirs()

        assert out.is_dir(), "output_dir was not created"
        assert (out / "chunks").is_dir(), "chunks sub-directory was not created"
        assert (out / "per_chapter").is_dir(), "per_chapter sub-directory was not created"

    def test_idempotent(self, tmp_path: Path):
        """Calling ensure_output_dirs twice must not raise."""
        out = tmp_path / "idempotent_output"
        s = Settings(output_dir=out)

        s.ensure_output_dirs()
        s.ensure_output_dirs()  # second call -- should not raise

        assert out.is_dir()
        assert (out / "chunks").is_dir()
        assert (out / "per_chapter").is_dir()


# ---------------------------------------------------------------------------
# 6. Override via environment variables (monkeypatch)
# ---------------------------------------------------------------------------
class TestEnvVarOverrides:
    """pydantic-settings should pick up upper-cased environment variables
    and use them instead of the coded defaults."""

    def test_llm_provider_override(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        s = Settings()
        assert s.llm_provider == "openai"

    def test_multiple_overrides(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("OLLAMA_MODEL", "llama3:8b")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.9")
        monkeypatch.setenv("LLM_MAX_RETRIES", "5")

        s = Settings()

        assert s.ollama_model == "llama3:8b"
        assert s.llm_temperature == pytest.approx(0.9)
        assert s.llm_max_retries == 5


# ---------------------------------------------------------------------------
# 7. Custom output_dir passed directly
# ---------------------------------------------------------------------------
class TestCustomOutputDir:
    """When output_dir is supplied at construction time the derived path
    properties and ensure_output_dirs must all honour it."""

    def test_custom_output_dir_propagates(self, tmp_path: Path):
        custom = tmp_path / "my_output"
        s = Settings(output_dir=custom)

        assert s.output_dir == custom
        assert s.chunks_dir == custom / "chunks"
        assert s.per_chapter_dir == custom / "per_chapter"

        s.ensure_output_dirs()

        assert custom.is_dir()
        assert (custom / "chunks").is_dir()
        assert (custom / "per_chapter").is_dir()
