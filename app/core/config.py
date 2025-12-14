from typing import List, Union
from pydantic import field_validator
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

    # CORS - Can be a comma-separated string or JSON array in .env file
    # Example: BACKEND_CORS_ORIGINS=["*"] or BACKEND_CORS_ORIGINS=*
    # Defaults to ["*"] if not provided
    # Use Union to allow both string and list, preventing JSON parsing errors
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = "*"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    UPLOAD_DIR: str = "uploads"

    # Security & JWT
    SECRET_KEY: str = (
        "your-secret-key-change-this-in-production-use-openssl-rand-hex-32"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

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

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from various formats"""
        # If value is None or empty, return default
        if v is None:
            return ["*"]

        # If it's already a list, return it
        if isinstance(v, list):
            return v

        # Handle string values
        if isinstance(v, str):
            v = v.strip()
            # Handle empty string
            if not v:
                return ["*"]

            # Handle comma-separated string: "http://localhost:3000,http://localhost:8000"
            # Or single value: "*"
            if v == "*":
                return ["*"]
            # Split by comma and strip whitespace
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
            return origins if origins else ["*"]

        # Fallback to default
        return ["*"]

    @property
    def DATABASE_URL(self) -> str:
        """Construct async database URL from settings"""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct sync database URL from settings (for Alembic and sync operations)"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
