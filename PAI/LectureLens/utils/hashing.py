"""File hashing utilities for duplicate detection."""
import hashlib
from pathlib import Path

def compute_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Compute SHA256 hash of a file.
    Args:
        file_path: Path to file.
        chunk_size: Read file in chunks to handle large files.
    Returns:
        Hexadecimal SHA256 hash as string.
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()