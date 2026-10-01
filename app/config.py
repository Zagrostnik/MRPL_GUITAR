from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'melody.db'}"
    admin_password: str = "change-me"
    secret_key: str = "change-me-too-please"
    seed_demo_data: bool = True
    upload_dir: Path = BASE_DIR / "app" / "static" / "uploads"
    max_upload_mb: int = 5


settings = Settings()
