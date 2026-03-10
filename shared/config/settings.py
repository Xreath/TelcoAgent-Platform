"""Shared configuration — loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Local Dev
    dev_mode: bool = False

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "telco"
    postgres_password: str = "telco_secret"
    postgres_db: str = "telcoagent"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"

    # JWT Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # LLM (DeepSeek — OpenAI compatible)
    openai_api_base: str = "https://api.deepseek.com/v1"
    openai_api_key: str = "your-deepseek-api-key"

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = "your-langsmith-key"
    langchain_project: str = "telco-agent-platform"

    # Service URLs
    customer_service_url: str = "http://localhost:8001/v1/customers"
    billing_service_url: str = "http://localhost:8002/v1/billing"
    network_service_url: str = "http://localhost:8003/v1/network"
    campaign_service_url: str = "http://localhost:8004/v1/campaigns"



@lru_cache
def get_settings() -> Settings:
    return Settings()
