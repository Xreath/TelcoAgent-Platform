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

    # MongoDB
    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_db: str = "telco_episodic"

    @property
    def mongo_url(self) -> str:
        return f"mongodb://{self.mongo_host}:{self.mongo_port}"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    schema_registry_url: str = "http://localhost:8081"

    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "telco-agents"
    keycloak_client_id: str = "customer-service"
    keycloak_client_secret: str = "change-me"

    # LLM (DeepSeek — OpenAI compatible)
    openai_api_base: str = "https://api.deepseek.com/v1"
    openai_api_key: str = "your-deepseek-api-key"

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = "your-langsmith-key"
    langchain_project: str = "telco-agent-platform"

    # Observability
    jaeger_endpoint: str = "http://localhost:14268/api/traces"


@lru_cache
def get_settings() -> Settings:
    return Settings()
