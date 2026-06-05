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
    llm_timeout: int = 60
    llm_max_retries: int = 2

    log_level: str = "info"
    max_chunk_size: int = 512
    chunk_overlap: int = 50
    retrieval_top_k: int = 5
    max_upload_size_mb: int = 50

    postgres_dsn: str | None = None
    postgres_pool_min: int = 2
    postgres_pool_max: int = 10

    allowed_origins: list[str] = ["http://localhost:3000"]
    rate_limit_chat: str = "20/minute"
    rate_limit_ingest: str = "5/minute"
    trusted_proxies: int = 0
    workers: int = 1

    allowed_url_domains: str = ""

    app_env: str = "development"


settings = Settings()  # type: ignore[call-arg]  # pydantic-settings injecte les champs depuis les env vars
