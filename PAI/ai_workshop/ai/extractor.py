"""
ai/extractor.py — Extract text/content from any supported file type
for feeding into the AI layer.
"""

import os
import csv
from pathlib import Path
from typing import Optional, List

# Optional deps — same flags as main app
def _try(pkg):
    try: __import__(pkg); return True
    except ImportError: return False

HAS_PDFPLUMBER = _try("pdfplumber")
HAS_DOCX       = _try("docx")
HAS_OPENPYXL   = _try("openpyxl")
HAS_PPTX       = _try("pptx")
HAS_PIL        = _try("PIL")

if HAS_PDFPLUMBER: import pdfplumber
if HAS_DOCX:       from docx import Document
if HAS_OPENPYXL:   import openpyxl
if HAS_PPTX:       from pptx import Presentation


IMAGE_EXTS = {".png",".jpg",".jpeg",".webp",".bmp",".gif",".tiff",".tif"}
AUDIO_EXTS = {".mp3",".wav",".ogg",".flac",".aac",".m4a",".wma"}
VIDEO_EXTS = {".mp4",".avi",".mov",".mkv",".webm",".flv",".wmv",".m4v"}


def extract_text(file_path: str, max_chars: int = 15000) -> str:
    """
    Extract readable text from any supported file.
    Returns a string (may be empty for binary/media files).
    """
    ext = Path(file_path).suffix.lower()

    # ── PDF ──────────────────────────────────────────────────────────────────
    if ext == ".pdf":
        if not HAS_PDFPLUMBER:
            return "[pdfplumber not installed — cannot extract PDF text]"
        try:
            lines = []
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        lines.append(f"--- Page {i+1} ---\n{text}")
            content = "\n\n".join(lines)
            return content[:max_chars]
        except Exception as e:
            return f"[PDF extraction error: {e}]"

    # ── Word ─────────────────────────────────────────────────────────────────
    if ext == ".docx":
        if not HAS_DOCX:
            return "[python-docx not installed — cannot extract DOCX text]"
        try:
            doc = Document(file_path)
            parts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)
            # Also extract tables
            for table in doc.tables:
                for row in table.rows:
                    parts.append(" | ".join(c.text for c in row.cells if c.text.strip()))
            return "\n".join(parts)[:max_chars]
        except Exception as e:
            return f"[DOCX extraction error: {e}]"

    # ── Excel ────────────────────────────────────────────────────────────────
    if ext in {".xlsx", ".xls", ".xlsm", ".ods"}:
        if not HAS_OPENPYXL:
            return "[openpyxl not installed — cannot extract Excel text]"
        try:
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            parts = []
            for ws in wb.worksheets:
                parts.append(f"=== Sheet: {ws.title} ===")
                for row in ws.iter_rows(values_only=True):
                    row_text = "\t".join(str(v) if v is not None else "" for v in row)
                    if row_text.strip():
                        parts.append(row_text)
            wb.close()
            return "\n".join(parts)[:max_chars]
        except Exception as e:
            return f"[Excel extraction error: {e}]"

    # ── PowerPoint ───────────────────────────────────────────────────────────
    if ext in {".pptx", ".ppt", ".odp"}:
        if not HAS_PPTX:
            return "[python-pptx not installed — cannot extract PPTX text]"
        try:
            prs = Presentation(file_path)
            parts = []
            for i, slide in enumerate(prs.slides, 1):
                texts = []
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for para in shape.text_frame.paragraphs:
                            t = para.text.strip()
                            if t: texts.append(t)
                if texts:
                    parts.append(f"--- Slide {i} ---\n" + "\n".join(texts))
            return "\n\n".join(parts)[:max_chars]
        except Exception as e:
            return f"[PPTX extraction error: {e}]"

    # ── CSV / TSV ─────────────────────────────────────────────────────────────
    if ext in {".csv", ".tsv"}:
        try:
            delim = "\t" if ext == ".tsv" else ","
            rows = []
            with open(file_path, newline="", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delim)
                for row in reader:
                    rows.append(" | ".join(row))
            return "\n".join(rows)[:max_chars]
        except Exception as e:
            return f"[CSV extraction error: {e}]"

    # ── Plain text / HTML ─────────────────────────────────────────────────────
    if ext in {".txt", ".html", ".htm", ".md", ".json", ".xml", ".yaml", ".yml"}:
        try:
            return Path(file_path).read_text(encoding="utf-8", errors="replace")[:max_chars]
        except Exception as e:
            return f"[Text read error: {e}]"

    # ── Images ────────────────────────────────────────────────────────────────
    if ext in IMAGE_EXTS:
        return f"[Image file — use 'Analyse Image' button for AI vision analysis]"

    # ── Audio / Video ─────────────────────────────────────────────────────────
    if ext in AUDIO_EXTS:
        return f"[Audio file — AI text extraction not supported for audio]"
    if ext in VIDEO_EXTS:
        return f"[Video file — AI text extraction not supported for video]"

    return f"[Unsupported file type: {ext}]"


def get_file_summary_context(file_paths: List[str]) -> str:
    """
    Build a brief context string listing all queued files with their types and sizes.
    Used as background context when chatting.
    """
    lines = ["Currently loaded files:"]
    for fp in file_paths:
        p = Path(fp)
        ext = p.suffix.lower()
        try:
            size_kb = p.stat().st_size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        except Exception:
            size_str = "unknown size"
        lines.append(f"  - {p.name}  [{ext}]  {size_str}")
    return "\n".join(lines)


def is_image(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in IMAGE_EXTS


def is_text_extractable(file_path: str) -> bool:
    ext = Path(file_path).suffix.lower()
    return ext in {".pdf", ".docx", ".xlsx", ".xls", ".xlsm", ".ods",
                   ".pptx", ".ppt", ".odp", ".csv", ".tsv",
                   ".txt", ".html", ".htm", ".md"}
