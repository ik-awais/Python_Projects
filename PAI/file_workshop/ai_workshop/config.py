"""
config.py — Central configuration for AI Workshop
"""

import os
import json
from pathlib import Path

CONFIG_FILE = Path.home() / ".ai_workshop_config.json"

DEFAULTS = {
    "gemini_api_key": "",
    "gemini_model":   "gemini-2.0-flash",
    "theme":          "dark",
    "output_dir":     "",
    "max_chat_history": 50,
    "auto_suggest":   True,
    "dpi_default":    150,
}

# The new google-genai SDK requires the "models/" prefix on model names.
# Map display names → API names used in generate_content calls.
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
]

# Human-readable labels shown in the Settings UI
GEMINI_MODEL_LABELS = {
    "gemini-2.0-flash":      "Gemini 2.0 Flash  ⚡ Latest & fastest (recommended)",
    "gemini-2.0-flash-lite": "Gemini 2.0 Flash Lite  🪶 Ultra-fast, lightweight",
    "gemini-1.5-flash":      "Gemini 1.5 Flash  🔥 Proven, reliable",
    "gemini-1.5-flash-8b":   "Gemini 1.5 Flash 8B  📦 Compact, quick",
    "gemini-1.5-pro":        "Gemini 1.5 Pro  🧠 Most capable for complex tasks",
}

def model_api_name(model: str) -> str:
    """Return the correct API model name for generate_content calls."""
    # Already prefixed — return as-is
    if model.startswith("models/"):
        return model
    return f"models/{model}"

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            merged = dict(DEFAULTS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULTS)

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[config] Could not save: {e}")

# Colour palette — dark theme
DARK = dict(
    bg      = "#0f0f17",
    panel   = "#16161f",
    card    = "#1e1e2c",
    card2   = "#252535",
    border  = "#2e2e45",
    border2 = "#3a3a5a",

    accent  = "#7c6af7",   # purple
    accent2 = "#f7706a",   # coral/red
    accent3 = "#06d6a0",   # teal/green  (AI responses)
    accent4 = "#ffd166",   # amber/yellow

    text    = "#e8e8f2",
    text2   = "#a8a8c0",
    dim     = "#6868888",
    dim2    = "#3a3a55",

    success = "#06d6a0",
    warning = "#ffd166",
    error   = "#f7706a",
    info    = "#74b9ff",

    sidebar = "#0c0c14",
    log_bg  = "#09090f",
    input_bg= "#1a1a28",
    chat_user = "#1e2a4a",
    chat_ai   = "#0a2018",
)

# Fonts
FONTS = dict(
    title   = ("Segoe UI", 18, "bold"),
    head    = ("Segoe UI", 11, "bold"),
    subhead = ("Segoe UI", 10, "bold"),
    body    = ("Segoe UI", 10),
    small   = ("Segoe UI", 9),
    mono    = ("Consolas", 10),
    mono_sm = ("Consolas", 9),
    btn     = ("Segoe UI", 10, "bold"),
    btnbig  = ("Segoe UI", 11, "bold"),
    chat    = ("Segoe UI", 10),
    tag     = ("Consolas", 9, "bold"),
)

# File type colours (for queue display)
TYPE_COLORS = {
    "pdf":   "#e74c3c",
    "excel": "#27ae60",
    "pptx":  "#e67e22",
    "docx":  "#2980b9",
    "image": "#9b59b6",
    "audio": "#1abc9c",
    "video": "#e91e8c",
    "csv":   "#16a085",
    "txt":   "#95a5a6",
    "html":  "#f39c12",
}
