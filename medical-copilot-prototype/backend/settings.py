from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    backend_storage_path: str = "./storage"
    sqlite_path: str = "./storage/copilot.db"
    whisper_mode: str = "mock"
    worker_mode: str = "fallback"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = (BASE_DIR / settings.backend_storage_path).resolve()
DB_PATH = (BASE_DIR / settings.sqlite_path).resolve()

for p in [
    STORAGE_DIR,
    STORAGE_DIR / "audio",
    STORAGE_DIR / "transcripts",
    STORAGE_DIR / "worker_tasks",
    STORAGE_DIR / "worker_outputs",
    STORAGE_DIR / "vectors",
]:
    p.mkdir(parents=True, exist_ok=True)
