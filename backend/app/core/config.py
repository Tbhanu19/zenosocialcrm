"""Environment-backed application settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRET_KEYS = frozenset(
    {
        "",
        "change-me",
        "replace-with-a-long-random-string",
        "secret",
        "test",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="mysql+pymysql://USER:PASSWORD@localhost:3306/zenosocialcrm?charset=utf8mb4",
    )
    secret_key: str = Field(default="replace-with-a-long-random-string")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    environment: str = "development"

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def expose_api_docs(self) -> bool:
        return not self.is_production

    def validate_runtime(self) -> None:
        if not self.is_production:
            return
        if self.secret_key.strip().lower() in _INSECURE_SECRET_KEYS or len(self.secret_key) < 32:
            raise RuntimeError("SECRET_KEY must be a strong unique value in production.")
        if "*" in self.cors_origin_list:
            raise RuntimeError("CORS origins cannot include '*' in production.")
        if not self.cors_origin_list:
            raise RuntimeError("CORS_ORIGINS must list explicit origins in production.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    return settings
