"""
Configuration settings for AI FileMat Web Backend
"""

from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Application settings
    app_name: str = "AI FileMat"
    app_version: str = "2.0.0"
    debug: bool = True
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # File storage
    upload_dir: str = "uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_extensions: list = [
        "pdf", "docx", "xlsx", "pptx", "txt", "csv",
        "jpg", "jpeg", "png", "gif", "bmp", "webp",
        "mp4", "avi", "mov", "mkv", "mp3", "wav", "flac",
        "zip", "rar", "7z", "tar", "gz"
    ]
    
    # AI service settings
    openai_api_key: str = ""
    gemini_api_key: str = ""
    nvidia_api_key: str = ""
    
    # Database settings
    database_url: str = "sqlite:///./ai_filemat.db"
    
    # Security settings
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    
    # Theme settings
    default_theme: str = "light"
    available_themes: list = ["light", "dark", "ocean"]
    
    class Config:
        env_file = ".env"

settings = Settings()
