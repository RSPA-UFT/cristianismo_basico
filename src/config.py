"""Settings loaded from .env via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider selection
    llm_provider: str = "ollama"  # "ollama", "openai", "anthropic"

    # Ollama
    ollama_model: str = "qwen2.5:14b"
    ollama_reasoning_model: str = "deepseek-r1:32b"
    ollama_base_url: str = "http://localhost:11434/v1"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # LLM parameters
    llm_temperature: float = 0.3
    llm_max_retries: int = 3

    # Paths
    project_dir: Path = Path(".")
    pdf_filename: str = "Cristianismo_Basico_John_Stott.pdf"
    output_dir: Path = Path("output")

    @property
    def pdf_path(self) -> Path:
        return self.project_dir / self.pdf_filename

    @property
    def chunks_dir(self) -> Path:
        return self.output_dir / "chunks"

    @property
    def per_chapter_dir(self) -> Path:
        return self.output_dir / "per_chapter"

    def ensure_output_dirs(self) -> None:
        self.output_dir.mkdir(exist_ok=True)
        self.chunks_dir.mkdir(exist_ok=True)
        self.per_chapter_dir.mkdir(exist_ok=True)


settings = Settings()
