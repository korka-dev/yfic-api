from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from pydantic import field_validator
from pydantic_settings import BaseSettings


def _to_asyncpg_url(url: str) -> str:
    """Convert a postgresql:// URL (sslmode=...) into an asyncpg-compatible one (ssl=...)."""
    parts = urlsplit(url)
    scheme = "postgresql+asyncpg"
    query = dict(parse_qsl(parts.query))
    query.pop("sslmode", None)
    query.pop("channel_binding", None)
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    database_url: str
    cors_origins: str = "http://localhost:3000"
    secret_key: str = "change-me-in-production"
    admin_email: str = "admin@yfic.com"
    admin_password: str = "yfic-admin-2026"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    resend_api_key: str = ""
    store_email: str = "noreply@yfic.com"
    store_name: str = "YFIC"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    env: str = "development"  # set to "production" in prod deployment

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v in ("change-me-in-production", ""):
            raise ValueError(
                "SECRET_KEY must be set to a strong random value — "
                "generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @property
    def async_database_url(self) -> str:
        return _to_asyncpg_url(self.database_url)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    class Config:
        env_file = ".env"


settings = Settings()
