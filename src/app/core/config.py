from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SpecForge AI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./specforge.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 1800
    DATABASE_ECHO: bool = False
    MIGRATION_MODE: str = "create_all"  # create_all for legacy/dev; alembic for production
    SECRET_KEY: str = "dev-only-change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: str = "http://127.0.0.1:8000,http://localhost:8000"
    AI_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5.6-luna"
    OPENAI_BASE_URL: str = ""
    LOCAL_LLM_URL: str = ""
    LOCAL_LLM_MODEL: str = "local-model"
    LOCAL_LLM_TIMEOUT_SECONDS: int = 120
    AI_KNOWLEDGE_LIMIT: int = 25
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"  # text or json
    LOG_FILE: str = ""
    ENABLE_SCHEDULER: bool = False
    SCHEDULER_INTERVAL_MINUTES: int = 15
    TRUSTED_PROXY_COUNT: int = 0
    TRUSTED_HOSTS: str = "127.0.0.1,localhost,testserver"
    GIT_ALLOWED_ROOTS: str = ""
    BACKUP_DIR: str = "./backups"
    BACKUP_RETENTION_DAYS: int = 14
    BACKUP_RETENTION_COUNT: int = 20
    ENABLE_BACKUP_SCHEDULER: bool = False
    BACKUP_INTERVAL_HOURS: int = 24

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def git_allowed_roots(self) -> list[str]:
        return [item.strip() for item in self.GIT_ALLOWED_ROOTS.split(",") if item.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [item.strip() for item in self.TRUSTED_HOSTS.split(",") if item.strip()]

    def validate_security(self) -> None:
        environment = self.ENVIRONMENT.lower().strip()

        if self.TRUSTED_PROXY_COUNT < 0:
            raise RuntimeError("TRUSTED_PROXY_COUNT cannot be negative")
        if not 5 <= self.ACCESS_TOKEN_EXPIRE_MINUTES <= 1440:
            raise RuntimeError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 5 and 1440 minutes")
        if not self.trusted_hosts:
            raise RuntimeError("TRUSTED_HOSTS must contain at least one host")

        if environment in {"production", "prod"}:
            if not self.SECRET_KEY or self.SECRET_KEY == "dev-only-change-this-secret-key" or len(self.SECRET_KEY) < 32:
                raise RuntimeError("SECRET_KEY must be a strong value of at least 32 characters in production")
            if self.DEBUG:
                raise RuntimeError("DEBUG must be false in production")
            if self.MIGRATION_MODE.lower() != "alembic":
                raise RuntimeError("MIGRATION_MODE must be 'alembic' in production")
            if self.DATABASE_URL.lower().startswith("sqlite"):
                raise RuntimeError("SQLite is not recommended for production; configure PostgreSQL")
            if not self.cors_origins or any(origin == "*" for origin in self.cors_origins):
                raise RuntimeError("CORS_ORIGINS must explicitly list trusted origins in production")
            for origin in self.cors_origins:
                if not origin.startswith("https://"):
                    raise RuntimeError("Production CORS origins must use HTTPS")
            if self.AI_PROVIDER.lower() == "openai" and not self.OPENAI_API_KEY.strip():
                raise RuntimeError("OPENAI_API_KEY must be configured when AI_PROVIDER=openai in production")
            if not self.git_allowed_roots:
                raise RuntimeError("GIT_ALLOWED_ROOTS must be configured in production")


settings = Settings()
