from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./investigation.db"
    jwt_secret: str = Field(min_length=32)
    token_minutes: int = Field(default=45, ge=5, le=120)
    corpus_path: Path = Path(__file__).resolve().parents[3] / "data" / "law_corpus" / "sections.json"
    tesseract_binary: str = "tesseract"
    pdf_image_binary: str = "pdftoppm"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    embedding_model: str = ""
    allowed_origin: str = "http://localhost:5173"

    @field_validator("ollama_url")
    @classmethod
    def local_model_only(cls, value: str) -> str:
        from urllib.parse import urlsplit

        url = urlsplit(value)
        if (
            url.scheme != "http"
            or url.hostname not in {"localhost", "127.0.0.1", "::1", "ollama"}
            or url.username
            or url.password
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError("Use loopback or the internal Compose Ollama service.")
        return value.rstrip("/")
