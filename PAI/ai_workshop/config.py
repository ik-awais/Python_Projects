"""
config.py — Central configuration for AI Workshop
"""

import json
from pathlib import Path

CONFIG_FILE = Path.home() / ".ai_workshop_config.json"

DEFAULTS = {
    "ai_provider": "nvidia",
    "gemini_api_key": "",
    "gemini_model": "gemini-1.5-flash",
    "nvidia_api_key": "",
    "nvidia_model": "meta/llama-3.1-70b-instruct",
    "huggingface_token": "",
    "ui_scale": 1.0,
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
    config = dict(DEFAULTS)
    
    # Load from config file if it exists
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            config.update(data)
        except Exception:
            pass
    
    # Load API keys from environment variables as fallback (if not set in config)
    import os
    
    # Only use env vars if config doesn't have them or they're empty
    if not config.get("gemini_api_key"):
        env_gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if env_gemini_key:
            config["gemini_api_key"] = env_gemini_key.strip()
    
    if not config.get("nvidia_api_key"):
        env_nvidia_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NIM_API_KEY")
        if env_nvidia_key:
            config["nvidia_api_key"] = env_nvidia_key.strip()
    
    if not config.get("huggingface_token"):
        env_hf_token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
        if env_hf_token:
            config["huggingface_token"] = env_hf_token.strip()
    
    return config

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[config] Could not save: {e}")

# Refactored Light Theme Colour Palette — Modern clean light theme
LIGHT_THEME = dict(
    # Main content areas, sidebar, and top bar colors
    bg          = "#e8ecf5",      # Main content areas - lighter than sidebar for clear separation
    bg_alt      = "#e8ecf5",      # Alternative background
    panel       = "#f5f7fb",      # Panel backgrounds
    panel_alt   = "#f0f3f8",      # Alternative panel
    card        = "#ffffff",      # White cards with borders
    card2       = "#fafbff",      # Very light card alternative
    card_hover  = "#f8faff",      # Card hover state
    
    # Sidebar colors
    sidebar     = "#dde3ee",      # Sidebar background - enhanced visibility
    sidebar_alt = "#d6dff0",      # Sidebar alternative/top bar
    
    # Borders with better visibility
    border      = "#c9d4e8",      # Light border for cards
    border2     = "#b0bfd8",      # Medium border
    border3     = "#95a5c0",      # Darker border
    sidebar_border = "#b8c5d8",    # Distinct border for sidebar separation
    
    # Primary accent color
    accent      = "#4a7fcb",      # Primary blue accent
    accent2     = "#5a8fdb",      # Lighter accent
    accent3     = "#3a6fbb",      # Darker accent
    accent4     = "#6a9feb",      # Very light accent
    accent5     = "#2a5fab",      # Dark accent
    accent6     = "#7aaffb",      # Light accent
    
    # Text colors
    text        = "#1e2d45",      # Headings and important text
    text2       = "#2c3e5a",      # Sidebar nav items text - optimized for 4.5:1 contrast
    text3       = "#5a6a80",      # Card descriptions
    dim         = "#7a8a9c",      # Dimmed text
    dim2        = "#9aa5b5",      # Very dim text
    
    # Status colors
    success     = "#4a7fcb",      # Success uses primary accent
    warning     = "#f59e0b",      # Warning amber
    error       = "#ef4444",      # Error red
    info        = "#4a7fcb",      # Info uses primary accent
    
    # Component-specific colors
    log_bg      = "#dce3ef",      # Status bar background
    input_bg    = "#f4f7fc",      # Chat input area background
    input_hover = "#e8ecf5",      # Input hover state
    
    # Chat colors
    chat_user   = "#f0f7ff",      # Light blue for user messages
    chat_ai     = "#f8faff",      # Very light for AI messages
    chat_system = "#fafbff",      # System messages
    
    # Interactive states
    hover       = "#c5d5ef",      # Suggestion chips hover
    active      = "#4a7fcb",      # Active state
    focus       = "#5a8fdb",      # Focus state
    
    # Mode tabs colors
    tab_inactive = "#cdd6e8",    # Inactive tab background
    tab_inactive_text = "#3a4f6e",  # Inactive tab text
    tab_active = "#4a7fcb",       # Active tab background
    
    # Suggestion chips
    chip_bg     = "#dce6f5",      # Suggestion chip background
    chip_text   = "#2c4070",      # Suggestion chip text
    chip_border = "#b0bfd8",      # Suggestion chip border
    
    # Shadow colors
    shadow      = "rgba(0,0,0,0.07)",  # Card shadow
    shadow_dark = "rgba(0,0,0,0.12)",  # Darker shadow
    
    # Special colors for badges and labels
    badge_bg    = "#4a7fcb",      # Badge background
    badge_text  = "#ffffff",      # Badge text
)

# Enhanced Dark Theme Colour Palette — Modern dark theme with better contrast
DARK = dict(
    # Background layers with subtle gradients
    bg          = "#0a0a0f",      # deeper, richer background
    bg_alt      = "#0f0f17",      # alternative background
    panel       = "#141421",      # refined panel color
    panel_alt   = "#1a1a28",      # alternative panel
    card        = "#1f1f2e",      # elevated card
    card2       = "#242438",      # secondary card
    card_hover  = "#2a2a42",      # hover state
    
    # Borders with better contrast
    border      = "#2d2d4a",      # primary border
    border2     = "#3a3a5a",      # secondary border
    border3     = "#4a4a7a",      # tertiary border
    
    # Refined accent colors with better harmony
    accent      = "#8b7aff",      # vibrant purple (enhanced)
    accent2     = "#ff6b6b",      # softer coral
    accent3     = "#4ecdc4",      # modern teal
    accent4     = "#ffd93d",      # warm amber
    accent5     = "#6bcf7f",      # fresh green
    accent6     = "#ff8cc8",      # soft pink
    
    # Text with better hierarchy
    text        = "#f0f0f5",      # cleaner white
    text2       = "#b8b8d0",      # muted text
    text3       = "#8888a8",      # dimmer text
    dim         = "#585878",      # subtle text
    dim2        = "#383858",      # very dim
    
    # Status colors with better balance
    success     = "#4ade80",      # modern green
    warning     = "#fbbf24",      # warmer yellow
    error       = "#f87171",      # softer red
    info        = "#60a5fa",      # modern blue
    
    # Component-specific colors
    sidebar     = "#08080d",      # deeper sidebar
    sidebar_alt = "#0c0c14",      # sidebar accent
    log_bg      = "#05050a",      # log background
    input_bg    = "#1e1e30",      # input background
    input_hover = "#252540",      # input hover
    
    # Chat colors with better contrast
    chat_user   = "#1e293b",      # user chat bg
    chat_ai     = "#0f2920",      # AI chat bg
    chat_system = "#1a1a2e",      # system chat bg
    
    # Interactive states
    hover       = "#3a3a5a",      # hover overlay
    active      = "#4a4a7a",      # active state
    focus       = "#5a5a8a",      # focus ring
    
    # Gradient stops for visual effects
    grad_start  = "#0a0a0f",
    grad_end    = "#141421",
    
    # Shadow colors
    shadow      = "#00000020",    # subtle shadow
    shadow_dark = "#00000040",    # darker shadow
)

# Theme management
def get_theme(theme_name: str):
    """Get theme configuration by name"""
    themes = {
        "dark": DARK,
        "light": LIGHT_THEME,
        "light_theme": LIGHT_THEME,
        "sky_blue": LIGHT_THEME
    }
    return themes.get(theme_name.lower(), LIGHT_THEME)

def get_available_themes():
    """Get list of available themes"""
    return ["dark", "light", "light_theme"]

# Enhanced fonts with better typography and spacing
FONTS = dict(
    # Title hierarchy
    title       = ("Segoe UI", 20, "bold"),      # main titles
    subtitle    = ("Segoe UI", 16, "bold"),      # subtitles
    
    # Content hierarchy
    head        = ("Segoe UI", 12, "bold"),      # section headers
    subhead     = ("Segoe UI", 11, "bold"),      # subsection headers
    
    # Body text
    body        = ("Segoe UI", 10, "normal"),   # main body text
    body_small  = ("Segoe UI", 9, "normal"),    # smaller body text
    
    # UI elements
    small       = ("Segoe UI", 9, "normal"),     # small UI text
    tiny        = ("Segoe UI", 8, "normal"),     # tiny labels
    
    # Monospace fonts
    mono        = ("Consolas", 11, "normal"),     # code/monospace
    mono_small  = ("Consolas", 10, "normal"),    # small monospace
    mono_tiny   = ("Consolas", 9, "normal"),     # tiny monospace
    
    # Button fonts
    btn         = ("Segoe UI", 10, "bold"),       # standard buttons
    btn_small   = ("Segoe UI", 9, "bold"),       # small buttons
    btn_large   = ("Segoe UI", 12, "bold"),       # large buttons
    
    # Chat-specific
    chat        = ("Segoe UI", 10, "normal"),    # chat text
    chat_label  = ("Segoe UI", 9, "bold"),       # chat labels
    
    # Specialized fonts
    tag         = ("Consolas", 9, "bold"),        # tags
    code        = ("Consolas", 10, "normal"),     # inline code
    
    # Status fonts
    status      = ("Segoe UI", 9, "italic"),      # status messages
    hint        = ("Segoe UI", 8, "italic"),       # hints/tips
)

# Enhanced file type colors with better visual harmony
TYPE_COLORS = {
    "pdf":     "#ef4444",      # modern red
    "excel":   "#10b981",      # modern green
    "pptx":    "#f59e0b",      # modern amber
    "docx":    "#3b82f6",      # modern blue
    "image":   "#8b5cf6",      # modern purple
    "audio":    "#06b6d4",      # modern cyan
    "video":    "#ec4899",      # modern pink
    "csv":     "#84cc16",      # modern lime
    "text":     "#6b7280",      # modern gray
    "archive":  "#f97316",      # modern orange
    "code":     "#0ea5e9",      # modern sky blue
    "txt":   "#95a5a6",
    "html":  "#f39c12",
}
