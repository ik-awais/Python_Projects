"""Configuration management with environment validation."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    """Application configuration validated at startup."""
    # Flask
    SECRET_KEY: str
    DEBUG: bool

    # API Keys
    GEMINI_API_KEY: str
    NVIDIA_API_KEY: str

    # Auth
    ADMIN_PASSWORD: str

    # Paths
    CHROMA_PATH: Path
    DATABASE_PATH: Path
    UPLOAD_FOLDER: Path
    LOG_FILE: Path

    # Upload & Document Processing
    MAX_FILE_SIZE_MB: int
    CHUNK_SIZE: int
    OVERLAP: int
    ALLOWED_EXTENSIONS: tuple = ('.pdf', '.docx', '.pptx')

    @classmethod
    def from_env(cls) -> 'Config':
        """Load and validate configuration from environment variables."""
        required_vars = {
            'FLASK_SECRET_KEY': os.getenv('FLASK_SECRET_KEY'),
            'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
            'NVIDIA_API_KEY': os.getenv('NVIDIA_API_KEY'),
            'ADMIN_PASSWORD': os.getenv('ADMIN_PASSWORD'),
        }
        missing = [k for k, v in required_vars.items() if not v]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")

        # Parse optional with defaults
        debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        max_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', '50'))
        
        # New Chunking defaults
        chunk_size = int(os.getenv('CHUNK_SIZE', '500'))
        overlap = int(os.getenv('OVERLAP', '100'))
        
        chroma_path = Path(os.getenv('CHROMA_PATH', './database/chroma'))
        db_path = Path(os.getenv('DATABASE_PATH', './database/metadata.db'))
        upload_folder = Path(os.getenv('UPLOAD_FOLDER', './uploads'))
        log_file = Path(os.getenv('LOG_FILE', './logs/lecturelens.log'))

        # Ensure parent directories exist (except for files, we'll create on write)
        chroma_path.mkdir(parents=True, exist_ok=True)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        upload_folder.mkdir(parents=True, exist_ok=True)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        return cls(
            SECRET_KEY=required_vars['FLASK_SECRET_KEY'],
            DEBUG=debug,
            GEMINI_API_KEY=required_vars['GEMINI_API_KEY'],
            NVIDIA_API_KEY=required_vars['NVIDIA_API_KEY'],
            ADMIN_PASSWORD=required_vars['ADMIN_PASSWORD'],
            CHROMA_PATH=chroma_path,
            DATABASE_PATH=db_path,
            UPLOAD_FOLDER=upload_folder,
            LOG_FILE=log_file,
            MAX_FILE_SIZE_MB=max_size_mb,
            CHUNK_SIZE=chunk_size,
            OVERLAP=overlap,
        )