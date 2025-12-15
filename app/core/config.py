from typing import List, Union
from pydantic import field_validator, model_validator
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
    BACKEND_CORS_ORIGINS: Union[List[str], str] = []

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
    ALLOWED_HOSTS: List[str] = ["localhost", "127.00.1"]

    # Security & JWT
    # Default is INSECURE for dev only
    SECRET_KEY: str = (
        "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """
        Fail-fast check to prevent using insecure default in production-like environments.
        This ensures we don't accidentally deploy with a known secret.
        """

        # Access ENVIRONMENT from the instance if possible, or assume 'local' if not yet validated
        # Note: field_validator context doesn't easily give access to other fields yet processed
        # unless using model_validator.
        # But we can check os.getenv for immediate fail-fast or rely on model_validator.
        # We will relax this check here and enforce strictness in model_validator.
        return v

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
            if not v_str or v_str == "*":
                # For backward compat in dev, if explicit "*" string is given, we might allow it
                # BUT validate_security logic below will strip it if credentials are enabled (which they are).
                # So here we just parse.
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

        is_production = self.ENVIRONMENT.lower() == "production"

        # 1. SECRET_KEY Check
        if is_production and self.SECRET_KEY == insecure_default:
            raise ValueError(
                "CRITICAL SECURITY ERROR: The application is running in PRODUCTION mode but uses the default insecure SECRET_KEY. "
                "You must set a secure SECRET_KEY in your environment variables."
            )

        # 2. CORS Wildcard Check
        # If allow_credentials is True (default in main.py), we strictly cannot allow wildcard '*'.
        # In production, we should be even stricter.
        if "*" in self.BACKEND_CORS_ORIGINS:
            if is_production:
                print(
                    "WARNING: wildcard '*' in BACKEND_CORS_ORIGINS is allowed in production. This is highly unsafe with credentials."
                )
                # Force disable in production
                raise ValueError(
                    "CRITICAL SECURITY ERROR: Wildcard CORS (*) is not allowed in production with credentials. Set explicit domains."
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

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False  # Set to True for SQL query logging (useful for debugging)

    @property
    def DATABASE_URL(self) -> str:
        """Construct async database URL from settings"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct sync database URL from settings (for Alembic and sync operations)"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
