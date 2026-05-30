from pydantic_settings import BaseSettings
from pydantic import model_validator

class Settings(BaseSettings):
    # The format is postgresql+ASYNC_DRIVER://user:password@host/dbname
    DATABASE_URL: str = "postgresql+asyncpg://postgres:root@localhost:5432/ekyc_db"
    DATABASE_SYNC_URL: str | None = None
    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 20 * 1024 * 1024
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    COMPLIANCE_SCREENING_ENABLED: bool = True
    COMPLIANCE_RETRY_MAX_ATTEMPTS: int = 2
    COMPLIANCE_SANCTIONS_ENABLED: bool = True
    COMPLIANCE_PEP_ENABLED: bool = True
    COMPLIANCE_ADVERSE_MEDIA_ENABLED: bool = True
    COMPLIANCE_INTERNAL_WATCHLIST_ENABLED: bool = True
    COMPLIANCE_EXIT_LIST_ENABLED: bool = True
    COMPLIANCE_IP_RISK_ENABLED: bool = True

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def set_database_sync_url(self):
        if self.DATABASE_SYNC_URL is None:
            self.DATABASE_SYNC_URL = self.DATABASE_URL.replace(
                "postgresql+asyncpg://",
                "postgresql+psycopg2://",
                1,
            )
        return self

settings = Settings()
