"""Input validation utilities (file size, extensions, etc.)."""
from pathlib import Path

def is_allowed_file(filename: str, allowed_extensions: tuple) -> bool:
    """Check if file extension is in allowed list."""
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions

def is_file_size_within_limit(file_size_bytes: int, max_size_mb: int) -> bool:
    """Check if file size does not exceed limit (MB to bytes)."""
    max_bytes = max_size_mb * 1024 * 1024
    return file_size_bytes <= max_bytes