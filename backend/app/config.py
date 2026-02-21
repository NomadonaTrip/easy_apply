from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root directory (Easy_Apply/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "easy_apply"
    debug: bool = False
    testing: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # LLM Provider Configuration
    llm_provider: Literal["gemini", "claude"] = "gemini"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.0-flash-exp"
    llm_model_gen: str = ""  # Override model for generation (resume/cover letter)

    # Tool API Keys
    serper_api_key: str | None = None  # For web search tool

    @property
    def database_url(self) -> str:
        """SQLite database URL."""
        if self.testing:
            return f"sqlite+aiosqlite:///{DATA_DIR}/test_easy_apply.db"
        return f"sqlite+aiosqlite:///{DATA_DIR}/easy_apply.db"

    @property
    def tool_config(self) -> dict:
        """Configuration for LLM tools."""
        config = {
            "web_fetch": {},
        }
        if self.serper_api_key:
            config["web_search"] = {"api_key": self.serper_api_key}
        return config


settings = Settings()
