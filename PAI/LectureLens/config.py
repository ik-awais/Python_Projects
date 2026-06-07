"""Configuration management with environment validation."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    SECRET_KEY: str
    DEBUG: bool
    GEMINI_API_KEY: str | None
    NVIDIA_API_KEY: str
    ADMIN_PASSWORD: str
    CHROMA_PATH: Path
    DATABASE_PATH: Path
    UPLOAD_FOLDER: Path
    LOG_FILE: Path
    MAX_FILE_SIZE_MB: int
    CHUNK_SIZE: int
    OVERLAP: int
    BATCH_SIZE: int          # for embedding batching
    INDEXING_WORKERS: int    # number of background threads
    WATCH_FOLDER_ENABLED: bool
    WATCH_FOLDER_INTERVAL_SECONDS: int
    ALLOWED_EXTENSIONS: tuple = ('.pdf', '.docx', '.pptx')

    @classmethod
    def from_env(cls) -> 'Config':
        nvidia_key = os.getenv('NVIDIA_API_KEY')
        if not nvidia_key:
            raise ValueError("Missing NVIDIA_API_KEY – required for LLM generation")

        required_vars = {
            'FLASK_SECRET_KEY': os.getenv('FLASK_SECRET_KEY'),
            'NVIDIA_API_KEY': nvidia_key,
            'ADMIN_PASSWORD': os.getenv('ADMIN_PASSWORD'),
        }
        missing = [k for k, v in required_vars.items() if not v]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")

        gemini_key = os.getenv('GEMINI_API_KEY')
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        max_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', '2048'))   # 2GB for bulk uploads
        chroma_path = Path(os.getenv('CHROMA_PATH', './database/chroma'))
        db_path = Path(os.getenv('DATABASE_PATH', './database/metadata.db'))
        upload_folder = Path(os.getenv('UPLOAD_FOLDER', './uploads'))
        log_file = Path(os.getenv('LOG_FILE', './logs/lecturelens.log'))
        chunk_size = int(os.getenv('CHUNK_SIZE', '500'))
        overlap = int(os.getenv('OVERLAP', '100'))
        batch_size = int(os.getenv('BATCH_SIZE', '32'))
        indexing_workers = int(os.getenv('INDEXING_WORKERS', '4'))   # increase to 4
        watch_enabled = os.getenv('WATCH_FOLDER_ENABLED', 'True').lower() == 'true'
        watch_interval = int(os.getenv('WATCH_FOLDER_INTERVAL_SECONDS', '30'))

        # Ensure directories exist
        chroma_path.mkdir(parents=True, exist_ok=True)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        upload_folder.mkdir(parents=True, exist_ok=True)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            SECRET_KEY=required_vars['FLASK_SECRET_KEY'],
            DEBUG=debug,
            GEMINI_API_KEY=gemini_key,
            NVIDIA_API_KEY=required_vars['NVIDIA_API_KEY'],
            ADMIN_PASSWORD=required_vars['ADMIN_PASSWORD'],
            CHROMA_PATH=chroma_path,
            DATABASE_PATH=db_path,
            UPLOAD_FOLDER=upload_folder,
            LOG_FILE=log_file,
            MAX_FILE_SIZE_MB=max_size_mb,
            CHUNK_SIZE=chunk_size,
            OVERLAP=overlap,
            BATCH_SIZE=batch_size,
            INDEXING_WORKERS=indexing_workers,
            WATCH_FOLDER_ENABLED=watch_enabled,
            WATCH_FOLDER_INTERVAL_SECONDS=watch_interval,
        )