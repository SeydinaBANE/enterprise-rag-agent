from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    openrouter_api_key: str
    api_key: str

    chroma_host: str = "localhost"
    chroma_port: int = 8001

    llm_model: str = "openai/gpt-4o-mini"
    embedding_model: str = "openai/text-embedding-3-small"

    log_level: str = "info"
    max_chunk_size: int = 512
    chunk_overlap: int = 50
    retrieval_top_k: int = 5

    otel_endpoint: str | None = None
    postgres_dsn: str | None = None

    allowed_origins: list[str] = ["*"]
    rate_limit_chat: str = "20/minute"
    rate_limit_ingest: str = "5/minute"


settings = Settings()  # type: ignore[call-arg]  # fields come from env vars
