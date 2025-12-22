from typing import List, Union
import json
from pydantic import field_validator, model_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_parse_none_str=True,
    )

    PROJECT_NAME: str = "FastAPI App"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS Configuration
    # This controls which frontend sites can talk to your API.
    # You can list them here (comma-separated or JSON list).
    # Examples:
    #   - BACKEND_CORS_ORIGINS=["http://localhost:3000"]
    #   - BACKEND_CORS_ORIGINS=["https://app.yourdomain.com"]
    #
    # Note: In production, for security, you must list specific domains.
    # Don't use "*" because it's not safe when cookies/credentials are involved.
    BACKEND_CORS_ORIGINS: List[str] = []

    # Advanced CORS: Subdomain Support
    # Use this if you have dynamic subdomains like tenant1.yourdomain.com.
    # It takes a Regex pattern (e.g., ^https://.*\.yourdomain\.com$).
    BACKEND_CORS_ORIGIN_REGEX: Union[str, None] = None

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    UPLOAD_DIR: str = "uploads"

    # Environment
    ENVIRONMENT: str = "local"  # local, staging, production
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]

    # Security & JWT
    # Default is INSECURE for dev only
    SECRET_KEY: str = (
        "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        if v is None:
            return ["localhost", "127.0.0.1"]
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return ["localhost", "127.0.0.1"]
            return [host.strip() for host in v_str.split(",") if host.strip()]
        return ["localhost", "127.0.0.1"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Strictly parse CORS origins into a List[str].
        Validates wildcards against credential usage.
        """
        origins: List[str] = []

        if v is None:
            origins = []
        elif isinstance(v, list):
            origins = v
        elif isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []

            # Try parsing as JSON first
            try:
                parsed = json.loads(v_str)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

            # Fallback to comma-separated
            if v_str == "*":
                origins = ["*"]
            else:
                origins = [
                    origin.strip() for origin in v_str.split(",") if origin.strip()
                ]

        if not origins:
            return []

        return origins

    @model_validator(mode="after")
    def validate_security_config(self) -> "Settings":
        """
        Post-init validation for cross-field security checks.
        """
        insecure_default = (
            "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
        )

        is_sensitive_env = self.ENVIRONMENT.lower() not in {"local", "test"}

        # 1. SECRET_KEY Check
        if is_sensitive_env and self.SECRET_KEY == insecure_default:
            raise ValueError("SECRET_KEY must be overridden in non-local environments")

        # 2. CORS Wildcard Check
        # If allow_credentials is True (default in main.py), we strictly cannot allow wildcard '*'.
        # In sensitive environments, we should be even stricter.
        if "*" in self.BACKEND_CORS_ORIGINS:
            if is_sensitive_env:
                # Force disable in production/staging
                raise ValueError(
                    "Wildcard CORS (*) forbidden in sensitive environments"
                )

            print(
                "WARNING: wildcard '*' in BACKEND_CORS_ORIGINS is unsafe with credentials. Disabling CORS."
            )
            self.BACKEND_CORS_ORIGINS = []

        return self

    # Database
    # For local development, use "localhost"
    # For Docker, use "postgres" (service name)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "erp_db"
    POSTGRES_HOST: str = "localhost"  # Default to localhost for local development
    POSTGRES_PORT: str = "5432"

    # Direct URL Override (e.g. for Neon, Railway, Heroku)
    # If this is set, it takes precedence over the components above.
    DATABASE_URL_OVERRIDE: Union[str, None] = Field(
        default=None, validation_alias="DATABASE_URL"
    )

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False  # Set to True for SQL query logging (useful for debugging)

    @property
    def DATABASE_URL(self) -> str:
        """Construct async database URL from settings"""
        if self.DATABASE_URL_OVERRIDE:
            # Ensure we are using asyncpg driver
            if (
                "postgresql://" in self.DATABASE_URL_OVERRIDE
                and "postgresql+asyncpg" not in self.DATABASE_URL_OVERRIDE
            ):
                return self.DATABASE_URL_OVERRIDE.replace(
                    "postgresql://", "postgresql+asyncpg://"
                )
            return self.DATABASE_URL_OVERRIDE

        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct sync database URL from settings (for Alembic and sync operations)"""
        if self.DATABASE_URL_OVERRIDE:
            # Ensure we are NOT using asyncpg driver for sync
            url = self.DATABASE_URL_OVERRIDE.replace(
                "postgresql+asyncpg://", "postgresql://"
            )
            # Fix SSL info for psycopg2 (expects sslmode=, asyncpg expects ssl=)
            # We replace common query param patterns
            url = url.replace("?ssl=", "?sslmode=")
            url = url.replace("&ssl=", "&sslmode=")
            return url

        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
