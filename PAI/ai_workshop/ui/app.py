"""
ui/app.py — File Workshop AI  v2
Chat-first interface: AI lives at the centre, tools slide in as needed.

Layout:
  ┌──────────────────────────────────────────────────────────────┐
  │  TOPBAR:  Logo · AI status · Drop zone · Settings            │
  ├────────────┬─────────────────────────────────┬───────────────┤
  │  self.SIDEBAR   │   CENTRE (tool panel / chat)    │  CHAT self.PANEL   │
  │  nav tabs  │   switches based on active tab  │  always live  │
  └────────────┴─────────────────────────────────┴───────────────┘
"""

import os, sys, threading, subprocess, shutil, time
from pathlib import Path
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_theme, get_available_themes, FONTS as F, load_config, save_config, GEMINI_MODELS
from core.processor import (
    cat, cat_icon, parse_pages, parse_groups, do_convert, preview_convert_paths,
    pdf_page_count, pptx_slide_count,
    split_each, split_range, split_custom,
    merge_pdfs, pptx_merge, pptx_split_slides,
    resequence_pdf, delete_pages, rotate_pages, reverse_pdf,
    compress_pdf, encrypt_pdf, decrypt_pdf,
    watermark_text, watermark_pdf_overlay,
    get_metadata, set_metadata,
    video_split, video_merge, audio_merge, video_get_duration, format_duration,
    _parse_time, audio_split,
    HAS_PYPDF, HAS_PDFPLUMBER, HAS_DOCX, HAS_PIL,
    HAS_PDF2IMAGE, HAS_FFMPEG, HAS_OPENPYXL, HAS_PPTX, HAS_LIBREOFFICE, HAS_CAIROSVG,
    IMAGE_EXTS, AUDIO_EXTS, VIDEO_EXTS, EXCEL_EXTS, PPTX_EXTS, CSV_EXTS
)
from ai.gemini import GeminiClient, HAS_GENAI
from ai.nvidia_nim import NIMClient, HAS_NIM, NIM_MODELS
from ai.extractor import extract_text, get_file_summary_context, is_image, is_text_extractable
from utils.upscaler import upscale_image, batch_upscale, get_image_info, SCALE_METHODS, HAS_PIL as UP_PIL

# ── Dynamic Color System ──────────────────────────────────────────────────────────
# Colors are now handled dynamically within the app class to support theme switching
# Global shortcuts removed to enable proper theme management

# Helper function to get colors (will be used within app class)
def get_color(color_name, theme_dict):
    """Get a color from the theme dictionary"""
    return theme_dict.get(color_name, "#000000")

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

class Tooltip:
    def __init__(self, w, text, app=None):
        self.w = w
        self.text = text
        self.app = app  # Reference to app for theme access
        self.tip = None
        
    def get_color(self, color_name):
        """Get color from current theme"""
        if self.app and hasattr(self.app, 'C'):
            return self.app.C.get(color_name, "#000000")
        return "#000000"
        
    def show(self, x, y):
        """Show tooltip at specified coordinates"""
        # Use theme colors
        bg = self.get_color("card2")
        fg = self.get_color("text")
        
        self.tip = tk.Toplevel(self.w)
        tooltip_frame = tk.Frame(self.tip, bg=self.get_color("border"))
        tooltip_frame.pack(padx=1, pady=1)
        
        tk.Label(tooltip_frame, text=self.text, 
                 font=("Segoe UI", 8), bg=bg, fg=fg).pack(padx=4, pady=2)
        
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.wm_attributes("-topmost", "true")
        self.tip.withdraw()
        
        # Show after a brief delay to ensure proper positioning
        self.w.after(100, self._show_tip)
        
    def _show_tip(self):
        """Actually show the tooltip"""
        self.tip.deiconify()
        self.tip.wm_geometry(f"+{self.w.winfo_rootx()+12}+{self.w.winfo_rooty()+12}")
        self.tip.overrideredirect(False)
        self.tip.lift()
        self.tip.after(100, lambda: self.tip.attributes("-alpha", 0.9))
        
    def hide(self):
        """Hide the tooltip"""
        if self.tip:
            self.tip.destroy()
            self.tip = None

    def on_enter(self, event):
        if self.tip: return
        x = event.x_root + 15
        y = event.y_root + 10
        self.show(x, y)

    def on_leave(self, event):
        if self.tip:
            self.tip.destroy()
            self.tip = None

    def bind(self):
        self.w.bind("<Enter>", self.on_enter)
        self.w.bind("<Leave>", self.on_leave)


def mk_btn(parent, text, cmd, bg=None, fg="#ffffff", font=None, padx=12, pady=6, app=None, rounded=True):
    """Create an enhanced button with modern styling and rounded corners"""
    # Get colors from theme if app is provided
    if app and hasattr(app, 'C'):
        if bg is None:
            btn_bg = app.C.get("accent", "#2196f3")
            hover = app.C.get("active", "#90caf9")
        else:
            btn_bg = bg
            hover = app.C.get("hover", "#bbdefb")
    else:
        # Fallback colors
        if bg is None:
            btn_bg = "#2196f3"
            hover = "#1976d2"
        else:
            btn_bg = bg
            hover = bg
    
    if font is None:
        font = F["btn"]
    
    # Create button with enhanced styling and rounded corners
    btn = tk.Button(parent, text=text, command=cmd,
                   bg=btn_bg, fg=fg,
                   activebackground=hover, 
                   activeforeground=fg,
                   relief="flat" if rounded else "raised", 
                   bd=0 if rounded else 2,
                   cursor="hand2",
                   padx=padx, pady=pady,
                   font=font)
    
    # Add hover effects with proper restoration
    def on_enter(e):
        btn.config(bg=hover)
    def on_leave(e):
        btn.config(bg=btn_bg)
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    
    return btn

def mk_big_btn(parent, text, cmd, bg=None, app=None):
    """Create an enhanced large button"""
    return mk_btn(parent, text, cmd, 
                 bg=bg, 
                 font=F["btn_large"], 
                 padx=20, pady=12,
                 app=app)

def sep(parent, vertical=False, app=None):
    """Create an enhanced separator with gradient effect"""
    # Get colors from theme if app is provided
    if app and hasattr(app, 'C'):
        bg = app.C.get("bg", "#e8f4fd")
        border = app.C.get("border", "#c8ddf0")
    else:
        bg = "#e8f4fd"
        border = "#c8ddf0"
    
    if vertical:
        sep = tk.Frame(parent, bg=border, width=1)
        sep.pack(fill="y", padx=8)
    else:
        sep = tk.Frame(parent, bg=border, height=1)
        sep.pack(fill="x", pady=8)
    return sep

def card(parent, app=None, rounded=True):
    """Create a modern card container with rounded corners"""
    if app and hasattr(app, 'C'):
        bg = app.C.get("card", "#ffffff")
        border = app.C.get("border", "#c8ddf0")
    else:
        # Fallback colors
        bg = "#ffffff"
        border = "#c8ddf0"
    
    f = tk.Frame(parent, bg=bg, padx=20, pady=16)
    f.pack(fill="x", padx=16, pady=(0, 12))
    
    # Add subtle border effect with rounded corners
    if rounded:
        border_frame = tk.Frame(f, bg=border, relief="flat", bd=1)
        border_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
    
    return f

def section_hdr(parent, title, subtitle="", app=None):
    """Create an enhanced section header with unstyled bold text"""
    # Get colors from theme if app is provided
    if app and hasattr(app, 'C'):
        bg = app.C.get("bg", "#eef1f7")
        text_color = app.C.get("text", "#1e2d45")
        text2 = app.C.get("text2", "#2c3e5a")
    else:
        bg = "#eef1f7"
        text_color = "#1e2d45"
        text2 = "#2c3e5a"
    
    h = tk.Frame(parent, bg=bg)
    h.pack(fill="x", padx=20, pady=(20, 12))
    
    # Main title with unstyled bold text, transparent background
    title_label = tk.Label(h, text=title, 
                          font=F["head"], 
                          bg=bg, fg=text_color)
    title_label.pack(side="left")
    
    # Subtitle with better spacing
    if subtitle:
        subtitle_label = tk.Label(h, text=f"  •  {subtitle}", 
                                 font=F["small"],
                                 bg=bg, fg=text2)
        subtitle_label.pack(side="left")
    
    return h

def lbl(parent, text, head=False, mono=False, dim=False, w=None, wrap=None, app=None):
    """Create an enhanced label with better typography"""
    # Get colors from theme if app is provided
    if app and hasattr(app, 'C'):
        bg = app.C.get("bg", "#e8f4fd")
        accent = app.C.get("accent", "#2196f3")
        text2 = app.C.get("text2", "#3949ab")
    else:
        bg = "#e8f4fd"
        accent = "#2196f3"
        text2 = "#3949ab"
    
    # Choose font based on type
    if head:
        font = F["head"]
    elif mono:
        font = F["mono"]
    else:
        font = F["body"]
    
    # Create label with enhanced styling
    label = tk.Label(parent, text=text, font=font, bg=bg, fg=accent if head else text2)
    
    # Apply additional styling
    if w:
        label.config(width=w)
    if wrap:
        label.config(wraplength=wrap)
    
    return label

def entry(parent, var, width=22, show=None, mono=True, app=None):
    """Create an enhanced entry field with modern styling"""
    # Get colors from theme if app is provided
    if app and hasattr(app, 'C'):
        bg = app.C.get("input_bg", "#f0f8ff")
        fg = app.C.get("text", "#1a237e")
        focus = app.C.get("focus", "#64b5f6")
    else:
        bg = "#f0f8ff"
        fg = "#1a237e"
        focus = "#64b5f6"
    
    font = F["mono"] if mono else F["body"]
    entry_widget = tk.Entry(parent, textvariable=var, 
                              font=font, bg=bg, fg=fg,
                              insertbackground=focus,
                              selectbackground=app.C.get("accent", "#2196f3") if app else "#2196f3",
                              selectforeground="#ffffff")
    
    # Add hover effects
    def on_enter(e):
        entry_widget.config(bg=app.C.get("input_hover", "#e3f2fd") if app else "#e3f2fd")
    def on_leave(e):
        entry_widget.config(bg=bg)
    entry_widget.bind("<Enter>", on_enter)
    entry_widget.bind("<Leave>", on_leave)
    
    if show: 
        entry_widget.config(show=show)
        
    return entry_widget


import re as _re
def _clean_ai_response(text: str) -> str:
    """
    Remove raw JSON blocks and code fences from AI responses so the chat
    display only shows the natural-language parts.
    Also strips intent markers like 🎯 lines that are handled elsewhere.
    """
    # Remove ```json ... ``` blocks entirely
    text = _re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=_re.DOTALL)
    # Remove bare JSON objects that start a line (common LLM pattern)
    text = _re.sub(r"^\s*\{[^{}]*\"action\"\s*:[^{}]*\}\s*$", "",
                   text, flags=_re.MULTILINE | _re.DOTALL)
    # Remove any remaining ``` code fences
    text = _re.sub(r"```[a-z]*\n?", "", text)
    text = text.replace("```", "")
    # Collapse 3+ newlines to 2
    text = _re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def _extract_intent_json(text: str) -> Optional[Dict]:
    """Extract intent JSON from AI response fences or bare object."""
    if not text:
        return None
    m = _re.search(r"```json\s*(\{.*?\})\s*```", text, flags=_re.DOTALL)
    if m:
        try:
            import json
            return json.loads(m.group(1))
        except Exception:
            pass
    m2 = _re.search(r"\{[\s\S]*?\}", text)
    if m2:
        try:
            import json
            return json.loads(m2.group(0))
        except Exception:
            return None
    return None


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

class AIWorkshopApp(tk.Tk):

    TABS = [
        ("🏠", "Home",      "home"),
        ("🤖", "AI Chat",   "aichat"),
        ("🧠", "AI Command", "command"),
        ("🔄", "Convert",   "convert"),
        ("✂️",  "Split",     "split"),
        ("🔗", "Merge",     "merge"),
        ("🎬", "Media",     "video"),
        ("📐", "Organise",  "organise"),
        ("🖼",  "Upscale",   "upscale"),
        ("💧", "Stamp",     "stamp"),
        ("🔒", "Protect",   "protect"),
        ("📦", "Compress",  "compress"),
        ("🏷",  "Metadata",  "metadata"),
        ("📋", "Queue",     "queue"),
        ("📜", "Log",       "log"),
    ]

    def __init__(self):
        super().__init__()
        self.title("AI FileMat")
        self.geometry("1480x860")
        self.minsize(1100, 720)

        self.cfg    = load_config()
        self.files: List[str] = []
        self.out_dir = tk.StringVar(value=self.cfg.get("output_dir", ""))
        self.page_count = 0
        self.active_pdf = ""
        self.ai_context_file = ""
        self.ui_scale = float(self.cfg.get("ui_scale", 1.0) or 1.0)
        
        # Theme system
        self.current_theme = self.cfg.get("theme", "light_theme")
        self.C = get_theme(self.current_theme)  # Current theme colors
        self.available_themes = get_available_themes()
        
        # Dynamic color shortcuts for use in UI building
        self._setup_color_shortcuts()
        
        # Now we can safely configure the background
        self.configure(bg=self.BG)

        self.ai = self._make_ai_client()

        self.pages: Dict[str, tk.Frame] = {}
        self.tab_btns: Dict[str, tk.Button] = {}
        self._running_ops: int = 0          # count of active background operations
        self._op_history: List[Dict] = []   # full log history for the Log tab
        self._latest_intent: Optional[Dict] = None
        self._latest_intent_raw: str = ""
        
        # Build the UI
        self._build()
        self._apply_zoom(self.ui_scale)
        
        # Bind keyboard shortcuts
        self.bind_all("<Control-plus>", lambda e: self._zoom_in())
        self.bind_all("<Control-equal>", lambda e: self._zoom_in())
        self.bind_all("<Control-minus>", lambda e: self._zoom_out())
        self.bind_all("<Control-0>", lambda e: self._zoom_reset())
        
        # Add mouse scroll support for zooming
        self.bind_all("<Control-MouseWheel>", self._on_mousewheel_zoom)
        self.bind_all("<Control-Button-4>", lambda e: self._zoom_in())  # Linux scroll up
        self.bind_all("<Control-Button-5>", lambda e: self._zoom_out())  # Linux scroll down
        
        # Initialize UI state
        self._switch_tab("aichat")
        self._status("Welcome — click 🤖 AI Chat to get started")
        self._update_ai_status()
    
    def _setup_color_shortcuts(self):
        """Setup color shortcuts from current theme for easy access"""
        # Core colors
        self.BG          = self.C["bg"]
        self.BG_ALT      = self.C["bg_alt"]
        self.PANEL       = self.C["panel"]
        self.PANEL_ALT   = self.C["panel_alt"]
        self.CARD        = self.C["card"]
        self.CARD2       = self.C["card2"]
        self.CARD_HOVER  = self.C["card_hover"]
        
        # Borders
        self.BORDER      = self.C["border"]
        self.BORDER2     = self.C["border2"]
        self.BORDER3     = self.C["border3"]
        self.SIDEBAR_BORDER = self.C.get("sidebar_border", "#b8c5d8")
        
        # Accent colors
        self.ACCENT      = self.C["accent"]
        self.ACCENT2     = self.C["accent2"]
        self.ACCENT3     = self.C["accent3"]
        self.ACCENT4     = self.C["accent4"]
        self.ACCENT5     = self.C["accent5"]
        self.ACCENT6     = self.C["accent6"]
        
        # Text hierarchy
        self.TEXT        = self.C["text"]
        self.TEXT2       = self.C["text2"]
        self.TEXT3       = self.C["text3"]
        self.DIM         = self.C["dim"]
        self.DIM2        = self.C["dim2"]
        
        # Status colors
        self.SUCCESS     = self.C["success"]
        self.WARN        = self.C["warning"]
        self.ERROR       = self.C["error"]
        self.INFO        = self.C["info"]
        
        # Component colors
        self.SIDEBAR     = self.C["sidebar"]
        self.SIDEBAR_ALT = self.C["sidebar_alt"]
        self.LOG_BG      = self.C["log_bg"]
        self.INPUT_BG    = self.C["input_bg"]
        self.INPUT_HOVER = self.C["input_hover"]
        
        # Chat colors
        self.CHAT_USER   = self.C["chat_user"]
        self.CHAT_AI     = self.C["chat_ai"]
        self.CHAT_SYSTEM = self.C["chat_system"]
        self.CHAT_BG     = self.C["log_bg"]  # Use log_bg as chat background
        
        # Interactive states
        self.HOVER       = self.C["hover"]
        self.ACTIVE      = self.C["active"]
        self.FOCUS       = self.C["focus"]
        
        # Mode tabs colors
        self.TAB_INACTIVE = self.C.get("tab_inactive", "#cdd6e8")
        self.TAB_INACTIVE_TEXT = self.C.get("tab_inactive_text", "#3a4f6e")
        self.TAB_ACTIVE = self.C.get("tab_active", "#4a7fcb")
        
        # Badge colors
        self.BADGE_BG = self.C.get("badge_bg", "#4a7fcb")
        self.BADGE_TEXT = self.C.get("badge_text", "#ffffff")
        
        # Suggestion chips colors
        self.CHIP_BG = self.C.get("chip_bg", "#dce6f5")
        self.CHIP_TEXT = self.C.get("chip_text", "#2c4070")
        self.CHIP_BORDER = self.C.get("chip_border", "#b0bfd8")
        
        # File type colors
        self.TYPE_COLORS = {
            "pdf": "#dc3545",
            "docx": "#0066cc",
            "xlsx": "#107c10",
            "pptx": "#d24726",
            "txt": "#6c757d",
            "md": "#495057",
            "html": "#e83e8c",
            "csv": "#17a2b8",
            "jpg": "#fd7e14",
            "jpeg": "#fd7e14",
            "png": "#fd7e14",
            "gif": "#20c997",
            "svg": "#6610f2",
            "mp3": "#6f42c1",
            "wav": "#6f42c1",
            "mp4": "#dc3545",
            "avi": "#dc3545",
            "mov": "#dc3545",
            "mkv": "#dc3545",
        }
    
    def _update_color_shortcuts(self):
        """Update color shortcuts when theme changes"""
        self._setup_color_shortcuts()

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        self._build_topbar()
        body = tk.Frame(self, bg=self.BG); body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_centre(body)   # full width — no more right rail

    # ── Topbar ────────────────────────────────────────────────────────────────

    def _build_topbar(self):
        """Build an enhanced topbar with modern design"""
        bar = tk.Frame(self, bg=self.SIDEBAR_ALT, height=65)  # Use top bar color
        bar.pack(fill="x"); bar.pack_propagate(False)

        # Logo with enhanced styling and better spacing
        logo = tk.Frame(bar, bg=self.SIDEBAR_ALT)
        logo.pack(side="left", padx=24, pady=14)
        
        # Enhanced logo with gradient effect
        logo_main = tk.Label(logo, text="⬛ AI FileMat",
                            font=F["subtitle"], 
                            bg=self.SIDEBAR_ALT, fg=self.ACCENT)
        logo_main.pack(side="left")
        
        logo_ai = tk.Label(logo, text=" AI",
                          font=F["subtitle"], 
                          bg=self.SIDEBAR_ALT, fg=self.ACCENT)
        logo_ai.pack(side="left")

        # Enhanced hint section with better typography
        hint_frame = tk.Frame(bar, bg=self.SIDEBAR_ALT)
        hint_frame.pack(side="left", padx=30, pady=16)
        
        # Main hint
        main_hint = tk.Label(hint_frame, 
                           text="Convert • Split • Merge • Upscale • Analyse",
                           font=F["body"], 
                           bg=self.SIDEBAR_ALT, fg=self.TEXT2)
        main_hint.pack()
        
        # Zoom hint with better styling
        zoom_hint = tk.Label(hint_frame, 
                           text="Ctrl+Scroll to zoom • A+/- for quick zoom",
                           font=F["tiny"], 
                           bg=self.SIDEBAR_ALT, fg=self.DIM)
        zoom_hint.pack(pady=(2, 0))

        # Enhanced right controls with better spacing
        right = tk.Frame(bar, bg=self.SIDEBAR_ALT)
        right.pack(side="right", padx=20, pady=12)

        # Live operations badge with enhanced styling
        self.ops_badge = tk.Button(right, text="",
                                   font=F["small"], 
                                   bg=self.SIDEBAR, fg=self.ACCENT4,
                                   activebackground=self.CARD,
                                   relief="flat", cursor="hand2",
                                   padx=12, pady=8, bd=0,
                                   command=lambda: self._switch_tab("log"))
        self.ops_badge.pack(side="left", padx=(0, 12))
        self.ops_badge.pack_forget()  # hidden until something runs

        # Enhanced AI status label
        self.ai_status_lbl = tk.Label(right, text="", 
                                    font=F["small"], 
                                    bg=self.SIDEBAR_ALT, fg=self.TEXT2)
        self.ai_status_lbl.pack(side="left", padx=(0, 16))

        # Enhanced button groups with better visual organization
        btn_container = tk.Frame(right, bg=self.SIDEBAR_ALT)
        btn_container.pack(side="left")
        
        # Theme switcher with primary accent styling
        theme_group = tk.Frame(btn_container, bg=self.SIDEBAR_ALT)
        theme_group.pack(side="left", padx=(0, 8))
        
        self.theme_btn = tk.Button(theme_group, text="🎨 Theme",
                                 font=F["btn_small"],
                                 bg=self.ACCENT, fg="#ffffff",
                                 relief="flat", cursor="hand2",
                                 padx=12, pady=8, bd=0,
                                 command=self._show_theme_menu)
        self.theme_btn.pack(side="left")
        
        # Add hover effects to theme button
        def on_theme_enter(e):
            self.theme_btn.config(bg=self.ACTIVE)
        def on_theme_leave(e):
            self.theme_btn.config(bg=self.ACCENT)
        self.theme_btn.bind("<Enter>", on_theme_enter)
        self.theme_btn.bind("<Leave>", on_theme_leave)
        
        # Navigation group
        nav_group = tk.Frame(btn_container, bg=self.SIDEBAR_ALT)
        nav_group.pack(side="left", padx=(0, 8))
        mk_btn(nav_group, "📜 Log", 
               lambda: self._switch_tab("log"), 
               self.BORDER2, app=self).pack(side="left", padx=1)
        
        # Zoom group with enhanced styling
        zoom_group = tk.Frame(btn_container, bg=self.SIDEBAR_ALT)
        zoom_group.pack(side="left", padx=(0, 8))
        mk_btn(zoom_group, "A-", 
               self._zoom_out, 
               self.BORDER2, app=self).pack(side="left", padx=1)
        mk_btn(zoom_group, "A+", 
               self._zoom_in, 
               self.ACCENT, app=self).pack(side="left", padx=1)
        
        # Action group
        action_group = tk.Frame(btn_container, bg=self.SIDEBAR_ALT)
        action_group.pack(side="left")
        mk_btn(action_group, "⚙ Settings", 
               self._open_settings, 
               self.BORDER2, app=self).pack(side="left", padx=1)
        mk_btn(action_group, "📂 Output", 
               self._open_output, 
               self.BORDER2, app=self).pack(side="left", padx=1)
        mk_btn(action_group, "+ Add Files", 
               self._add_files, 
               self.ACCENT, app=self).pack(side="left", padx=(10, 1))

    # ── Left sidebar ──────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        """Build an enhanced sidebar with modern design"""
        # Create sidebar container with border
        self._sidebar_container = tk.Frame(parent, bg=self.SIDEBAR_BORDER)
        self._sidebar_container.pack(side="left", fill="y")
        self._sidebar_container.pack_propagate(False)
        
        # Create actual sidebar with inset from border
        self._sidebar = tk.Frame(self._sidebar_container, bg=self.SIDEBAR, width=188)
        self._sidebar.pack(side="left", fill="y", padx=1, pady=1)
        self._sidebar.pack_propagate(False)
        
        # Use self._sidebar for the sidebar content
        sb = self._sidebar

        # Enhanced sidebar header with better visual hierarchy
        header_frame = tk.Frame(sb, bg=self.SIDEBAR)
        header_frame.pack(fill="x", padx=16, pady=16)
        
        # Enhanced tools header with badge styling
        tools_header = tk.Label(header_frame, text="🔧 TOOLS", 
                               font=F["head"], 
                               bg=self.BADGE_BG, fg=self.BADGE_TEXT)
        tools_header.pack(anchor="w", fill="x", pady=(0, 8))
        
        # Enhanced zoom indicator with better styling
        self.zoom_indicator = tk.Label(header_frame, 
                                       text=f"🔍 Zoom: {int(self.ui_scale * 100)}%", 
                                       font=F["small"], 
                                       bg=self.SIDEBAR, fg=self.TEXT2)
        self.zoom_indicator.pack(anchor="w", pady=(6, 0))

        # Enhanced navigation buttons with proper active states
        self.active_tab = None  # Track active tab for selection highlighting
        for icon, label, key in self.TABS:
            # Create container for left border effect
            btn_container = tk.Frame(sb, bg=self.SIDEBAR, height=1)
            btn_container.pack(fill="x", padx=0, pady=0)
            btn_container.pack_propagate(False)
            
            # Create the button with transparent background initially
            btn = tk.Button(btn_container, text=f"  {icon}  {label}",
                           font=F["body"],
                           bg=self.SIDEBAR, fg=self.TEXT2,
                           relief="flat", bd=0, cursor="hand2",
                           anchor="w", padx=16, pady=12,
                           command=lambda k=key: self._switch_tab(k))
            btn.pack(fill="both", expand=True)
            self.tab_btns[key] = btn
            
            # Enhanced hover effects with better contrast
            def on_enter(e, b=btn, k=key, container=btn_container):
                if self.active_tab != k:  # Don't change if this is the active tab
                    b.config(bg=self.HOVER, fg=self.TEXT)  # Use darker text on hover
            def on_leave(e, b=btn, k=key, container=btn_container):
                if self.active_tab != k:  # Don't change if this is the active tab
                    b.config(bg=self.SIDEBAR, fg=self.TEXT2)  # Restore nav text color
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

        # Enhanced separator
        sep(sb, app=self).pack(fill="x", padx=12, pady=16)

        # Enhanced output section
        output_frame = tk.Frame(sb, bg=self.SIDEBAR)
        output_frame.pack(fill="x", padx=16, pady=(0, 12))
        
        # Enhanced output header with badge styling
        tk.Label(output_frame, text="📁 OUTPUT", 
                font=F["head"], 
                bg=self.BADGE_BG, fg=self.BADGE_TEXT).pack(anchor="w", fill="x", pady=(0, 8))
        
        # Enhanced output directory display
        self.out_dir_display = tk.Label(output_frame, 
                                       textvariable=self.out_dir,
                                       font=F["mono_small"],
                                       bg=self.SIDEBAR, fg=self.TEXT2,
                                       anchor="w",
                                       wraplength=140)
        self.out_dir_display.pack(fill="x", pady=(4, 0))
        
        # Enhanced change button
        mk_btn(output_frame, "📂 Change", 
               self._open_output, 
               self.BORDER2, app=self).pack(fill="x", pady=(8, 0))

        # Enhanced separator
        sep(sb, app=self).pack(fill="x", padx=12, pady=12)

        # Enhanced file status section
        file_frame = tk.Frame(sb, bg=self.SIDEBAR)
        file_frame.pack(fill="x", padx=16, pady=(0, 12))
        
        file_header = tk.Label(file_frame, text="📋  FILES", 
                               font=F["subhead"],
                               bg=self.SIDEBAR, fg=self.ACCENT)
        file_header.pack(anchor="w", pady=(0, 8))
        
        self.file_badge = tk.Label(file_frame, text="No files loaded",
                                   font=F["body_small"], 
                                   bg=self.SIDEBAR, fg=self.TEXT2,
                                   wraplength=170, justify="left")
        self.file_badge.pack(anchor="w")

        # Enhanced separator
        sep(sb, app=self).pack(fill="x", padx=12, pady=12)

        # Enhanced status section
        status_frame = tk.Frame(sb, bg=self.SIDEBAR)
        status_frame.pack(fill="x", padx=16, pady=(0, 16))
        
        status_header = tk.Label(status_frame, text="⚡  STATUS", 
                                 font=F["subhead"],
                                 bg=self.SIDEBAR, fg=self.ACCENT)
        status_header.pack(anchor="w", pady=(0, 8))
        
        self.dep_lbl = tk.Label(status_frame, text="", 
                                font=F["mono_tiny"],
                                bg=self.SIDEBAR, fg=self.TEXT2)
        self.dep_lbl.pack(anchor="w")
        self._refresh_deps()

    # ── Centre panel ──────────────────────────────────────────────────────────

    def _build_centre(self, parent):
        """Build the centre panel with all pages"""
        self._centre = tk.Frame(parent, bg=self.BG)
        self._centre.pack(side="left", fill="both", expand=True)
        
        # Create pages for each tab
        for _, _, key in self.TABS:
            f = tk.Frame(self._centre, bg=self.BG)
            self.pages[key] = f

        # Build individual pages
        self._build_home_page()
        self._build_aichat_page()
        self._build_command_page()
        self._build_convert_page()
        self._build_split_page()
        self._build_merge_page()
        self._build_video_page()
        self._build_organise_page()
        self._build_upscale_page()
        self._build_stamp_page()
        self._build_protect_page()
        self._build_compress_page()
        self._build_metadata_page()
        self._build_queue_page()
        self._build_log_page()

        # Slim status bar at very bottom — no log strip
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self._centre, textvariable=self.status_var,
                 font=F["small"], bg=self.LOG_BG, fg="#3a4f6e",
                 anchor="w", padx=10, pady=3).pack(fill="x", side="bottom")

    # ── AI Chat  (full tab) ───────────────────────────────────────────────────

    def _build_aichat_page(self):
        f = self.pages["aichat"]
        f.configure(bg=self.BG)

        # ── Top bar ───────────────────────────────────────────────────────────
        top = tk.Frame(f, bg=self.SIDEBAR, pady=10); top.pack(fill="x")

        left_top = tk.Frame(top, bg=self.SIDEBAR); left_top.pack(side="left", padx=18)
        tk.Label(left_top, text="🤖  AI Assistant",
                 font=("Segoe UI", 14, "bold"), bg=self.SIDEBAR, fg=self.TEXT).pack(side="left")
        self.ai_model_lbl = tk.Label(left_top, text="",
                 font=("Segoe UI", 9), bg=self.SIDEBAR, fg=self.TEXT2)
        self.ai_model_lbl.pack(side="left", padx=(12, 0))

        right_top = tk.Frame(top, bg=self.SIDEBAR); right_top.pack(side="right", padx=14)
        mk_btn(right_top, "🧠 Command Center", lambda: self._switch_tab("command"), self.BORDER2).pack(side="left", padx=4)
        mk_btn(right_top, "🗑  Clear Chat", self._clear_chat, self.BORDER2).pack(side="left", padx=4)
        mk_btn(right_top, "⚙  Settings",   self._open_settings, self.BORDER2).pack(side="left", padx=4)

        # ── Mode selector ─────────────────────────────────────────────────────
        mode_bar = tk.Frame(f, bg=self.CARD); mode_bar.pack(fill="x")
        tk.Label(mode_bar, text="Mode:", font=("Segoe UI", 9),
                 bg=self.CARD, fg=self.TEXT2).pack(side="left", padx=(14, 8), pady=8)
        self.ai_mode = tk.StringVar(value="chat")
        self._mode_btns: Dict[str, tk.Button] = {}
        modes = [
            ("chat",      "💬 Chat",       "Talk freely — ask anything"),
            ("qa",        "📄 Doc Q&A",    "Ask questions about a loaded file"),
            ("summarise", "📋 Summarise",  "Get a summary of a loaded file"),
            ("plan",      "🗂 Batch Plan", "Describe a goal — AI plans operations"),
        ]
        for val, label, tip in modes:
            b = tk.Button(mode_bar, text=label,
                          font=("Segoe UI", 9, "bold"),
                          bg=self.TAB_INACTIVE, fg=self.TAB_INACTIVE_TEXT,
                          relief="flat", cursor="hand2",
                          padx=12, pady=6, bd=0,
                          activebackground=self.TAB_ACTIVE,
                          activeforeground="#ffffff",
                          command=lambda v=val: self._set_ai_mode(v))
            b.pack(side="left", padx=(0, 2))
            Tooltip(b, tip)
            self._mode_btns[val] = b

        # File selector (shown only in qa / summarise modes)
        self.ai_file_frame = tk.Frame(f, bg=self.PANEL); self.ai_file_frame.pack(fill="x")
        file_inner = tk.Frame(self.ai_file_frame, bg=self.PANEL)
        file_inner.pack(anchor="w", padx=14, pady=6)
        tk.Label(file_inner, text="📎 Active file:", font=("Segoe UI", 9),
                 bg=self.PANEL, fg=self.TEXT2).pack(side="left")
        self.ai_file_var = tk.StringVar(value="(none — double-click a file in Queue tab)")
        self.ai_file_menu = tk.OptionMenu(file_inner, self.ai_file_var, "(none)")
        self.ai_file_menu.config(font=("Segoe UI", 9), bg=self.CARD2, fg=self.TEXT,
                                  activebackground=self.BORDER, relief="flat",
                                  bd=0, highlightthickness=0)
        self.ai_file_menu.pack(side="left", padx=(8, 0))

        # ── Chat history ──────────────────────────────────────────────────────
        chat_frame = tk.Frame(f, bg=self.BG)
        chat_frame.pack(fill="both", expand=True)
        
        # Create custom scrollbar styling
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure scrollbar colors based on current theme
        scrollbar_bg = self.C.get("border", "#c8ddf0")
        scrollbar_trough = self.C.get("panel", "#ffffff")
        scrollbar_thumb = self.C.get("accent", "#2196f3")
        
        style.configure("Custom.Horizontal.TScrollbar", 
                        background=scrollbar_bg,
                        troughcolor=scrollbar_trough,
                        bordercolor=scrollbar_bg,
                        arrowcolor=scrollbar_bg,
                        darkcolor=scrollbar_thumb,
                        lightcolor=scrollbar_thumb)
        
        style.configure("Custom.Vertical.TScrollbar", 
                        background=scrollbar_bg,
                        troughcolor=scrollbar_trough,
                        bordercolor=scrollbar_bg,
                        arrowcolor=scrollbar_bg,
                        darkcolor=scrollbar_thumb,
                        lightcolor=scrollbar_thumb)
        
        # Chat display with enhanced scrollbar
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            height=20, 
            font=F["chat"],
            bg=self.CHAT_BG, fg=self.TEXT,
            insertbackground=self.ACCENT,
            relief="flat", bd=0, wrap="word",
            padx=16, pady=12,
            selectbackground=self.ACCENT,
            selectforeground="#ffffff")
        
        self.chat_display.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.chat_display.config(state="disabled")

        # Tag styles — conversational bubble feel
        self.chat_display.tag_config("you_lbl",
            foreground=self.ACCENT, font=("Segoe UI", 9, "bold"))
        self.chat_display.tag_config("you_bubble",
            foreground="#e8f0ff",
            background="#1a2545",
            lmargin1=20, lmargin2=20, rmargin=60,
            spacing1=6, spacing3=6)
        self.chat_display.tag_config("ai_lbl",
            foreground=self.ACCENT3, font=("Segoe UI", 9, "bold"))
        self.chat_display.tag_config("ai_bubble",
            foreground="#e8fff4",
            background="#0a2018",
            lmargin1=20, lmargin2=20, rmargin=60,
            spacing1=6, spacing3=6)
        self.chat_display.tag_config("sys_msg",
            foreground=self.TEXT2, font=("Segoe UI", 9, "italic"),
            lmargin1=20, spacing1=2, spacing3=2)
        self.chat_display.tag_config("err_msg",
            foreground=self.ERROR, lmargin1=20, spacing1=4, spacing3=4)
        self.chat_display.tag_config("typing_msg",
            foreground=self.TEXT2, font=("Segoe UI", 9, "italic"),
            lmargin1=20)
        self.chat_display.tag_config("divider",
            foreground=self.DIM2)
        self.chat_display.tag_config("intent_msg",
            foreground=self.ACCENT4, font=("Segoe UI", 9),
            lmargin1=20, spacing1=2)

        # ── Quick suggestions ─────────────────────────────────────────────────
        suggest_bar = tk.Frame(f, bg=self.CARD); suggest_bar.pack(fill="x")
        tk.Label(suggest_bar, text="Try asking:",
                 font=("Segoe UI", 8), bg=self.CARD, fg=self.TEXT2).pack(side="left", padx=(14, 6), pady=6)
        suggestions = [
            ("What can you do?",            "What can you do for me?"),
            ("Summarise my file",           "Summarise selected file for me"),
            ("Best format?",                "What is best output format for my file and why?"),
            ("Plan my workflow",            "Look at my files and plan best set of operations for me"),
        ]
        for label, prompt in suggestions:
            b = tk.Button(suggest_bar, text=label,
                          font=("Segoe UI", 8),
                          bg=self.CHIP_BG, fg=self.CHIP_TEXT,
                          relief="flat", cursor="hand2",
                          padx=6, pady=3, bd=1,
                          command=lambda p=prompt: self._quick_prompt(p))
            
            # Add hover effects for suggestion chips
            def on_chip_enter(e):
                b.config(bg=self.HOVER)
            def on_chip_leave(e):
                b.config(bg=self.get_color("chip_bg", self.C))
            b.bind("<Enter>", on_chip_enter)
            b.bind("<Leave>", on_chip_leave)

        input_wrap = tk.Frame(f, bg=self.INPUT_BG)
        input_wrap.pack(fill="x")

        # Enhanced Input box + send side by side with better layout
        input_row = tk.Frame(input_wrap, bg=self.INPUT_BG)
        input_row.pack(fill="x", padx=16, pady=12)

        # Enhanced chat input with better styling and space
        self.chat_input = tk.Text(
            input_row, height=4,  # Increased height for better space
            font=F["body"],      # Use enhanced font system
            bg=self.INPUT_BG, fg=self.TEXT,
            relief="flat", bd=1,
            padx=12, pady=8,       # Better internal padding
            selectbackground=self.ACCENT,
            selectforeground="#ffffff")
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 12), ipady=8)
        
        # Enhanced key bindings
        self.chat_input.bind("<Return>", self._on_enter)
        self.chat_input.bind("<Shift-Return>", lambda e: None)
        self.chat_input.bind("<Control-Return>", self._send_btn)  # Ctrl+Enter to send

        # Enhanced placeholder with better styling
        self._placeholder = "💬 Type your message here... (Enter to send, Shift+Enter for new line, Ctrl+Enter for quick send)"
        self._placeholder_active = False
        self._set_placeholder()
        self.chat_input.bind("<FocusIn>", self._clear_placeholder)
        self.chat_input.bind("<FocusOut>", self._restore_placeholder)

        # Enhanced send column with better button layout
        send_col = tk.Frame(input_row, bg=self.INPUT_BG)
        send_col.pack(side="left", fill="y")
        
        # Primary send button with enhanced styling
        send_btn = tk.Button(send_col, text="Send\n📤",
                           command=self._send_btn,
                           font=F["btn"],
                           bg=self.ACCENT3, fg="#ffffff",
                           activebackground="#05b882",
                           relief="flat", cursor="hand2",
                           padx=16, pady=12, bd=0,
                           height=2)  # Make button taller
        send_btn.pack(fill="x", pady=(0, 6))
        
        # Add hover effects to send button
        def on_send_enter(e):
            send_btn.config(bg="#05b882")
        def on_send_leave(e):
            send_btn.config(bg=self.ACCENT3)
        send_btn.bind("<Enter>", on_send_enter)
        send_btn.bind("<Leave>", on_send_leave)
        
        # Secondary actions with better organization
        actions_frame = tk.Frame(send_col, bg=self.INPUT_BG)
        actions_frame.pack(fill="x")
        
        # Image analysis button
        mk_btn(actions_frame, "🖼 Image", self._analyse_image,
               self.BORDER2, padx=8, pady=4).pack(fill="x", pady=(0, 4))
        
        # Quick actions button
        quick_btn = tk.Button(actions_frame, text="⚡ Quick",
                             command=self._show_quick_actions,
                             font=F["btn_small"],
                             bg=self.BORDER2, fg=self.TEXT,
                             activebackground=self.HOVER,
                             relief="flat", cursor="hand2",
                             padx=8, pady=4, bd=0)
        quick_btn.pack(fill="x")
        
        # Add hover effects to quick button
        def on_quick_enter(e):
            quick_btn.config(bg=self.HOVER)
        def on_quick_leave(e):
            quick_btn.config(bg=self.BORDER2)
        quick_btn.bind("<Enter>", on_quick_enter)
        quick_btn.bind("<Leave>", on_quick_leave)

        # ── Welcome message ───────────────────────────────────────────────────
        self._set_ai_mode("chat", init=True)
        self._ai_sys(
            "👋  Hey! I'm your AI assistant. I'm here to help with your files.\n\n"
            "You can talk to me naturally — ask me to convert files, summarise documents, "
            "analyse images, plan a workflow, or just chat.\n\n"
            "To get started: add some files using + Add Files, then ask me anything!"
        )

    def _build_command_page(self):
        f = self.pages["command"]
        section_hdr(f, "AI COMMAND CENTER", "Review, edit and execute AI plans safely")

        top = card(f)
        lbl(top, "Intent summary", head=True).pack(anchor="w", pady=(0, 8))
        self.cmd_summary_var = tk.StringVar(
            value="No parsed plan yet. Ask AI in chat with a command (e.g. 'convert report.pdf to docx')."
        )
        tk.Label(top, textvariable=self.cmd_summary_var, font=F["body"], bg=self.PANEL, fg=self.TEXT2,
                 wraplength=900, justify="left").pack(anchor="w")

        json_card = card(f)
        hdr = tk.Frame(json_card, bg=self.PANEL); hdr.pack(fill="x")
        lbl(hdr, "Parsed intent JSON", head=True).pack(side="left")
        mk_btn(hdr, "Validate JSON", self._validate_command_json, self.BORDER2, pady=4).pack(side="right")
        self.cmd_json = tk.Text(json_card, height=14, font=F["mono_small"], bg=self.LOG_BG, fg=self.TEXT,
                                insertbackground=self.TEXT, relief="flat", bd=0, wrap="none")
        self.cmd_json.pack(fill="x", pady=(8, 0))

        files_card = card(f)
        lbl(files_card, "Files AI matched", head=True).pack(anchor="w", pady=(0, 8))
        self.cmd_files_lb = tk.Listbox(files_card, height=8, font=F["mono_small"], bg=self.LOG_BG, fg=self.TEXT,
                                       relief="flat", bd=0, selectbackground=self.ACCENT, selectforeground="#fff")
        self.cmd_files_lb.pack(fill="x")

        confirm = card(f)
        lbl(confirm, "Confirmation before execution", head=True).pack(anchor="w", pady=(0, 8))
        self.cmd_confirm_var = tk.BooleanVar(value=True)
        tk.Checkbutton(confirm,
            text="I have reviewed this plan and want to execute exactly this JSON plan",
            variable=self.cmd_confirm_var, font=F["small"], bg=self.PANEL, fg=self.TEXT2,
            selectcolor=self.ACCENT, activebackground=self.PANEL, cursor="hand2").pack(anchor="w")
        btns = tk.Frame(confirm, bg=self.PANEL); btns.pack(anchor="w", pady=(10, 0))
        mk_big_btn(btns, "▶ Run Exactly This Plan", self._run_command_plan, self.ACCENT3).pack(side="left", padx=(0, 8))
        mk_btn(btns, "↻ Sync from latest AI reply", self._sync_command_from_latest_intent, self.BORDER2).pack(side="left")
        self.cmd_dry_run_var = tk.StringVar(value="Dry-run: (edit JSON to preview)")
        tk.Label(confirm, textvariable=self.cmd_dry_run_var, font=F["mono_small"], bg=self.PANEL, fg=self.ACCENT4,
                 wraplength=920, justify="left").pack(anchor="w", pady=(10, 0))
        self.cmd_json.bind("<KeyRelease>", self._refresh_command_dry_run)
        self.after(0, self._refresh_command_dry_run)

    # ══════════════════════════════════════════════════════════════════════════
    # HOME PAGE  —  the friendly landing experience
    # ══════════════════════════════════════════════════════════════════════════

    def _build_home_page(self):
        f = self.pages["home"]

        # Hero area
        hero = tk.Frame(f, bg=self.BG); hero.pack(fill="x", padx=30, pady=(30, 0))
        tk.Label(hero, text="Welcome to File Workshop AI",
                 font=("Segoe UI", 22, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(hero, text="Your intelligent file toolkit. Convert · Split · Merge · Upscale · Analyse — all in one place.",
                 font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT2).pack(anchor="w", pady=(4, 0))

        sep(f).pack(fill="x", padx=30, pady=20)

        # Quick action cards row
        cards_row = tk.Frame(f, bg=self.BG); cards_row.pack(fill="x", padx=20, pady=(0, 16))

        quick_actions = [
            ("🔄", "Convert Files",   "PDF · DOCX · XLSX · PPTX · Images · Audio · Video",   "convert", self.ACCENT),
            ("🖼",  "Upscale Images",  "AI-quality upscaling up to 4×",                          "upscale", "#9b59b6"),
            ("✂️",  "Split Document",  "Break PDF or PPTX into pages/slides",                    "split",   self.ACCENT2),
            ("🔗", "Merge Files",     "Combine PDFs, images, presentations",                    "merge",   "#27ae60"),
            ("📐", "Organise PDF",    "Resequence · Delete · Rotate pages",                     "organise","#e67e22"),
            ("🔒", "Protect PDF",     "Encrypt or decrypt with password",                       "protect", "#c0392b"),
        ]

        for i, (icon, title, desc, tab, color) in enumerate(quick_actions):
            # Create card with border and shadow effect
            c2 = tk.Frame(cards_row, bg="#ffffff", padx=16, pady=14,
                          cursor="hand2", relief="solid", bd=1)
            c2.grid(row=i//3, column=i%3, padx=8, pady=8, sticky="ew")
            cards_row.columnconfigure(i%3, weight=1)

            tk.Label(c2, text=icon, font=("Segoe UI", 24),
                     bg="#ffffff", fg=color).pack(anchor="w")
            tk.Label(c2, text=title,
                     font=("Segoe UI", 11, "bold"), bg="#ffffff", fg="#1e2d45").pack(anchor="w", pady=(4, 0))
            tk.Label(c2, text=desc, font=("Segoe UI", 9),
                     bg="#ffffff", fg="#5a6a80", wraplength=200, justify="left").pack(anchor="w", pady=(2, 8))

            mk_btn(c2, f"Open {title.split()[0]} →",
                   lambda t=tab: self._switch_tab(t),
                   color, padx=10, pady=5).pack(anchor="w")

            # hover effect with proper restoration
            def on_enter(e, fr=c2): 
                fr.config(bg="#f8faff", relief="solid", bd=1)
            def on_leave(e, fr=c2): 
                fr.config(bg="#ffffff", relief="solid", bd=1)
            c2.bind("<Enter>", on_enter); c2.bind("<Leave>", on_leave)

        sep(f).pack(fill="x", padx=30, pady=(4, 16))

        # File drop zone
        drop_zone = tk.Frame(f, bg=self.CARD, padx=24, pady=18)
        drop_zone.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(drop_zone, text="📥  Add files to get started",
                 font=("Segoe UI", 12, "bold"), bg=self.CARD, fg=self.TEXT).pack(side="left")
        tk.Label(drop_zone,
                 text="  Supports: PDF · Word · Excel · PowerPoint · CSV · Images · Audio · Video",
                 font=("Segoe UI", 9), bg=self.CARD, fg=self.TEXT2).pack(side="left", pady=4)

        btn_area = tk.Frame(drop_zone, bg=self.CARD); btn_area.pack(side="right")
        mk_big_btn(btn_area, "+ Add Files",   self._add_files,  self.ACCENT).pack(side="left", padx=(0, 8))
        mk_btn(btn_area,     "+ Add Folder",  self._add_folder, self.BORDER2).pack(side="left")

        # Currently loaded files preview
        self.home_files_frame = tk.Frame(f, bg=self.BG); self.home_files_frame.pack(fill="x", padx=20)
        self._refresh_home_files()

    def _refresh_home_files(self):
        for w in self.home_files_frame.winfo_children(): w.destroy()
        if not self.files: return
        tk.Label(self.home_files_frame, text=f"📋  {len(self.files)} file(s) loaded:",
                 font=("Segoe UI", 9, "bold"), bg=self.BG, fg=self.TEXT2).pack(anchor="w", padx=10, pady=(8, 4))
        row = tk.Frame(self.home_files_frame, bg=self.BG); row.pack(fill="x", padx=10)
        for fp in self.files[:8]:  # show max 8
            c2 = cat(fp)
            color = {"pdf": "#e74c3c", "image": "#9b59b6", "excel": "#27ae60",
                     "pptx": "#e67e22", "docx": "#2980b9", "audio": "#1abc9c",
                     "video": "#e91e8c", "csv": "#16a085"}.get(c2, self.BORDER2)
            pill = tk.Frame(row, bg=color, padx=8, pady=3)
            pill.pack(side="left", padx=(0, 6), pady=2)
            tk.Label(pill, text=f"{cat_icon(c2)}  {Path(fp).name[:22]}",
                     font=("Segoe UI", 8), bg=color, fg="#ffffff").pack()
        if len(self.files) > 8:
            tk.Label(row, text=f"  +{len(self.files)-8} more",
                     font=("Segoe UI", 8), bg=self.BG, fg=self.TEXT2).pack(side="left")

    # ══════════════════════════════════════════════════════════════════════════
    # CONVERT PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_convert_page(self):
        f = self.pages["convert"]
        section_hdr(f, "CONVERT FILES", "Batch-convert any file to another format")

        fmt_card = card(f)
        lbl(fmt_card, "OUTPUT FORMAT", head=True).pack(anchor="w", pady=(0, 10))

        cats = [
            ("Documents",    ["txt", "docx", "pdf", "html"]),
            ("Spreadsheet",  ["xlsx", "csv"]),
            ("Presentation", ["pptx"]),
            ("Images",       ["png", "jpg", "webp", "bmp", "gif", "tiff", "ico"]),
            ("Audio",        ["mp3", "wav", "ogg", "flac", "aac", "m4a"]),
            ("Video",        ["mp4", "avi", "mov", "mkv", "webm", "gif"]),
        ]
        self.out_fmt = tk.StringVar(value="pdf")
        self._fmt_btns: Dict[str, tk.Button] = {}

        for cat_name, fmts in cats:
            row = tk.Frame(fmt_card, bg=self.PANEL); row.pack(fill="x", pady=3)
            lbl(row, f"{cat_name}:", dim=True, w=13).pack(side="left")
            for fmt in fmts:
                b = tk.Button(row, text=fmt.upper(), font=("Consolas", 9, "bold"),
                              bg=self.CARD2, fg=self.TEXT2, relief="flat",
                              padx=9, pady=4, cursor="hand2",
                              activebackground=self.ACCENT,
                              command=lambda f2=fmt: self._select_fmt(f2))
                b.pack(side="left", padx=3)
                self._fmt_btns[fmt] = b

        opt_card = card(f)
        lbl(opt_card, "OPTIONS", head=True).pack(anchor="w", pady=(0, 8))

        r1 = tk.Frame(opt_card, bg=self.PANEL); r1.pack(fill="x", pady=2)
        lbl(r1, "Pages (PDF/PPTX):", w=18).pack(side="left")
        self.conv_pages = tk.StringVar()
        entry(r1, self.conv_pages, width=22).pack(side="left", ipady=4, padx=(6, 6))
        lbl(r1, '"1,3,5-8" — blank = all', dim=True).pack(side="left")

        r2 = tk.Frame(opt_card, bg=self.PANEL); r2.pack(fill="x", pady=6)
        lbl(r2, "DPI (image export):", w=18).pack(side="left")
        self.conv_dpi = tk.StringVar(value="150")
        for val, label in [("72","72 draft"),("150","150 normal"),("300","300 print")]:
            tk.Radiobutton(r2, text=label, variable=self.conv_dpi, value=val,
                           font=F["small"], bg=self.PANEL, fg=self.TEXT2,
                           selectcolor=self.ACCENT, activebackground=self.PANEL,
                           cursor="hand2").pack(side="left", padx=(0, 14))

        self.conv_note = tk.Label(opt_card, text="", font=F["small"],
                                   bg=self.PANEL, fg=self.WARN, wraplength=580, justify="left")
        self.conv_note.pack(anchor="w", pady=(4, 0))

        # Now safe to set default
        self._select_fmt("pdf")

        btn_row = tk.Frame(f, bg=self.BG); btn_row.pack(pady=14)
        mk_big_btn(btn_row, "▶  RUN CONVERSION", self._run_convert).pack(side="left", padx=6)
        mk_btn(btn_row, "🤖 AI: Suggest Format", self._ai_suggest_format,
               self.ACCENT3, pady=10).pack(side="left", padx=6)

    # ══════════════════════════════════════════════════════════════════════════
    # UPSCALE PAGE  (new)
    # ══════════════════════════════════════════════════════════════════════════

    def _build_upscale_page(self):
        f = self.pages["upscale"]
        section_hdr(f, "IMAGE UPSCALER", "Enlarge images with high-quality resampling algorithms")

        # Source images info card
        info_card = card(f)
        lbl(info_card, "SELECTED IMAGES", head=True).pack(anchor="w", pady=(0, 6))
        self.upscale_info_lbl = tk.Label(info_card,
            text="Add image files to the queue, then configure and run.",
            font=F["small"], bg=self.PANEL, fg=self.TEXT2, wraplength=600, justify="left")
        self.upscale_info_lbl.pack(anchor="w")

        # Preview frame for first image
        self.upscale_preview_frame = tk.Frame(info_card, bg=self.PANEL)
        self.upscale_preview_frame.pack(anchor="w", pady=(6, 0))

        # Settings card
        settings_card = card(f)
        lbl(settings_card, "UPSCALE SETTINGS", head=True).pack(anchor="w", pady=(0, 12))

        # Scale factor
        scale_row = tk.Frame(settings_card, bg=self.PANEL); scale_row.pack(fill="x", pady=4)
        lbl(scale_row, "Scale factor:", w=16).pack(side="left")
        self.upscale_factor = tk.StringVar(value="2")
        for val, lbl_txt in [("1.5","1.5×"),("2","2×"),("3","3×"),("4","4×")]:
            tk.Radiobutton(scale_row, text=lbl_txt, variable=self.upscale_factor,
                           value=val, font=("Segoe UI", 10, "bold"),
                           bg=self.PANEL, fg=self.TEXT2,
                           selectcolor=self.ACCENT, activebackground=self.PANEL,
                           cursor="hand2").pack(side="left", padx=(0, 12))
        lbl(scale_row, "Custom:", w=8, dim=True).pack(side="left", padx=(12, 0))
        self.upscale_custom = tk.StringVar(value="")
        entry(scale_row, self.upscale_custom, width=5).pack(side="left", padx=(4, 0), ipady=4)
        lbl(scale_row, "× (overrides radio)", dim=True).pack(side="left", padx=(4, 0))

        # Method
        method_row = tk.Frame(settings_card, bg=self.PANEL); method_row.pack(fill="x", pady=6)
        lbl(method_row, "Algorithm:", w=16).pack(side="left")
        self.upscale_method = tk.StringVar(value="lanczos")
        method_cb = ttk.Combobox(method_row, textvariable=self.upscale_method,
                                  values=[m[0] for m in SCALE_METHODS],
                                  font=F["body"], width=14, state="readonly")
        method_cb.pack(side="left", padx=(0, 12))
        self.method_desc_lbl = tk.Label(method_row, text="",
                                         font=("Segoe UI", 9, "italic"),
                                         bg=self.PANEL, fg=self.TEXT2, wraplength=340)
        self.method_desc_lbl.pack(side="left")
        method_cb.bind("<<ComboboxSelected>>", self._update_method_desc)
        self._update_method_desc()

        # Sharpening
        sharp_row = tk.Frame(settings_card, bg=self.PANEL); sharp_row.pack(fill="x", pady=4)
        lbl(sharp_row, "Sharpness boost:", w=16).pack(side="left")
        self.upscale_sharpen = tk.StringVar(value="1.0")
        for val, label in [("1.0","None"),("1.3","Light"),("1.6","Medium"),("2.0","Strong")]:
            tk.Radiobutton(sharp_row, text=label, variable=self.upscale_sharpen,
                           value=val, font=F["small"],
                           bg=self.PANEL, fg=self.TEXT2,
                           selectcolor=self.ACCENT, activebackground=self.PANEL,
                           cursor="hand2").pack(side="left", padx=(0, 14))

        # Options row
        opts_row = tk.Frame(settings_card, bg=self.PANEL); opts_row.pack(fill="x", pady=4)
        lbl(opts_row, "Options:", w=16).pack(side="left")
        self.upscale_denoise = tk.BooleanVar(value=False)
        tk.Checkbutton(opts_row, text="Denoise before upscaling",
                        variable=self.upscale_denoise,
                        font=F["small"], bg=self.PANEL, fg=self.TEXT2,
                        selectcolor=self.ACCENT, activebackground=self.PANEL,
                        cursor="hand2").pack(side="left")

        # Output settings
        out_row = tk.Frame(settings_card, bg=self.PANEL); out_row.pack(fill="x", pady=(8, 0))
        lbl(out_row, "File suffix:", w=16).pack(side="left")
        self.upscale_suffix = tk.StringVar(value="_upscaled")
        entry(out_row, self.upscale_suffix, width=16).pack(side="left", ipady=4, padx=(6, 10))
        lbl(out_row, 'e.g.  photo_upscaled.png', dim=True).pack(side="left")

        # Progress bar
        self.upscale_progress_frame = tk.Frame(f, bg=self.BG)
        self.upscale_progress_frame.pack(fill="x", padx=14, pady=(0, 4))
        self.upscale_progress = ttk.Progressbar(self.upscale_progress_frame,
                                                  mode="determinate", length=400)
        self.upscale_progress_lbl = tk.Label(self.upscale_progress_frame,
                                              text="", font=F["small"], bg=self.BG, fg=self.TEXT2)

        btn_row = tk.Frame(f, bg=self.BG); btn_row.pack(pady=12)
        mk_big_btn(btn_row, "▶  UPSCALE IMAGES", self._run_upscale, "#9b59b6").pack(side="left", padx=6)
        mk_btn(btn_row, "🔍 Preview Info", self._upscale_preview_info,
               self.BORDER2, pady=10).pack(side="left", padx=6)
        mk_btn(btn_row, "🤖 AI Recommend", self._ai_upscale_recommend,
               self.ACCENT3, pady=10).pack(side="left", padx=6)

    # ══════════════════════════════════════════════════════════════════════════
    # SPLIT, MERGE, ORGANISE, STAMP, PROTECT, COMPRESS, METADATA, QUEUE pages
    # ══════════════════════════════════════════════════════════════════════════

    def _build_split_page(self):
        f = self.pages["split"]
        section_hdr(f, "SPLIT", "Break a PDF or PPTX into separate files")

        tc = card(f)
        lbl(tc, "FILE TYPE", head=True).pack(anchor="w", pady=(0, 6))
        self.split_type = tk.StringVar(value="pdf")
        self.split_info_lbl = tk.Label(tc, text="No PDF/PPTX in queue",
                                        font=F["small"], bg=self.PANEL, fg=self.TEXT2)
        self.split_info_lbl.pack(anchor="w", pady=(0, 4))
        for val, label in [("pdf","PDF — split pages"),("pptx","PPTX — split slides")]:
            tk.Radiobutton(tc, text=label, variable=self.split_type, value=val,
                           font=F["body"], bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT2, activebackground=self.PANEL,
                           command=self._update_split_ui, cursor="hand2").pack(anchor="w", pady=2)

        mc = card(f)
        lbl(mc, "MODE", head=True).pack(anchor="w", pady=(0, 8))
        self.split_mode = tk.StringVar(value="each")
        for val, label, tip in [
            ("each",   "Each page/slide → own file",  "10-page PDF → 10 files"),
            ("range",  "Range → one file",             "Pages 3–8 → one PDF"),
            ("custom", "Custom groups (PDF only)",     "1,10 | 3,5 | 2-4,7"),
        ]:
            r = tk.Frame(mc, bg=self.PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.split_mode, value=val,
                           font=F["body"], bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT2, activebackground=self.PANEL,
                           command=self._update_split_ui, cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")

        self.split_opts = card(f)
        self._update_split_ui()

        pr = tk.Frame(f, bg=self.BG); pr.pack(fill="x", padx=14, pady=2)
        lbl(pr, "File prefix:", w=12).pack(side="left")
        self.split_prefix = tk.StringVar(value="split")
        entry(pr, self.split_prefix, width=16).pack(side="left", padx=(6, 0), ipady=4)

        mk_big_btn(f, "▶  RUN SPLIT", self._run_split, self.ACCENT2).pack(pady=12)

    def _build_merge_page(self):
        f = self.pages["merge"]
        section_hdr(f, "MERGE", "Combine multiple files into one")

        tc = card(f)
        lbl(tc, "MERGE TYPE", head=True).pack(anchor="w", pady=(0, 6))
        self.merge_type = tk.StringVar(value="pdf")
        for val, label, tip in [
            ("pdf",  "→ PDF",  "Combine PDFs and/or images"),
            ("pptx", "→ PPTX", "Combine multiple presentations"),
        ]:
            r = tk.Frame(tc, bg=self.PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.merge_type, value=val,
                           font=F["body"], bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT, activebackground=self.PANEL,
                           cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")

        oc = card(f)
        r = tk.Frame(oc, bg=self.PANEL); r.pack(fill="x")
        lbl(r, "Output name:", w=14).pack(side="left")
        self.merge_name = tk.StringVar(value="merged_output")
        entry(r, self.merge_name, width=28).pack(side="left", padx=(6, 4), ipady=4)

        pc2 = card(f)
        lbl(pc2, "MERGE ORDER", head=True).pack(anchor="w", pady=(0, 6))
        self.merge_preview = tk.Text(pc2, height=7, font=F["mono_small"],
                                      bg=self.LOG_BG, fg=self.TEXT2,
                                      relief="flat", state="disabled", bd=0)
        self.merge_preview.pack(fill="x")
        mk_btn(pc2, "↻ Refresh", self._refresh_merge_preview, self.BORDER2).pack(anchor="w", pady=(6, 0))

        mk_big_btn(f, "▶  RUN MERGE", self._run_merge).pack(pady=12)

    def _build_video_page(self):
        f = self.pages["video"]
        section_hdr(f, "MEDIA TOOLS", "Split/merge audio or video by time — requires ffmpeg")

        if not HAS_FFMPEG:
            warn_card = card(f)
            tk.Label(warn_card,
                     text="⚠  ffmpeg not found.\n\n"
                          "Install it with:\n"
                          "  Ubuntu/Debian:  sudo apt install ffmpeg\n"
                          "  macOS:          brew install ffmpeg\n"
                          "  Windows:        https://ffmpeg.org/download.html",
                     font=("Consolas", 10), bg=self.PANEL, fg=self.WARN,
                     justify="left").pack(anchor="w")

        # Active file info
        info_c = card(f)
        self.video_info_lbl = tk.Label(info_c,
            text="Add a video or audio file to the queue, then configure below.",
            font=F["small"], bg=self.PANEL, fg=self.TEXT2, wraplength=620, justify="left")
        self.video_info_lbl.pack(anchor="w")
        self.video_duration_lbl = tk.Label(info_c, text="",
            font=("Consolas", 10, "bold"), bg=self.PANEL, fg=self.ACCENT3)
        self.video_duration_lbl.pack(anchor="w", pady=(4, 0))
        mk_btn(info_c, "📏 Load Duration", self._video_load_duration, self.BORDER2).pack(anchor="w", pady=(6, 0))

        # Operation selector
        op_c = card(f)
        lbl(op_c, "OPERATION", head=True).pack(anchor="w", pady=(0, 8))
        self.video_op = tk.StringVar(value="split")
        for val, label, tip in [
            ("split", "Split by time",   "Cut into segments using start/end timestamps"),
            ("merge", "Merge files",     "Join multiple video/audio files into one"),
        ]:
            r = tk.Frame(op_c, bg=self.PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.video_op, value=val,
                           font=F["body"], bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT, activebackground=self.PANEL,
                           command=self._update_video_ui, cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")

        # Dynamic options area
        self.video_opts = card(f)
        self._update_video_ui()

        # Output settings
        out_row = tk.Frame(f, bg=self.BG); out_row.pack(fill="x", padx=14, pady=2)
        lbl(out_row, "Output name:", w=14).pack(side="left")
        self.video_out_name = tk.StringVar(value="output")
        entry(out_row, self.video_out_name, width=22).pack(side="left", padx=(6, 4), ipady=4)
        lbl(out_row, "  (for merge only — split uses auto names)", dim=True).pack(side="left")

        btn_row = tk.Frame(f, bg=self.BG); btn_row.pack(pady=12)
        mk_big_btn(btn_row, "▶  RUN", self._run_video, "#e91e8c").pack(side="left", padx=6)
        mk_btn(btn_row, "🤖 AI: Suggest Settings", self._ai_video_suggest,
               self.ACCENT3, pady=10).pack(side="left", padx=6)

    def _update_video_ui(self):
        for w in self.video_opts.winfo_children(): w.destroy()
        op = self.video_op.get(); f = self.video_opts

        if op == "split":
            lbl(f, "TIME FORMAT:  HH:MM:SS  or  MM:SS  or  seconds  (e.g.  90  or  1:30  or  0:01:30)",
                dim=True).pack(anchor="w", pady=(0, 8))

            # Segments table header
            hdr_row = tk.Frame(f, bg=self.PANEL); hdr_row.pack(fill="x", pady=(0, 4))
            for txt, w in [("#", 3), ("Start time", 14), ("End time", 14), ("", 6)]:
                tk.Label(hdr_row, text=txt, font=("Consolas", 9, "bold"),
                         bg=self.PANEL, fg=self.TEXT2, width=w, anchor="w").pack(side="left", padx=4)

            # Scrollable segments frame
            seg_outer = tk.Frame(f, bg=self.PANEL)
            seg_outer.pack(fill="x")
            self.video_segments_frame = tk.Frame(seg_outer, bg=self.PANEL)
            self.video_segments_frame.pack(fill="x")
            self.video_segment_rows: List[tuple] = []  # (start_var, end_var, row_frame)

            # Add initial 3 rows
            for _ in range(3):
                self._add_segment_row()

            add_row = tk.Frame(f, bg=self.PANEL); add_row.pack(anchor="w", pady=(6, 0))
            mk_btn(add_row, "+ Add Segment", self._add_segment_row, self.BORDER2).pack(side="left")
            mk_btn(add_row, "✖ Remove Last", self._remove_last_segment, self.BORDER2).pack(side="left", padx=(6, 0))

            lbl(f, 'Tip: Use "end" as the End time to go to the end of the file.',
                dim=True).pack(anchor="w", pady=(8, 0))

            pr_row = tk.Frame(f, bg=self.PANEL); pr_row.pack(fill="x", pady=(8, 0))
            lbl(pr_row, "File prefix:", w=12).pack(side="left")
            self.video_prefix = tk.StringVar(value="segment")
            entry(pr_row, self.video_prefix, width=16).pack(side="left", padx=(6, 12), ipady=4)
            lbl(pr_row, "Output format:", w=14, dim=True).pack(side="left")
            self.video_fmt = tk.StringVar(value="")
            entry(pr_row, self.video_fmt, width=6).pack(side="left", padx=(4, 0), ipady=4)
            lbl(pr_row, " (blank = same as input)", dim=True).pack(side="left", padx=(4, 0))

        elif op == "merge":
            lbl(f, "All video/audio files currently in the queue will be merged in queue order.",
                dim=True, wrap=620).pack(anchor="w", pady=(0, 8))

            # Preview
            self.video_merge_preview = tk.Text(f, height=6, font=F["mono_small"],
                                                bg=self.LOG_BG, fg=self.TEXT2, relief="flat",
                                                state="disabled", bd=0)
            self.video_merge_preview.pack(fill="x", padx=2)
            mk_btn(f, "↻ Refresh Preview", self._refresh_video_merge_preview,
                   self.BORDER2).pack(anchor="w", pady=(6, 0))
            self._refresh_video_merge_preview()

            fmt_row = tk.Frame(f, bg=self.PANEL); fmt_row.pack(fill="x", pady=(10, 0))
            lbl(fmt_row, "Output format:", w=14, dim=True).pack(side="left")
            self.video_merge_fmt = tk.StringVar(value="mp4")
            for fmt in ["mp4", "mkv", "avi", "mov", "mp3", "wav", "flac", "aac", "ogg", "m4a"]:
                tk.Radiobutton(fmt_row, text=fmt, variable=self.video_merge_fmt, value=fmt,
                               font=F["btn"], bg=self.PANEL, fg=self.TEXT2,
                               selectcolor=self.ACCENT, activebackground=self.PANEL,
                               cursor="hand2").pack(side="left", padx=(0, 10))
            lbl(f, "Tip: for audio-only queues, prefer MP3/WAV/FLAC output formats.",
                dim=True).pack(anchor="w", pady=(6, 0))

    def _add_segment_row(self):
        if not hasattr(self, "video_segment_rows"):
            self.video_segment_rows = []
        i = len(self.video_segment_rows) + 1
        row = tk.Frame(self.video_segments_frame, bg=self.PANEL)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=f"{i:2d}.", font=("Consolas", 10),
                 bg=self.PANEL, fg=self.TEXT2, width=3).pack(side="left", padx=4)
        start_var = tk.StringVar(value="0:00:00")
        end_var   = tk.StringVar(value="end")
        entry(row, start_var, width=14).pack(side="left", padx=4, ipady=4)
        entry(row, end_var,   width=14).pack(side="left", padx=4, ipady=4)
        self.video_segment_rows.append((start_var, end_var, row))

    def _remove_last_segment(self):
        if hasattr(self, "video_segment_rows") and len(self.video_segment_rows) > 1:
            _, _, row = self.video_segment_rows.pop()
            row.destroy()

    def _refresh_video_merge_preview(self):
        if not hasattr(self, "video_merge_preview"): return
        av_files = [f for f in self.files if cat(f) in ("video", "audio")]
        self.video_merge_preview.config(state="normal")
        self.video_merge_preview.delete("1.0", "end")
        if not av_files:
            self.video_merge_preview.insert("end", "  No video/audio files in queue.")
        else:
            show_n = min(120, len(av_files))
            for i, fp in enumerate(av_files[:show_n], 1):
                self.video_merge_preview.insert("end", f"  {i:2d}.  {cat_icon(cat(fp))}  {Path(fp).name}\n")
            if len(av_files) > show_n:
                self.video_merge_preview.insert("end", f"\n  ... and {len(av_files)-show_n} more")
        self.video_merge_preview.config(state="disabled")

    def _build_organise_page(self):
        f = self.pages["organise"]
        section_hdr(f, "ORGANISE PDF", "Resequence · Delete · Rotate · Reverse pages")

        self.org_lbl_var = tk.StringVar(value="No PDF loaded — add one to the queue")
        ic = card(f)
        tk.Label(ic, textvariable=self.org_lbl_var, font=F["small"],
                 bg=self.PANEL, fg=self.SUCCESS).pack(anchor="w")

        oc = card(f)
        lbl(oc, "OPERATION", head=True).pack(anchor="w", pady=(0, 8))
        self.org_op = tk.StringVar(value="resequence")
        for val, label, tip in [
            ("resequence", "Resequence", "Custom order e.g. 3,1,2"),
            ("delete",     "Delete pages","Remove pages e.g. 2,5,7-9"),
            ("rotate",     "Rotate pages","90/180/270° on selected pages"),
            ("reverse",    "Reverse",     "Flip entire page order"),
        ]:
            r = tk.Frame(oc, bg=self.PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.org_op, value=val,
                           font=F["body"], bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT, activebackground=self.PANEL,
                           command=self._update_org_ui, cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")

        self.org_opts = card(f)
        self._update_org_ui()

        row = tk.Frame(f, bg=self.BG); row.pack(fill="x", padx=14, pady=2)
        lbl(row, "Output name:", w=14).pack(side="left")
        self.org_out_name = tk.StringVar(value="organised")
        entry(row, self.org_out_name, width=22).pack(side="left", padx=(6, 4), ipady=4)
        lbl(row, ".pdf", dim=True).pack(side="left")

        mk_big_btn(f, "▶  RUN ORGANISE", self._run_organise).pack(pady=12)

    def _build_stamp_page(self):
        f = self.pages["stamp"]
        section_hdr(f, "STAMP / WATERMARK", "Overlay text or PDF watermark on pages")

        mc = card(f)
        lbl(mc, "STAMP TYPE", head=True).pack(anchor="w", pady=(0, 6))
        self.stamp_mode = tk.StringVar(value="text")
        for val, label in [("text","Text watermark"),("pdf","PDF overlay")]:
            tk.Radiobutton(mc, text=label, variable=self.stamp_mode, value=val,
                           font=F["body"], bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT, activebackground=self.PANEL,
                           command=self._update_stamp_ui, cursor="hand2").pack(anchor="w", pady=2)
        self.stamp_opts = card(f); self._update_stamp_ui()

        pc2 = card(f)
        r = tk.Frame(pc2, bg=self.PANEL); r.pack(fill="x")
        lbl(r, "Pages (blank=all):", w=18).pack(side="left")
        self.stamp_pages = tk.StringVar()
        entry(r, self.stamp_pages, width=22).pack(side="left", padx=(6, 0), ipady=4)

        row = tk.Frame(f, bg=self.BG); row.pack(fill="x", padx=14, pady=2)
        lbl(row, "Output name:", w=14).pack(side="left")
        self.stamp_out_name = tk.StringVar(value="stamped")
        entry(row, self.stamp_out_name, width=22).pack(side="left", padx=(6, 4), ipady=4)
        lbl(row, ".pdf", dim=True).pack(side="left")
        mk_big_btn(f, "▶  RUN STAMP", self._run_stamp, self.ACCENT2).pack(pady=12)

    def _build_protect_page(self):
        f = self.pages["protect"]
        section_hdr(f, "PROTECT / DECRYPT", "Password-protect or unlock a PDF")
        mc = card(f)
        self.protect_mode = tk.StringVar(value="encrypt")
        for val, label, tip in [
            ("encrypt","Encrypt (add password)","Lock with password"),
            ("decrypt","Decrypt (remove password)","Requires current password"),
        ]:
            r = tk.Frame(mc, bg=self.PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.protect_mode, value=val,
                           font=F["body"], bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT, activebackground=self.PANEL,
                           cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")
        pc2 = card(f)
        lbl(pc2, "PASSWORD", head=True).pack(anchor="w", pady=(0, 8))
        for label, attr in [("User password:","protect_pw1"),("Owner password (opt.):","protect_pw2")]:
            r = tk.Frame(pc2, bg=self.PANEL); r.pack(fill="x", pady=3)
            lbl(r, label, w=22).pack(side="left")
            var = tk.StringVar(); setattr(self, attr, var)
            entry(r, var, width=24, show="•").pack(side="left", padx=(6, 0), ipady=4)
        row = tk.Frame(f, bg=self.BG); row.pack(fill="x", padx=14, pady=2)
        lbl(row, "Output name:", w=14).pack(side="left")
        self.protect_out = tk.StringVar(value="protected")
        entry(row, self.protect_out, width=22).pack(side="left", padx=(6, 4), ipady=4)
        lbl(row, ".pdf", dim=True).pack(side="left")
        mk_big_btn(f, "▶  RUN", self._run_protect).pack(pady=12)

    def _build_compress_page(self):
        f = self.pages["compress"]
        section_hdr(f, "COMPRESS PDF", "Reduce file size with lossless compression")
        ic = card(f)
        lbl(ic, "Compresses content streams (lossless). "
            "For image-heavy PDFs, re-export at lower DPI from Convert tab.",
            dim=True, wrap=620).pack(anchor="w")
        row = tk.Frame(f, bg=self.BG); row.pack(fill="x", padx=14, pady=10)
        lbl(row, "Output name:", w=14).pack(side="left")
        self.compress_out = tk.StringVar(value="compressed")
        entry(row, self.compress_out, width=22).pack(side="left", padx=(6, 4), ipady=4)
        lbl(row, ".pdf", dim=True).pack(side="left")
        mk_big_btn(f, "▶  RUN COMPRESS", self._run_compress).pack(pady=12)

    def _build_metadata_page(self):
        f = self.pages["metadata"]
        section_hdr(f, "PDF METADATA", "View and edit document properties")
        vc = card(f)
        lbl(vc, "CURRENT METADATA", head=True).pack(anchor="w", pady=(0, 6))
        self.meta_display = tk.Text(vc, height=8, font=F["mono"],
                                     bg=self.LOG_BG, fg=self.TEXT, relief="flat",
                                     state="disabled", bd=0)
        self.meta_display.pack(fill="x")
        br = tk.Frame(vc, bg=self.PANEL); br.pack(anchor="w", pady=(6, 0))
        mk_btn(br, "↻ Load", self._load_metadata, self.BORDER2).pack(side="left", padx=(0, 6))
        mk_btn(br, "🤖 AI Analyse", self._ai_analyse_metadata, self.ACCENT3).pack(side="left")
        ec = card(f)
        lbl(ec, "EDIT FIELDS", head=True).pack(anchor="w", pady=(0, 8))
        self.meta_fields: Dict[str, tk.StringVar] = {}
        for field in ["Title","Author","Subject","Creator"]:
            r = tk.Frame(ec, bg=self.PANEL); r.pack(fill="x", pady=3)
            lbl(r, field+":", w=10).pack(side="left")
            var = tk.StringVar(); self.meta_fields[field.lower()] = var
            entry(r, var, width=38).pack(side="left", padx=(6, 0), ipady=4)
        row = tk.Frame(f, bg=self.BG); row.pack(fill="x", padx=14, pady=2)
        lbl(row, "Output name:", w=14).pack(side="left")
        self.meta_out = tk.StringVar(value="updated_metadata")
        entry(row, self.meta_out, width=22).pack(side="left", padx=(6, 4), ipady=4)
        lbl(row, ".pdf", dim=True).pack(side="left")
        mk_big_btn(f, "▶  SAVE METADATA", self._run_metadata).pack(pady=12)

    # ══════════════════════════════════════════════════════════════════════════
    # LOG TAB  —  full operation history, parallel tracking, search
    # ══════════════════════════════════════════════════════════════════════════

    def _build_log_page(self):
        f = self.pages["log"]
        f.configure(bg=self.BG)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(f, bg=self.SIDEBAR, pady=10); hdr.pack(fill="x")
        tk.Label(hdr, text="📜  Operation Log",
                 font=("Segoe UI", 13, "bold"), bg=self.SIDEBAR, fg=self.TEXT).pack(side="left", padx=18)
        tk.Label(hdr, text="Full history of all operations — runs in background, never blocks your workflow",
                 font=("Segoe UI", 9), bg=self.SIDEBAR, fg=self.TEXT2).pack(side="left", padx=4)

        # Badge showing running count
        self.log_running_lbl = tk.Label(hdr, text="",
                                         font=("Segoe UI", 9, "bold"),
                                         bg=self.SIDEBAR, fg=self.ACCENT4)
        self.log_running_lbl.pack(side="right", padx=18)

        # ── Filter / search bar ───────────────────────────────────────────────
        filter_bar = tk.Frame(f, bg=self.CARD); filter_bar.pack(fill="x")

        tk.Label(filter_bar, text="Filter:", font=("Segoe UI", 9),
                 bg=self.CARD, fg=self.TEXT2).pack(side="left", padx=(14, 6), pady=8)

        self.log_filter_var = tk.StringVar()
        filter_entry = tk.Entry(filter_bar, textvariable=self.log_filter_var,
                                 font=("Consolas", 10),
                                 bg=self.CARD2, fg=self.TEXT, insertbackground=self.TEXT,
                                 relief="flat", bd=0, width=30)
        filter_entry.pack(side="left", ipady=4, padx=(0, 8))
        filter_entry.bind("<KeyRelease>", lambda e: self._apply_log_filter())

        # Filter type buttons
        self.log_filter_type = tk.StringVar(value="all")
        for val, label, col in [
            ("all",  "All",      self.TEXT2),
            ("ok",   "✔ Done",   self.SUCCESS),
            ("err",  "✖ Errors", self.ERROR),
            ("warn", "⚠ Warn",   self.WARN),
            ("info", "ℹ Info",   self.ACCENT),
        ]:
            tk.Radiobutton(filter_bar, text=label, variable=self.log_filter_type,
                           value=val, font=("Segoe UI", 9),
                           bg=self.CARD, fg=col,
                           selectcolor=self.CARD2,
                           activebackground=self.CARD, cursor="hand2",
                           command=self._apply_log_filter).pack(side="left", padx=(0, 10))

        # Right side controls
        mk_btn(filter_bar, "📋 Copy All", self._copy_log, self.BORDER2).pack(side="right", padx=4, pady=6)
        mk_btn(filter_bar, "🗑 Clear",    self._clear_log, self.BORDER2).pack(side="right", padx=4, pady=6)

        # ── Stats bar ─────────────────────────────────────────────────────────
        stats_bar = tk.Frame(f, bg=self.PANEL); stats_bar.pack(fill="x")
        self.log_stats_ok   = tk.Label(stats_bar, text="✔ 0",  font=("Segoe UI", 9, "bold"), bg=self.PANEL, fg=self.SUCCESS)
        self.log_stats_err  = tk.Label(stats_bar, text="✖ 0",  font=("Segoe UI", 9, "bold"), bg=self.PANEL, fg=self.ERROR)
        self.log_stats_warn = tk.Label(stats_bar, text="⚠ 0",  font=("Segoe UI", 9, "bold"), bg=self.PANEL, fg=self.WARN)
        self.log_stats_total= tk.Label(stats_bar, text="Total: 0", font=("Segoe UI", 9), bg=self.PANEL, fg=self.TEXT2)
        for w in [self.log_stats_total, self.log_stats_ok,
                  self.log_stats_err, self.log_stats_warn]:
            w.pack(side="left", padx=14, pady=4)

        # ── Log display ───────────────────────────────────────────────────────
        log_frame = tk.Frame(f, bg=self.LOG_BG)
        log_frame.pack(fill="both", expand=True, padx=0)

        self.log_box = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 10),
            bg=self.LOG_BG, fg=self.TEXT,
            insertbackground=self.TEXT,
            relief="flat", state="disabled", bd=0,
            padx=14, pady=8,
            spacing1=2, spacing3=2)
        self.log_box.pack(fill="both", expand=True)

        # Colour tags
        self.log_box.tag_config("ok",        foreground=self.SUCCESS)
        self.log_box.tag_config("err",        foreground=self.ERROR)
        self.log_box.tag_config("warn",       foreground=self.WARN)
        self.log_box.tag_config("info",       foreground=self.ACCENT)
        self.log_box.tag_config("ai",         foreground=self.ACCENT3)
        self.log_box.tag_config("ts",         foreground=self.DIM2)
        self.log_box.tag_config("op_start",   foreground=self.ACCENT4,  font=("Consolas", 10, "bold"))
        self.log_box.tag_config("op_done",    foreground=self.SUCCESS,  font=("Consolas", 10, "bold"))
        self.log_box.tag_config("op_fail",    foreground=self.ERROR,    font=("Consolas", 10, "bold"))
        self.log_box.tag_config("divider",    foreground=self.DIM2)

        # Internal log store (all entries, unfiltered)
        self._log_entries: List[Dict] = []  # {"ts", "msg", "kind", "op"}

        # Stats counters
        self._log_count = {"ok": 0, "err": 0, "warn": 0, "total": 0}

    def _build_queue_page(self):
        f = self.pages["queue"]
        section_hdr(f, "FILE QUEUE", "Manage staged files — Ctrl+click multi-select · double-click sets AI context")

        # Selection info bar
        sel_bar = tk.Frame(f, bg=self.BG); sel_bar.pack(fill="x", padx=12, pady=(0, 4))
        self.queue_sel_lbl = tk.Label(sel_bar,
            text="Tip: Ctrl+click to select multiple, then click ✖ Remove Selected",
            font=F["small"], bg=self.BG, fg=self.TEXT2)
        self.queue_sel_lbl.pack(side="left")
        self.queue_count_lbl = tk.Label(sel_bar, text="",
            font=("Consolas", 9, "bold"), bg=self.BG, fg=self.ACCENT3)
        self.queue_count_lbl.pack(side="right")

        # Listbox
        lf = tk.Frame(f, bg=self.PANEL)
        lf.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.queue_lb = tk.Listbox(
            lf, font=F["body"],
            bg=self.CARD2, fg=self.TEXT,
            selectbackground=self.ACCENT,
            activestyle="none", relief="flat", bd=0,
            selectmode="extended")
        sb2 = tk.Scrollbar(lf, orient="vertical", command=self.queue_lb.yview)
        self.queue_lb.config(yscrollcommand=sb2.set)
        self.queue_lb.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")

        # Bindings
        self.queue_lb.bind("<Double-Button-1>",  self._queue_select_for_ai)
        self.queue_lb.bind("<<ListboxSelect>>",  self._on_queue_select)
        self.queue_lb.bind("<Button-3>",          self._queue_right_click)  # right-click menu
        self.queue_lb.bind("<Delete>",            lambda e: self._remove_selected())

        # Button bar
        br = tk.Frame(f, bg=self.BG); br.pack(fill="x", padx=12, pady=(0, 4))

        # Left side — reorder + remove
        left_btns = tk.Frame(br, bg=self.BG); left_btns.pack(side="left")
        mk_btn(left_btns, "↑ Up",   self._move_up,   self.BORDER2).pack(side="left", padx=(0, 4))
        mk_btn(left_btns, "↓ Down", self._move_down, self.BORDER2).pack(side="left", padx=(0, 12))

        # Remove Selected — highlighted so users know it's per-selection
        self.remove_sel_btn = tk.Button(
            left_btns, text="✖  Remove Selected",
            command=self._remove_selected,
            font=F["btn"], bg="#5a1a1a", fg="#ff9999",
            activebackground=self.ACCENT2, activeforeground="#ffffff",
            relief="flat", cursor="hand2", padx=12, pady=5, bd=0)
        self.remove_sel_btn.pack(side="left", padx=(0, 4))
        Tooltip(self.remove_sel_btn,
                "Removes only the highlighted/selected items.\n"
                "Use Ctrl+click to select multiple files.\n"
                "Press Delete key also works.")

        mk_btn(left_btns, "🗑 Clear All", self._clear_queue, self.BORDER2).pack(side="left", padx=(0, 4))

        # Right side — AI + select-all
        right_btns = tk.Frame(br, bg=self.BG); right_btns.pack(side="right")
        mk_btn(right_btns, "☑ Select All",   self._select_all_queue, self.BORDER2).pack(side="left", padx=(0, 6))
        mk_btn(right_btns, "🤖 AI Analyse",  self._ai_analyse_selected, self.ACCENT3).pack(side="left")

        # Right-click context menu (created once, reused)
        self._queue_ctx_menu = tk.Menu(self, tearoff=0,
                                        bg=self.CARD2, fg=self.TEXT,
                                        activebackground=self.ACCENT,
                                        activeforeground="#ffffff",
                                        font=F["body"])
        self._queue_ctx_menu.add_command(label="✖  Remove Selected",  command=self._remove_selected)
        self._queue_ctx_menu.add_command(label="☑  Select All",        command=self._select_all_queue)
        self._queue_ctx_menu.add_separator()
        self._queue_ctx_menu.add_command(label="↑  Move Up",           command=self._move_up)
        self._queue_ctx_menu.add_command(label="↓  Move Down",         command=self._move_down)
        self._queue_ctx_menu.add_separator()
        self._queue_ctx_menu.add_command(label="🤖 AI Analyse",        command=self._ai_analyse_selected)
        self._queue_ctx_menu.add_command(label="📎 Set as AI context",  command=self._queue_select_for_ai)

    # ══════════════════════════════════════════════════════════════════════════
    # DYNAMIC SUB-UIs
    # ══════════════════════════════════════════════════════════════════════════


# ═══ END OF PART 1 — paste app_part2.py directly below this line ═══
    def _update_split_ui(self):
        for w in self.split_opts.winfo_children(): w.destroy()
        mode = self.split_mode.get(); f = self.split_opts
        if mode == "each":
            lbl(f, "Every page/slide becomes its own numbered file.").pack(anchor="w")
        elif mode == "range":
            r = tk.Frame(f, bg=self.PANEL); r.pack(anchor="w")
            lbl(r, "Start:", w=7).pack(side="left")
            self.range_start = tk.StringVar(value="1")
            entry(r, self.range_start, width=5).pack(side="left", padx=(4,12), ipady=4)
            lbl(r, "End:", w=5).pack(side="left")
            self.range_end = tk.StringVar(value="5")
            entry(r, self.range_end, width=5).pack(side="left", padx=(4,0), ipady=4)
        elif mode == "custom":
            lbl(f, "Groups by  |  ·  Pages by  ,  ·  Ranges with  -  (PDF only)", dim=True).pack(anchor="w")
            lbl(f, "Example:   1,10 | 3,5 | 2-4,7", head=True).pack(anchor="w", pady=(2,4))
            self.custom_groups = tk.StringVar(value="1,2 | 3,4 | 5-7")
            entry(f, self.custom_groups, width=40).pack(fill="x", ipady=5)

    def _update_org_ui(self):
        for w in self.org_opts.winfo_children(): w.destroy()
        op = self.org_op.get(); f = self.org_opts
        if op == "resequence":
            lbl(f, "New page order (pages not listed are DROPPED)", dim=True).pack(anchor="w")
            lbl(f, "Example:  3,1,2  →  page 3 first", head=True).pack(anchor="w", pady=(2,4))
            self.org_seq = tk.StringVar(value="1,2,3")
            entry(f, self.org_seq, width=40).pack(fill="x", ipady=5)
        elif op == "delete":
            lbl(f, "Pages to DELETE — all others are kept", dim=True).pack(anchor="w")
            lbl(f, "Example:  2,5,7-9", head=True).pack(anchor="w", pady=(2,4))
            self.org_del_pages = tk.StringVar(value="")
            entry(f, self.org_del_pages, width=40).pack(fill="x", ipady=5)
        elif op == "rotate":
            r = tk.Frame(f, bg=self.PANEL); r.pack(fill="x", pady=2)
            lbl(r, "Degrees:", w=10).pack(side="left")
            self.org_rotate_deg = tk.StringVar(value="90")
            for d in ["90","180","270"]:
                tk.Radiobutton(r, text=d+"°", variable=self.org_rotate_deg, value=d,
                               font=F["btn"], bg=self.PANEL, fg=self.TEXT2,
                               selectcolor=self.ACCENT, activebackground=self.PANEL,
                               cursor="hand2").pack(side="left", padx=(0,12))
            r2 = tk.Frame(f, bg=self.PANEL); r2.pack(fill="x", pady=(4,0))
            lbl(r2, "Pages (blank=all):", w=18).pack(side="left")
            self.org_rotate_pages = tk.StringVar(value="")
            entry(r2, self.org_rotate_pages, width=22).pack(side="left", padx=(6,0), ipady=4)
        elif op == "reverse":
            lbl(f, "Entire page order will be reversed.").pack(anchor="w")

    def _update_stamp_ui(self):
        for w in self.stamp_opts.winfo_children(): w.destroy()
        mode = self.stamp_mode.get(); f = self.stamp_opts
        if mode == "text":
            lbl(f, "self.TEXT WATERMARK", head=True).pack(anchor="w", pady=(0,8))
            for label, attr, default in [
                ("Watermark text:","stamp_text","CONFIDENTIAL"),
                ("Font size:",     "stamp_size","48"),
                ("Color (hex):",   "stamp_color","#888888"),
                ("Opacity (0–1):","stamp_opacity","0.3"),
                ("Angle (°):",    "stamp_angle","45"),
            ]:
                r = tk.Frame(f, bg=self.PANEL); r.pack(fill="x", pady=2)
                lbl(r, label, w=18).pack(side="left")
                var = tk.StringVar(value=default); setattr(self, attr, var)
                entry(r, var, width=22).pack(side="left", padx=(6,0), ipady=4)
        else:
            lbl(f, "PDF OVERLAY", head=True).pack(anchor="w", pady=(0,8))
            r = tk.Frame(f, bg=self.PANEL); r.pack(fill="x")
            self.stamp_wm_path = tk.StringVar(value="")
            entry(r, self.stamp_wm_path, width=36).pack(side="left", fill="x", expand=True, ipady=4, padx=(0,6))
            mk_btn(r, "Browse", self._browse_stamp_pdf, self.BORDER2).pack(side="left")

    def _update_method_desc(self, _=None):
        m = self.upscale_method.get()
        descs = dict(SCALE_METHODS)
        desc = descs.get(m, "")
        if hasattr(self, "method_desc_lbl"):
            self.method_desc_lbl.config(text=desc)

    # ══════════════════════════════════════════════════════════════════════════
    # RUN HANDLERS
    # ══════════════════════════════════════════════════════════════════════════

    def _require_pdf(self, label=""):
        pdfs = [f for f in self.files if cat(f) == "pdf"]
        if not pdfs:
            messagebox.showwarning(label or "No PDF", "Add a PDF file to the queue first.")
            return None
        return pdfs[0]

    def _require_out(self):
        out = self.out_dir.get()
        if not out:
            messagebox.showwarning("No Output Folder", "Set an output folder in the sidebar first.")
            return None
        return out

    def _run_task(self, name: str, fn, on_done=None):
        """
        Wrapper: runs fn() in a background thread, tracks it in the op counter,
        logs start/finish automatically, opens output folder when done.
        fn should call self._log() for progress messages.
        """
        self._op_start(name)
        self._switch_tab("log") if False else None  # don't auto-switch, just badge

        def _worker():
            success = True
            try:
                fn()
            except Exception as e:
                self._log(f"✖  {name}: {e}", "err")
                success = False
            finally:
                self._op_done(name, success)
                if success and on_done:
                    self.after(300, on_done)
        threading.Thread(target=_worker, daemon=True).start()

    def _run_convert(self):
        if not self.files: messagebox.showwarning("No Files","Add files first."); return
        out = self._require_out()
        if not out: return
        fmt = self.out_fmt.get()
        pages_str = self.conv_pages.get().strip()
        try: dpi = int(self.conv_dpi.get())
        except: dpi = 150

        def task():
            total = len(self.files); ok = 0
            for idx, src in enumerate(list(self.files)):
                self._status(f"Converting {idx+1}/{total}: {Path(src).name}")
                try:
                    results = do_convert(src, fmt, out, pages_str, dpi, log=self._log)
                    for r in results: self._log(f"→ {Path(r).name}", "ok")
                    ok += 1
                except Exception as e: self._log(f"✖ {Path(src).name}: {e}", "err")
            self._log(f"Done — {ok}/{total} converted.", "info")
            self._status(f"Done — {ok}/{total} converted")

        self._run_task(f"Convert {len(self.files)} file(s) → {fmt.upper()}", task, self._open_output)

    def _run_upscale(self):
        images = [f for f in self.files if cat(f) == "image"]
        if not images: messagebox.showwarning("No Images","Add image files to the queue."); return
        out = self._require_out()
        if not out: return
        if not UP_PIL: messagebox.showerror("Missing","pip install Pillow"); return

        # resolve scale
        custom = self.upscale_custom.get().strip()
        try:
            scale = float(custom) if custom else float(self.upscale_factor.get())
        except ValueError:
            messagebox.showerror("Invalid Scale","Enter a valid scale number."); return
        if scale < 1.1 or scale > 8:
            messagebox.showerror("Invalid Scale","Scale must be between 1.1 and 8."); return

        method  = self.upscale_method.get()
        sharpen = float(self.upscale_sharpen.get())
        denoise = self.upscale_denoise.get()
        suffix  = self.upscale_suffix.get().strip() or "_upscaled"

        # Show progress bar
        self.upscale_progress_frame.pack(fill="x", padx=14, pady=(0, 4))
        self.upscale_progress.pack(fill="x")
        self.upscale_progress_lbl.pack(anchor="w")
        self.upscale_progress["maximum"] = len(images)
        self.upscale_progress["value"] = 0

        def task():
            ok = 0
            for i, src in enumerate(images):
                self._status(f"Upscaling {i+1}/{len(images)}: {Path(src).name}")
                self.after(0, lambda v=i: self.upscale_progress.config(value=v))
                self.after(0, lambda n=Path(src).name: self.upscale_progress_lbl.config(
                    text=f"Processing: {n}"))
                stem = Path(src).stem; ext = Path(src).suffix
                dst = os.path.join(out, f"{stem}{suffix}{ext}")
                try:
                    _, orig, new = upscale_image(src, dst, scale, method, sharpen, denoise, self._log)
                    self._log(f"✔ {Path(dst).name}  {orig[0]}×{orig[1]} → {new[0]}×{new[1]}", "ok")
                    ok += 1
                except Exception as e:
                    self._log(f"✖ {Path(src).name}: {e}", "err")
            self.after(0, lambda: self.upscale_progress.config(value=len(images)))
            self.after(0, lambda: self.upscale_progress_lbl.config(
                text=f"Done — {ok}/{len(images)} images upscaled"))
            self._log(f"Upscale complete — {ok}/{len(images)} images.", "info")
            self._status(f"Upscale done — {ok}/{len(images)}")

        self._run_task(f"Upscale {len(images)} image(s) ×{scale}", task, self._open_output)

    def _upscale_preview_info(self):
        images = [f for f in self.files if cat(f) == "image"]
        if not images:
            self._ai_sys("⚠  No image files in the queue."); return
        for w in self.upscale_preview_frame.winfo_children(): w.destroy()
        for fp in images[:4]:
            info = get_image_info(fp)
            if info:
                txt = (f"📷 {Path(fp).name}  —  "
                       f"{info['width']}×{info['height']}  "
                       f"{info['mode']}  {info['size_kb']}")
                tk.Label(self.upscale_preview_frame, text=txt,
                         font=("Consolas", 9), bg=self.PANEL, fg=self.TEXT2).pack(anchor="w")
        self.upscale_info_lbl.config(
            text=f"{len(images)} image(s) ready to upscale.", fg=self.SUCCESS)

    def _run_split(self):
        out = self._require_out()
        if not out: return
        stype = self.split_type.get(); mode = self.split_mode.get()
        prefix = self.split_prefix.get().strip() or "split"
        if stype == "pptx":
            pptxs = [f for f in self.files if cat(f) == "pptx"]
            if not pptxs: messagebox.showwarning("No PPTX","Add a PPTX first."); return
            src = pptxs[0]
            def ptask():
                files = pptx_split_slides(src, out, prefix)
                self._log(f"✔ {len(files)} slide files created.", "ok")
            self._run_task(f"Split PPTX: {Path(src).name}", ptask, self._open_output); return
        src = self._require_pdf("Split")
        if not src: return
        def task():
            if mode == "each":
                files = split_each(src, out)
                self._log(f"✔ {len(files)} files.", "ok")
            elif mode == "range":
                try: s, e = int(self.range_start.get()), int(self.range_end.get())
                except: self._log("⚠ Invalid range.", "err"); return
                p = split_range(src, s, e, out)
                self._log(f"✔ {Path(p).name}", "ok")
            elif mode == "custom":
                groups = parse_groups(self.custom_groups.get(), self.page_count or 9999)
                if not groups: self._log("⚠ No valid groups.", "err"); return
                files = split_custom(src, groups, out)
                for fp in files: self._log(f"  → {Path(fp).name}")
                self._log(f"✔ {len(files)} files.", "ok")
        self._run_task(f"Split PDF: {Path(src).name}", task, self._open_output)

    def _run_merge(self):
        if not self.files: messagebox.showwarning("Merge","Add files first."); return
        out = self._require_out()
        if not out: return
        mtype = self.merge_type.get()
        dst = os.path.join(out, (self.merge_name.get().strip() or "merged_output") + "." + mtype)
        srcs = list(self.files)
        def task():
            merge_pdfs(srcs, dst) if mtype == "pdf" else pptx_merge(srcs, dst)
            self._log(f"✔ {Path(dst).name}  ({os.path.getsize(dst)/1024:.1f} KB)", "ok")
        self._run_task(f"Merge {len(srcs)} files → {mtype.upper()}", task, self._open_output)

    # ── Video run handlers ────────────────────────────────────────────────────

    def _video_load_duration(self):
        """Load and display duration of the first video/audio file in queue."""
        av = [f for f in self.files if cat(f) in ("video", "audio")]
        if not av:
            messagebox.showinfo("No Media", "Add a video or audio file to the queue first.")
            return
        if not HAS_FFMPEG:
            self._log("⚠ ffmpeg not found — sudo apt install ffmpeg", "err")
            return
        src = av[0]
        def task():
            try:
                dur = video_get_duration(src)
                dur_str = format_duration(dur)
                self.after(0, lambda: self.video_info_lbl.config(
                    text=f"File: {Path(src).name}", fg=self.TEXT))
                self.after(0, lambda: self.video_duration_lbl.config(
                    text=f"⏱  Duration: {dur_str}  ({dur:.1f} seconds)"))
                self._log(f"Duration of {Path(src).name}: {dur_str}", "info")
            except Exception as e:
                self._log(f"Could not read duration: {e}", "err")
        threading.Thread(target=task, daemon=True).start()

    def _run_video(self):
        out = self._require_out()
        if not out: return
        if not HAS_FFMPEG:
            messagebox.showerror("ffmpeg Missing",
                "ffmpeg is required for video/audio operations.\n\n"
                "Install: sudo apt install ffmpeg")
            return
        op = self.video_op.get()

        if op == "split":
            av = [f for f in self.files if cat(f) in ("video", "audio")]
            if not av:
                messagebox.showwarning("No Media", "Add a video or audio file to the queue.")
                return
            src = av[0]

            # Build segments list from the rows
            if not hasattr(self, "video_segment_rows") or not self.video_segment_rows:
                messagebox.showwarning("No Segments", "Add at least one segment.")
                return

            segments = []
            for i, (sv, ev, _) in enumerate(self.video_segment_rows, 1):
                start = sv.get().strip()
                end   = ev.get().strip()
                if not start:
                    messagebox.showerror("Empty Start",
                        f"Segment {i}: start time cannot be empty.")
                    return
                try:
                    _parse_time(start)  # validate
                    if end.lower() not in ("end", ""):
                        _parse_time(end)
                except ValueError as e:
                    messagebox.showerror("Invalid Time", f"Segment {i}: {e}")
                    return
                segments.append((start, end or "end"))

            prefix = self.video_prefix.get().strip() or "segment"
            fmt    = self.video_fmt.get().strip().lstrip(".")

            def task():
                self._log(f"Splitting {Path(src).name} into {len(segments)} segment(s) …")
                split_fn = audio_split if cat(src) == "audio" else video_split
                files = split_fn(src, segments, out, prefix, fmt)
                for fp in files:
                    sz = os.path.getsize(fp) / (1024*1024)
                    self._log(f"✔ {Path(fp).name}  ({sz:.1f} MB)", "ok")
                self._log(f"Split complete — {len(files)} segment(s) saved.", "info")
                self._status(f"Split done — {len(files)} segments")
            self._run_task(f"Video Split: {Path(src).name}", task, self._open_output)

        elif op == "merge":
            av = [f for f in self.files if cat(f) in ("video", "audio")]
            if len(av) < 2:
                messagebox.showwarning("Need 2+ Files",
                    "Add at least 2 video or audio files to the queue.")
                return
            ext  = self.video_merge_fmt.get().strip() or "mp4"
            name = (self.video_out_name.get().strip() or "output") + "." + ext
            dst  = os.path.join(out, name)

            only_audio = all(cat(fp) == "audio" for fp in av)

            def task():
                self._log(f"Merging {len(av)} file(s) → {name} …")
                merge_fn = audio_merge if only_audio else video_merge
                merge_fn(av, dst, log=self._log)
                sz = os.path.getsize(dst) / (1024*1024)
                self._log(f"✔ {Path(dst).name}  ({sz:.1f} MB)", "ok")
                self._status(f"Merge done — {Path(dst).name}")
            mode_label = "Audio Merge" if only_audio else "Media Merge"
            self._run_task(f"{mode_label} → {name}", task, self._open_output)

    def _ai_video_suggest(self):
        """Ask AI for advice about the current video/audio file."""
        av = [f for f in self.files if cat(f) in ("video", "audio")]
        if not av:
            self._ai_sys("⚠  Add a video or audio file to the queue first.")
            return
        if not self.ai.is_ready:
            self._ai_sys("⚠  Configure AI in Settings first.")
            return
        src = av[0]
        ext = Path(src).suffix.lower()
        prompt = (
            f"I have a {cat(src)} file: {Path(src).name} ({ext})\n"
            f"I want to split it into segments or merge it with other files.\n"
            f"What format should I use for the output? Any tips on ffmpeg settings "
            f"for best quality vs file size? Keep it brief and practical."
        )
        self._ai_user(f"Suggest settings for: {Path(src).name}")
        self.ai.chat(prompt, on_done=self._ai_response, on_error=self._ai_error)

    def _run_organise(self):
        src = self._require_pdf("Organise"); out = self._require_out()
        if not src or not out: return
        op = self.org_op.get()
        dst = os.path.join(out, (self.org_out_name.get().strip() or "organised") + ".pdf")
        pc = self.page_count or pdf_page_count(src)
        def task():
            if op == "resequence":
                order = [p for p in parse_pages(self.org_seq.get(), pc*10) if 1<=p<=pc]
                if not order: self._log("⚠ No valid order.", "err"); return
                resequence_pdf(src, order, dst)
            elif op == "delete":
                pages = parse_pages(self.org_del_pages.get(), pc)
                if not pages: self._log("⚠ No pages.", "err"); return
                delete_pages(src, pages, dst)
            elif op == "rotate":
                try: deg = int(self.org_rotate_deg.get())
                except: deg = 90
                pstr = self.org_rotate_pages.get().strip()
                pages = parse_pages(pstr, pc) if pstr else None
                rotate_pages(src, deg, pages, dst)
            elif op == "reverse":
                reverse_pdf(src, dst)
            self._log(f"✔ {Path(dst).name}  ({os.path.getsize(dst)/1024:.1f} KB)", "ok")
        self._run_task(f"Organise PDF ({op}): {Path(src).name}", task, self._open_output)

    def _run_stamp(self):
        src = self._require_pdf("Stamp"); out = self._require_out()
        if not src or not out: return
        mode = self.stamp_mode.get()
        dst = os.path.join(out, (self.stamp_out_name.get().strip() or "stamped") + ".pdf")
        pc = self.page_count or pdf_page_count(src)
        pstr = self.stamp_pages.get().strip()
        pages = parse_pages(pstr, pc) if pstr else None
        def task():
            if mode == "text":
                text = self.stamp_text.get().strip() or "WATERMARK"
                try: fsize = int(self.stamp_size.get())
                except: fsize = 48
                color = self.stamp_color.get().strip() or "#888888"
                try: opacity = float(self.stamp_opacity.get())
                except: opacity = 0.3
                try: angle = int(self.stamp_angle.get())
                except: angle = 45
                watermark_text(src, dst, text, opacity, fsize, color, angle, pages)
            else:
                wm = self.stamp_wm_path.get().strip()
                if not wm or not os.path.isfile(wm):
                    self._log("⚠ Select watermark PDF.", "err"); return
                watermark_pdf_overlay(src, wm, dst, pages)
            self._log(f"✔ {Path(dst).name}", "ok")
        self._run_task(f"Stamp PDF: {Path(src).name}", task, self._open_output)

    def _run_protect(self):
        src = self._require_pdf("Protect"); out = self._require_out()
        if not src or not out: return
        mode = self.protect_mode.get()
        pw1 = self.protect_pw1.get(); pw2 = self.protect_pw2.get()
        dst = os.path.join(out, (self.protect_out.get().strip() or "protected") + ".pdf")
        def task():
            if mode == "encrypt":
                if not pw1: self._log("⚠ Enter a password.", "err"); return
                encrypt_pdf(src, dst, pw1, pw2)
            else:
                if not pw1: self._log("⚠ Enter the password.", "err"); return
                decrypt_pdf(src, dst, pw1)
            self._log(f"✔ {Path(dst).name}", "ok")
        self._run_task(f"{'Encrypt' if mode=='encrypt' else 'Decrypt'} PDF: {Path(src).name}",
                       task, self._open_output)

    def _run_compress(self):
        src = self._require_pdf("Compress"); out = self._require_out()
        if not src or not out: return
        dst = os.path.join(out, (self.compress_out.get().strip() or "compressed") + ".pdf")
        before = os.path.getsize(src)/1024
        def task():
            compress_pdf(src, dst)
            after = os.path.getsize(dst)/1024
            self._log(f"✔ {Path(dst).name}  ({after:.1f} KB)  saved {before-after:.1f} KB", "ok")
        self._run_task(f"Compress PDF: {Path(src).name}", task, self._open_output)

    def _run_metadata(self):
        src = self._require_pdf("Metadata"); out = self._require_out()
        if not src or not out: return
        dst = os.path.join(out, (self.meta_out.get().strip() or "updated") + ".pdf")
        fields = {k: v.get() for k, v in self.meta_fields.items()}
        def task():
            set_metadata(src, dst, fields)
            self._log(f"✔ Metadata saved: {Path(dst).name}", "ok")
        self._run_task(f"Update Metadata: {Path(src).name}", task, self._open_output)

    # ══════════════════════════════════════════════════════════════════════════
    # AI ACTIONS
    # ══════════════════════════════════════════════════════════════════════════

    def _on_enter(self, event=None):
        if event and event.state & 0x0001: return   # Shift+Enter = newline
        self._send_btn(); return "break"

    def _send_btn(self):
        # Get text, ignoring placeholder
        raw = self.chat_input.get("1.0","end-1c")
        if self._placeholder_active or not raw.strip():
            return
        text_to_send = raw.strip()
        if not self.ai.is_ready:
            self._ai_sys("⚠  AI not configured. Open ⚙ Settings and connect NVIDIA NIM or Gemini.")
            return
        self.chat_input.delete("1.0","end")
        self._set_placeholder()
        self._ai_user(text_to_send)
        mode = self.ai_mode.get()
        selected_file = self.ai_file_var.get()

        if mode == "chat":
            ctx = get_file_summary_context(self.files)
            self.ai.chat(text_to_send, context=ctx,
                          on_done=lambda r: self._ai_response(r, check_intent=True),
                          on_error=self._ai_error)
        elif mode == "qa":
            fp = self._resolve_ai_file(selected_file)
            if not fp: self._ai_sys("⚠  Select a file first."); return
            self.ai.ask_document(fp, extract_text(fp), text_to_send,
                                  on_done=self._ai_response, on_error=self._ai_error)
        elif mode == "summarise":
            fp = self._resolve_ai_file(selected_file)
            if not fp: self._ai_sys("⚠  Select a file first."); return
            self.ai.summarise_document(fp, extract_text(fp),
                                        on_done=self._ai_response, on_error=self._ai_error)
        elif mode == "plan":
            self.ai.plan_batch(self.files, text_to_send,
                                on_done=self._ai_response, on_error=self._ai_error)

    def _quick_prompt(self, prompt: str):
        """Insert a quick prompt and send it immediately."""
        # Remove placeholder first
        if self._placeholder_active:
            self.chat_input.delete("1.0", "end")
            self.chat_input.config(fg=self.TEXT)
            self._placeholder_active = False
        self.chat_input.delete("1.0","end")
        self.chat_input.insert("1.0", prompt)
        self._send_btn()

    def _analyse_image(self):
        images = [f for f in self.files if is_image(f)]
        if not images: messagebox.showinfo("No Images","Add image files first."); return
        if not self.ai.is_ready: self._ai_sys("⚠  Configure AI in Settings first."); return
        fp = images[0]
        self._ai_user(f"[Analyse image: {Path(fp).name}]")
        self.ai.analyse_image(fp, "Describe this image in detail. Include: content, objects, colours, style, text.",
                               on_done=self._ai_response, on_error=self._ai_error)

    def _ai_suggest_format(self):
        if not self.files: messagebox.showinfo("No Files","Add files first."); return
        if not self.ai.is_ready: self._ai_sys("⚠  Configure AI in Settings first."); return
        src = self.files[0]
        self._ai_user(f"What is the best output format for: {Path(src).name}?")
        self.ai.suggest_format(src, "Most useful for sharing, editing, archiving",
                                on_done=self._ai_response, on_error=self._ai_error)

    def _ai_upscale_recommend(self):
        images = [f for f in self.files if is_image(f)]
        if not images: self._ai_sys("⚠  No images in queue."); return
        if not self.ai.is_ready: self._ai_sys("⚠  Configure AI in Settings first."); return
        info = get_image_info(images[0])
        prompt = (f"I have a {info.get('width',0)}×{info.get('height',0)} "
                  f"{info.get('mode','')} image ({info.get('size_kb','')}) "
                  f"and want to upscale it. The available algorithms are: "
                  f"lanczos, bicubic, bilinear, nearest, edgeplus. "
                  f"Which algorithm and scale factor do you recommend and why?")
        self._ai_user("Recommend best upscale settings for my image")
        self.ai.chat(prompt, on_done=self._ai_response, on_error=self._ai_error)

    def _ai_analyse_metadata(self):
        src = self._require_pdf("Metadata")
        if not src: return
        if not self.ai.is_ready: self._ai_sys("⚠  Configure AI in Settings first."); return
        meta = get_metadata(src)
        meta_text = "\n".join(f"{k}: {v}" for k, v in meta.items())
        self._ai_user("Analyse the metadata of this PDF and suggest improvements")
        self.ai.chat(f"Analyse this PDF metadata and suggest improvements:\n\n{meta_text}",
                      on_done=self._ai_response, on_error=self._ai_error)

    def _ai_analyse_selected(self):
        sel = list(self.queue_lb.curselection())
        if not sel: messagebox.showinfo("Select","Select a file in the queue."); return
        if not self.ai.is_ready: self._ai_sys("⚠  Configure AI in Settings first."); return
        fp = self.files[sel[0]]
        if is_image(fp):
            self._ai_user(f"[Analyse image: {Path(fp).name}]")
            self.ai.analyse_image(fp, "Describe this image in detail.",
                                   on_done=self._ai_response, on_error=self._ai_error)
        elif is_text_extractable(fp):
            self._ai_user(f"Summarise: {Path(fp).name}")
            self.ai.summarise_document(fp, extract_text(fp),
                                        on_done=self._ai_response, on_error=self._ai_error)
        else:
            self._ai_sys(f"⚠  Cannot extract text from {Path(fp).suffix} files.")

    def _queue_select_for_ai(self, event=None):
        sel = list(self.queue_lb.curselection())
        if not sel: return
        fp = self.files[sel[0]]
        self.ai_context_file = fp
        self._update_ai_file_menu()
        self.ai_file_var.set(Path(fp).name)
        self._ai_sys(f"📎 Active AI file set to: {Path(fp).name}\n"
                     f"Switch to Doc Q&A or Summarise mode to ask about it.")

    def _insert_ai_bubble(self, text: str):
        """Render an AI response as a styled chat bubble."""
        # Remove any typing indicator first
        self._remove_typing()
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", "\n🤖  AI\n", "ai_lbl")
        self.chat_display.insert("end", text + "\n", "ai_bubble")
        self.chat_display.insert("end", "\n", "divider")
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")

    def _show_typing(self):
        """Show a 'AI is thinking…' indicator."""
        def _do():
            self.chat_display.config(state="normal")
            self.chat_display.insert("end", "⏳  AI is thinking…\n", "typing_msg")
            self.chat_display.mark_set("typing_start",
                self.chat_display.index("end-2l"))
            self.chat_display.see("end")
            self.chat_display.config(state="disabled")
        self.after(0, _do)

    def _remove_typing(self):
        """Remove the typing indicator line."""
        try:
            start = self.chat_display.index("typing_start")
            self.chat_display.delete(start, f"{start} lineend +1c")
        except Exception:
            pass

    def _ai_response(self, text: str, check_intent: bool = False):
        self.after(0, lambda: self._display_ai(text, check_intent))

    def _display_ai(self, text: str, check_intent: bool = False):
        # Strip raw JSON blocks from display — show only the human-readable part
        clean = _clean_ai_response(text)
        self.chat_display.config(state="normal")
        self._insert_ai_bubble(clean)
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")
        self._log(f"AI responded ({len(text)} chars)", "ai")
        if check_intent:
            intent = _extract_intent_json(text)
            if intent and intent.get("action") not in (None, "chat", "unknown"):
                self._latest_intent = intent
                self._latest_intent_raw = text
                self._update_command_center(intent, text)
                self._apply_intent(intent)

    def _match_intent_files(self, intent: dict) -> List[str]:
        hints = [str(x).strip().lower() for x in (intent.get("files") or []) if str(x).strip()]
        if not hints:
            return []
        matched = []
        for fp in self.files:
            name = Path(fp).name.lower()
            if any(h in name for h in hints):
                matched.append(fp)
        return matched

    def _update_command_center(self, intent: dict, raw_text: str = ""):
        if not hasattr(self, "cmd_json"):
            return
        import json
        self.cmd_json.delete("1.0", "end")
        self.cmd_json.insert("1.0", json.dumps(intent, indent=2))
        self.cmd_files_lb.delete(0, "end")
        matched = self._match_intent_files(intent)
        if matched:
            for fp in matched:
                self.cmd_files_lb.insert("end", f"{cat_icon(cat(fp))}  {Path(fp).name}")
        else:
            self.cmd_files_lb.insert("end", "(no direct file match from AI hints)")
        action = intent.get("action", "unknown")
        msg = intent.get("message", "")
        self.cmd_summary_var.set(f"Action: {action}" + (f"  |  {msg}" if msg else ""))
        self._refresh_command_dry_run()

    def _refresh_command_dry_run(self, _=None):
        if not hasattr(self, "cmd_dry_run_var"):
            return
        try:
            import json
            intent = json.loads(self.cmd_json.get("1.0", "end-1c").strip() or "{}")
        except Exception:
            self.cmd_dry_run_var.set("Dry-run: invalid JSON — fix or validate")
            return
        self.cmd_dry_run_var.set(self._build_command_dry_run_text(intent))

    def _build_command_dry_run_text(self, intent: dict) -> str:
        out = self.out_dir.get().strip()
        if not out:
            return "Dry-run: set output folder in sidebar"
        if not intent or not (intent.get("action") or "").strip():
            return "Dry-run: add JSON with an \"action\" (e.g. convert, merge, split)"
        action = (intent.get("action") or "").strip().lower()
        if action == "media":
            action = "video"
        if action == "convert":
            fmt = (intent.get("format") or "").strip().lower()
            if not fmt:
                return "Dry-run: convert — add \"format\" in JSON"
            pages_s = str(intent.get("pages") or "").strip()
            n = len(self.files)
            if not self.files:
                return "Dry-run: convert — no files in queue"
            try:
                dpi = int(self.conv_dpi.get())
            except Exception:
                dpi = 150
            ex = preview_convert_paths(self.files[0], fmt, out, pages_s, dpi)[0]
            return f"Dry-run: Convert ×{n} queued file(s) → {fmt.upper()} | first output: {ex}"
        if action == "merge":
            mtype = self.merge_type.get()
            name = (self.merge_name.get().strip() or "merged_output") + "." + mtype
            return f"Dry-run: Merge → {os.path.join(out, name)}  ({len(self.files)} file(s) in queue)"
        if action == "split":
            stype = self.split_type.get()
            prefix = self.split_prefix.get().strip() or "split"
            if stype == "pptx":
                pptxs = [f for f in self.files if cat(f) == "pptx"]
                if not pptxs:
                    return "Dry-run: split — add a PPTX to the queue"
                return f"Dry-run: Split PPTX → {os.path.join(out, prefix + '_001.pptx')} (one file per slide)"
            pdfs = [f for f in self.files if cat(f) == "pdf"]
            if not pdfs:
                return "Dry-run: split — add a PDF to the queue"
            stem = Path(pdfs[0]).stem
            mode = self.split_mode.get()
            if mode == "each":
                return f"Dry-run: Split PDF (each page) → {os.path.join(out, stem + '_p001.pdf')} …"
            if mode == "range":
                try:
                    s, e = int(self.range_start.get()), int(self.range_end.get())
                except Exception:
                    return "Dry-run: split PDF (range) — set valid page range in Split tab"
                return f"Dry-run: Split PDF (range) → {os.path.join(out, stem + f'_p{s}-{e}.pdf')}"
            return f"Dry-run: Split PDF (custom groups) → multiple files like «{stem}_g01_….pdf»"
        if action == "compress":
            pdfs = [f for f in self.files if cat(f) == "pdf"]
            if not pdfs:
                return "Dry-run: compress — add a PDF"
            dst = os.path.join(out, (self.compress_out.get().strip() or "compressed") + ".pdf")
            return f"Dry-run: Compress PDF → {dst}"
        if action == "protect":
            pdfs = [f for f in self.files if cat(f) == "pdf"]
            if not pdfs:
                return "Dry-run: protect — add a PDF"
            dst = os.path.join(out, (self.protect_out.get().strip() or "protected") + ".pdf")
            mode = self.protect_mode.get()
            return f"Dry-run: {'Encrypt' if mode == 'encrypt' else 'Decrypt'} PDF → {dst}"
        if action == "organise":
            pdfs = [f for f in self.files if cat(f) == "pdf"]
            if not pdfs:
                return "Dry-run: organise — add a PDF"
            dst = os.path.join(out, (self.org_out_name.get().strip() or "organised") + ".pdf")
            return f"Dry-run: Organise PDF ({self.org_op.get()}) → {dst}"
        if action == "stamp":
            pdfs = [f for f in self.files if cat(f) == "pdf"]
            if not pdfs:
                return "Dry-run: stamp — add a PDF"
            dst = os.path.join(out, (self.stamp_out_name.get().strip() or "stamped") + ".pdf")
            return f"Dry-run: Stamp PDF → {dst}"
        if action == "metadata":
            pdfs = [f for f in self.files if cat(f) == "pdf"]
            if not pdfs:
                return "Dry-run: metadata — add a PDF"
            dst = os.path.join(out, (self.meta_out.get().strip() or "updated") + ".pdf")
            return f"Dry-run: Update metadata → {dst}"
        if action == "video":
            op = self.video_op.get()
            if op == "merge":
                av = [f for f in self.files if cat(f) in ("video", "audio")]
                ext = self.video_merge_fmt.get().strip() or "mp4"
                name = (self.video_out_name.get().strip() or "output") + "." + ext
                return f"Dry-run: Media merge → {os.path.join(out, name)}  ({len(av)} media file(s))"
            av = [f for f in self.files if cat(f) in ("video", "audio")]
            if not av:
                return "Dry-run: media split — add video/audio"
            prefix = self.video_prefix.get().strip() or "segment"
            fmt = self.video_fmt.get().strip().lstrip(".") or Path(av[0]).suffix.lstrip(".")
            return f"Dry-run: Media split → under {out}/  (names like «{prefix}_seg*_….{fmt}»)"
        if action == "upscale":
            images = [f for f in self.files if cat(f) == "image"]
            if not images:
                return "Dry-run: upscale — add image(s)"
            src = images[0]
            suf = self.upscale_suffix.get().strip() or "_upscaled"
            dst = os.path.join(out, f"{Path(src).stem}{suf}{Path(src).suffix}")
            return f"Dry-run: Upscale → {dst}  ({len(images)} image(s))"
        if action in ("summarise", "qa", "analyse", "chat", "unknown"):
            return f"Dry-run: {action} — no batch file output from this button (UI / AI mode only)"
        return f"Dry-run: action «{action}» — review JSON or use a supported tool action"

    def _sync_command_from_latest_intent(self):
        if not self._latest_intent:
            messagebox.showinfo("No Plan", "No parsed AI command found yet.")
            return
        self._update_command_center(self._latest_intent, self._latest_intent_raw)
        self._status("Command Center synced from latest AI plan")

    def _validate_command_json(self):
        try:
            import json
            json.loads(self.cmd_json.get("1.0", "end-1c").strip() or "{}")
            messagebox.showinfo("Valid JSON", "Intent JSON is valid.")
            self._refresh_command_dry_run()
        except Exception as e:
            messagebox.showerror("Invalid JSON", str(e))

    def _run_command_plan(self):
        if not self.cmd_confirm_var.get():
            messagebox.showwarning("Confirmation Required", "Please confirm before execution.")
            return
        try:
            import json
            intent = json.loads(self.cmd_json.get("1.0", "end-1c").strip())
        except Exception as e:
            messagebox.showerror("Invalid JSON", f"Cannot execute invalid JSON:\n{e}")
            return
        self._apply_intent(intent, run_now=True)

    def _apply_intent(self, intent: dict, run_now: bool = False):
        action = (intent.get("action", "") or "").strip().lower()
        fmt = (intent.get("format") or "").strip().lower()
        msg = intent.get("message","")
        pages = intent.get("pages")
        params = intent.get("params") or {}

        if action == "convert" and fmt:
            self._select_fmt(fmt)
            self._switch_tab("convert")
            if pages:
                self.conv_pages.set(str(pages))
            self._ai_sys(f"✅ Prepared Convert tab → {fmt.upper()}" + (f" (pages: {pages})" if pages else ""))
            if run_now or params.get("run_now") or params.get("auto_run"):
                self._run_convert()
        elif action in ("split","merge","compress","protect","organise","stamp","metadata","video","media","upscale"):
            if action == "media":
                action = "video"
            self._switch_tab(action)
            self._ai_sys(f"✅ Switched to {action.title()} tab for you")
            if run_now:
                runner = {
                    "split": self._run_split,
                    "merge": self._run_merge,
                    "compress": self._run_compress,
                    "protect": self._run_protect,
                    "organise": self._run_organise,
                    "stamp": self._run_stamp,
                    "metadata": self._run_metadata,
                    "video": self._run_video,
                    "upscale": self._run_upscale,
                }.get(action)
                if runner:
                    runner()
        elif action == "summarise":
            self._set_ai_mode("summarise")
            self._ai_sys("✅ Switched AI mode to Summarise.")
        elif action in ("analyse", "qa"):
            self._set_ai_mode("qa")
            self._ai_sys("✅ Switched AI mode to Doc Q&A.")
        if msg:
            self._ai_sys("🧭 " + msg)

    def _ai_error(self, msg: str):
        def _do():
            self._remove_typing()
            self.chat_display.config(state="normal")
            self.chat_display.insert("end", f"\n⚠  {msg}\n\n", "err_msg")
            self.chat_display.see("end")
            self.chat_display.config(state="disabled")
        self.after(0, _do)

    def _ai_user(self, text: str):
        """Render a user message as a chat bubble and show typing indicator."""
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", "\n👤  You\n", "you_lbl")
        self.chat_display.insert("end", text + "\n", "you_bubble")
        self.chat_display.insert("end", "\n", "divider")
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")
        self._show_typing()

    def _ai_sys(self, text: str):
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", text + "\n", "sys_msg")
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")

    def _clear_chat(self):
        self.chat_display.config(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.config(state="disabled")
        self.ai.reset_chat()
        self._ai_sys("✨ Chat cleared. Fresh start — ask me anything!")

    def _set_ai_mode(self, val: str, init=False):
        self.ai_mode.set(val)
        for v, b in self._mode_btns.items():
            if v == val: b.config(bg=self.TAB_ACTIVE, fg="#ffffff")
            else:        b.config(bg=self.TAB_INACTIVE, fg=self.TAB_INACTIVE_TEXT)
        if not init:
            needs_file = val in ("qa", "summarise")
            if needs_file:
                self.ai_file_frame.pack(fill="x")
            else:
                self.ai_file_frame.pack_forget()
            hints = {
                "chat":      "💬 Chat mode — just talk naturally!",
                "qa":        "📄 Doc Q&A — select a file then ask questions about it",
                "summarise": "📋 Summarise — select a file and I'll summarise it",
                "plan":      "🗂 Batch Plan — describe what you want to achieve",
            }
            self._ai_sys(hints.get(val, ""))

    # ══════════════════════════════════════════════════════════════════════════
    # PLACEHOLDER  — uses a flag to avoid content/placeholder confusion
    # ══════════════════════════════════════════════════════════════════════════

    def _show_theme_menu(self):
        """Show theme selection popup menu"""
        # Create theme popup
        popup = tk.Toplevel(self)
        popup.title("Theme Selection")
        popup.geometry("280x200")
        popup.configure(bg=self.CARD)
        popup.transient(self)
        popup.grab_set()
        
        # Center the popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (280 // 2)
        y = (popup.winfo_screenheight() // 2) - (200 // 2)
        popup.geometry(f"280x200+{x}+{y}")
        
        # Header
        tk.Label(popup, text="🎨 Select Theme", 
                font=F["head"], 
                bg=self.CARD, fg=self.ACCENT).pack(pady=12)
        
        # Theme options
        theme_info = {
            "light_theme": ("☁️ Light Theme", "Light and modern"),
            "dark": ("🌙 Dark", "Dark professional"),
            "light": ("☀️ Light", "Bright and clean")
        }
        
        for theme_name, (display_name, description) in theme_info.items():
            btn_frame = tk.Frame(popup, bg=self.CARD)
            btn_frame.pack(fill="x", padx=20, pady=4)
            
            # Theme button
            is_current = theme_name == self.current_theme
            btn = tk.Button(btn_frame, 
                          text=f"{display_name} {'✓' if is_current else ''}",
                          font=F["body"],
                          bg=self.ACCENT if is_current else self.INPUT_BG,
                          fg="#ffffff" if is_current else self.TEXT,
                          relief="flat", cursor="hand2",
                          padx=12, pady=8,
                          command=lambda t=theme_name, p=popup: self._switch_theme(t, p))
            btn.pack(fill="x")
            
            # Description label
            desc_label = tk.Label(btn_frame, text=description,
                                font=F["small"],
                                bg=self.CARD, fg=self.TEXT2)
            desc_label.pack(anchor="w", padx=(4, 0))
            
            # Add hover effects
            def on_enter(e, b=btn, current=is_current):
                if not current:
                    b.config(bg=self.HOVER)
            def on_leave(e, b=btn, current=is_current):
                if not current:
                    b.config(bg=self.INPUT_BG)
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        
        # Close button
        tk.Button(popup, text="Close",
                 font=F["btn_small"],
                 bg=self.BORDER2, fg=self.TEXT,
                 relief="flat", cursor="hand2",
                 padx=12, pady=6,
                 command=popup.destroy).pack(pady=12)
    
    def _switch_theme(self, theme_name: str, popup):
        """Switch to a new theme"""
        if theme_name == self.current_theme:
            popup.destroy()
            return
        
        # Update theme
        self.current_theme = theme_name
        self.C = get_theme(theme_name)
        
        # Save to config
        self.cfg["theme"] = theme_name
        save_config(self.cfg)
        
        # Update UI with new theme
        self._apply_theme_to_ui()
        
        # Update status
        theme_display = theme_name.replace("_", " ").title()
        self._status(f"Theme switched to {theme_display}")
        
        # Close popup
        popup.destroy()
    
    def _apply_theme_to_ui(self):
        """Apply current theme to all UI elements"""
        try:
            # Update color shortcuts first
            self._update_color_shortcuts()
            
            # Update main window background
            self.configure(bg=self.BG)
            
            # Update all child widgets recursively
            self._update_widget_theme(self)
            
            # Update all open dialogs
            for widget in self.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    self._update_widget_theme(widget)
            
            # Update tab buttons
            self._switch_tab(self.active_tab if hasattr(self, 'active_tab') and self.active_tab else "aichat")
            
        except Exception as e:
            print(f"Error applying theme: {e}")
    
    def _update_widget_theme(self, widget):
        """Recursively update theme for a widget and its children"""
        try:
            widget_class = widget.winfo_class()
            
            # Update based on widget type
            if widget_class in ["Frame", "Toplevel"]:
                widget.configure(bg=self.C["bg"])
            elif widget_class in ["Label"]:
                # Keep existing text color for specific labels that need special colors
                current_fg = widget.cget("fg")
                if current_fg in ["#ffffff", self.SUCCESS, WARNING, self.ERROR]:
                    # Keep special colors
                    pass
                else:
                    widget.configure(fg=self.C["text"])
                widget.configure(bg=self.C["bg"])
            elif widget_class in ["Button"]:
                # Update button based on its current role
                current_bg = widget.cget("bg")
                if current_bg == self.ACCENT or "accent" in str(current_bg):
                    widget.configure(bg=self.C["accent"])
                else:
                    widget.configure(bg=self.C["sidebar"])
                widget.configure(fg=self.C["text"])
            elif widget_class in ["Entry"]:
                widget.configure(bg=self.C["input_bg"], fg=self.C["text"])
            elif widget_class in ["Text", "Listbox"]:
                widget.configure(bg=self.C["log_bg"], fg=self.C["text"])
            
            # Recursively update children
            for child in widget.winfo_children():
                self._update_widget_theme(child)
                
        except Exception:
            pass  # Ignore errors for widgets that don't support these options

    def _show_quick_actions(self):
        """Show quick action prompts in a popup"""
        quick_actions = [
            "Summarize all files",
            "Convert all PDFs to DOCX",
            "Extract text from images",
            "Merge all files",
            "Analyze document structure",
            "Create workflow plan"
        ]
        
        # Create a simple popup with quick actions
        popup = tk.Toplevel(self)
        popup.title("Quick Actions")
        popup.geometry("300x400")
        popup.configure(bg=self.CARD)
        popup.transient(self)
        popup.grab_set()
        
        # Header
        tk.Label(popup, text="⚡ Quick Actions", 
                font=F["head"], 
                bg=self.CARD, fg=self.ACCENT).pack(pady=12)
        
        # Actions list
        for action in quick_actions:
            btn = tk.Button(popup, text=action,
                          font=F["body"],
                          bg=self.INPUT_BG, fg=self.TEXT,
                          relief="flat", cursor="hand2",
                          padx=12, pady=8,
                          command=lambda a=action: self._quick_action_selected(a, popup))
            btn.pack(fill="x", padx=20, pady=4)
            
            # Add hover effects
            def on_enter(e, b=btn):
                b.config(bg=self.HOVER)
            def on_leave(e, b=btn):
                b.config(bg=self.INPUT_BG)
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        
        # Close button
        tk.Button(popup, text="Close",
                 font=F["btn_small"],
                 bg=self.BORDER2, fg=self.TEXT,
                 relief="flat", cursor="hand2",
                 padx=12, pady=6,
                 command=popup.destroy).pack(pady=12)
    
    def _quick_action_selected(self, action, popup):
        """Handle quick action selection"""
        popup.destroy()
        self._quick_prompt(action)

    def _set_placeholder(self):
        """Show placeholder hint text in the input box."""
        self.chat_input.delete("1.0", "end")
        self.chat_input.config(fg=self.TEXT2)  # Use proper light theme text color
        self.chat_input.insert("1.0", self._placeholder)
        self._placeholder_active = True

    def _clear_placeholder(self, _=None):
        """Remove placeholder when user focuses the input."""
        if self._placeholder_active:
            self.chat_input.delete("1.0", "end")
            self.chat_input.config(fg=self.TEXT)  # Use proper light theme text color
            self._placeholder_active = False

    def _restore_placeholder(self, _=None):
        """Restore placeholder if box is empty when user leaves."""
        if not self._placeholder_active:
            content = self.chat_input.get("1.0", "end-1c").strip()
            if not content:
                self._set_placeholder()

    # ══════════════════════════════════════════════════════════════════════════
    # SETTINGS DIALOG
    # ══════════════════════════════════════════════════════════════════════════

    def _open_settings(self):
        win = tk.Toplevel(self)
        win.title("Settings — File Workshop AI")
        win.configure(bg=self.BG)
        win.geometry("800x700")
        win.resizable(True, True)
        win.transient(self); win.grab_set()
        
        # Make window responsive
        win.grid_rowconfigure(0, weight=1)
        win.grid_columnconfigure(0, weight=1)

        # Main container with scroll
        main_canvas = tk.Canvas(win, bg=self.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas, bg=self.BG)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        hdr = tk.Frame(scrollable_frame, bg=self.SIDEBAR, pady=14)
        hdr.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(hdr, text="⚙  SETTINGS", font=("Segoe UI", 16, "bold"),
                 bg=self.SIDEBAR, fg=self.ACCENT).pack(side="left", padx=20)

        c2 = tk.Frame(scrollable_frame, bg=self.PANEL, padx=24, pady=18)
        c2.pack(fill="x", padx=20, pady=(16, 20))
        
        tk.Label(c2, text="🤖  AI PROVIDER & KEY",
                 font=("Segoe UI", 12, "bold"), bg=self.PANEL, fg=self.ACCENT3).pack(anchor="w", pady=(0,12))

        guide_box = tk.Frame(c2, bg=self.CARD2, padx=14, pady=10)
        guide_box.pack(fill="x", pady=(0,14))
        tk.Label(guide_box, text="Select your AI provider and enter the API key:",
                 font=("Segoe UI", 10, "bold"), bg=self.CARD2, fg=self.TEXT).pack(anchor="w")
        for step in ["1.  Choose provider below",
                    "2.  Enter your API key",
                    "3.  Select a model",
                    "4.  Click Save & Apply"]:
            tk.Label(guide_box, text=step, font=("Consolas", 9),
                     bg=self.CARD2, fg=self.TEXT2).pack(anchor="w")

        provider_var = tk.StringVar(value=self.cfg.get("ai_provider", "nvidia"))
        pr = tk.Frame(c2, bg=self.PANEL); pr.pack(fill="x", pady=(0, 15))
        tk.Label(pr, text="Provider:", font=("Segoe UI", 11, "bold"),
                 bg=self.PANEL, fg=self.TEXT).pack(side="left")
        for v, label in [("nvidia", "NVIDIA NIM"), ("gemini", "Google Gemini")]:
            tk.Radiobutton(pr, text=label, variable=provider_var, value=v,
                           font=("Segoe UI", 11), bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT3, activebackground=self.PANEL,
                           cursor="hand2").pack(side="left", padx=(15, 10))

        # Single API Key section that changes based on provider
        tk.Label(c2, text="API Key:", font=("Segoe UI", 11, "bold"),
                 bg=self.PANEL, fg=self.TEXT).pack(anchor="w", pady=(0,4))
        
        api_key_frame = tk.Frame(c2, bg=self.PANEL); api_key_frame.pack(fill="x", pady=(0,6))
        
        nvidia_key_var = tk.StringVar(value=self.cfg.get("nvidia_api_key",""))
        gemini_key_var = tk.StringVar(value=self.cfg.get("gemini_api_key",""))
        
        api_key_entry = tk.Entry(api_key_frame, 
                              font=("Consolas", 11),
                              bg=self.CARD2, fg=self.TEXT, insertbackground=self.TEXT,
                              show="•", relief="flat", bd=0, width=60)
        api_key_entry.pack(side="left", ipady=8, padx=(0,8))
        
        def update_api_key_field():
            if provider_var.get() == "nvidia":
                api_key_entry.config(textvariable=nvidia_key_var)
            else:
                api_key_entry.config(textvariable=gemini_key_var)
        
        update_api_key_field()
        provider_var.trace("w", lambda *args: update_api_key_field())
        
        show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(c2, text="Show API key", variable=show_var,
                        command=lambda: api_key_entry.config(show="" if show_var.get() else "•"),
                        font=("Segoe UI", 10), bg=self.PANEL, fg=self.TEXT2,
                        selectcolor=self.ACCENT, activebackground=self.PANEL,
                        cursor="hand2").pack(anchor="w", pady=(5,0))

        # Model selection - dynamic based on provider
        tk.Label(c2, text="Model:", font=("Segoe UI", 11, "bold"),
                 bg=self.PANEL, fg=self.TEXT).pack(anchor="w", pady=(15,4))
        
        model_frame = tk.Frame(c2, bg=self.PANEL); model_frame.pack(fill="x", pady=(0,4))
        
        nvidia_model_var = tk.StringVar(value=self.cfg.get("nvidia_model","meta/llama-3.1-70b-instruct"))
        gemini_model_var = tk.StringVar(value=self.cfg.get("gemini_model","gemini-1.5-flash"))
        
        # Model radio buttons
        nvidia_models_frame = tk.Frame(model_frame, bg=self.PANEL)
        gemini_models_frame = tk.Frame(model_frame, bg=self.PANEL)
        
        for m in NIM_MODELS:
            tk.Radiobutton(nvidia_models_frame, text=m, variable=nvidia_model_var, value=m,
                           font=("Consolas", 10), bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT3, activebackground=self.PANEL,
                           cursor="hand2").pack(anchor="w")
        
        for m in GEMINI_MODELS:
            tk.Radiobutton(gemini_models_frame, text=m, variable=gemini_model_var, value=m,
                           font=("Consolas", 10), bg=self.PANEL, fg=self.TEXT,
                           selectcolor=self.ACCENT3, activebackground=self.PANEL,
                           cursor="hand2").pack(anchor="w")
        
        def update_model_selection():
            if provider_var.get() == "nvidia":
                nvidia_models_frame.pack(fill="x")
                gemini_models_frame.pack_forget()
            else:
                gemini_models_frame.pack(fill="x")
                nvidia_models_frame.pack_forget()
        
        update_model_selection()
        provider_var.trace("w", lambda *args: update_model_selection())

        # Optional Hugging Face token
        tk.Label(c2, text="Hugging Face Token (optional):", font=("Segoe UI", 11, "bold"),
                 bg=self.PANEL, fg=self.TEXT).pack(anchor="w", pady=(20,4))
        hf_var = tk.StringVar(value=self.cfg.get("huggingface_token",""))
        hf_entry = tk.Entry(c2, textvariable=hf_var,
                            font=("Consolas", 11),
                            bg=self.CARD2, fg=self.TEXT, insertbackground=self.TEXT,
                            show="•", relief="flat", bd=0, width=60)
        hf_entry.pack(anchor="w", ipady=8, pady=(0, 4))
        tk.Label(c2, text="Stored for future model integrations in this app.",
                 font=("Segoe UI", 9, "italic"), bg=self.PANEL, fg=self.TEXT2).pack(anchor="w")

        # Status label
        status_lbl = tk.Label(scrollable_frame, text="", font=("Segoe UI", 11), 
                             bg=self.BG, fg=self.SUCCESS)
        status_lbl.pack(anchor="w", padx=20, pady=(12,0))

        def save():
            self.cfg["ai_provider"] = provider_var.get()
            self.cfg["nvidia_api_key"] = nvidia_key_var.get().strip()
            self.cfg["nvidia_model"] = nvidia_model_var.get()
            self.cfg["gemini_api_key"] = gemini_key_var.get().strip()
            self.cfg["gemini_model"] = gemini_model_var.get()
            self.cfg["huggingface_token"] = hf_var.get().strip()
            self.cfg["output_dir"] = self.out_dir.get()
            save_config(self.cfg)

            self._reload_config_and_ai()
            if self.ai.is_ready:
                provider = self.cfg.get("ai_provider", "nvidia").title()
                model = self.cfg.get("nvidia_model") if self.cfg.get("ai_provider") == "nvidia" else self.cfg.get("gemini_model")
                status_lbl.config(text="✔  Saved! AI is now active.", fg=self.SUCCESS)
                self._ai_sys(f"✔ AI configured: {provider} / {model}")
                win.after(1500, win.destroy)
            else:
                status_lbl.config(text="⚠  Saved, but AI is not active. Add a valid key.", fg=self.WARN)

        def test():
            provider = provider_var.get()
            if provider == "nvidia":
                key = nvidia_key_var.get().strip()
                model = nvidia_model_var.get()
                tmp = NIMClient(key, model)
            else:
                key = gemini_key_var.get().strip()
                model = gemini_model_var.get()
                tmp = GeminiClient(key, model)

            if not key:
                status_lbl.config(text="⚠  Paste your API key first", fg=self.WARN)
                return
            status_lbl.config(text="⏳  Testing …", fg=self.TEXT2)
            if tmp.is_ready:
                tmp.chat("Reply with exactly: Connection OK",
                          on_done=lambda r: status_lbl.config(text=f"✔  {r.strip()[:80]}", fg=self.SUCCESS),
                          on_error=lambda e: status_lbl.config(text=f"✖  {e}", fg=self.ERROR))
            else:
                status_lbl.config(text=f"✖  {tmp.error}", fg=self.ERROR)

        # Buttons
        bf = tk.Frame(scrollable_frame, bg=self.BG); bf.pack(fill="x", padx=20, pady=(20,30))
        tk.Button(bf, text="💾  Save & Apply", command=save,
                  font=("Segoe UI", 12, "bold"), bg=self.ACCENT, fg="#fff",
                  activebackground=self.BORDER2, relief="flat",
                  cursor="hand2", padx=20, pady=10, bd=0).pack(side="left", padx=(0,15))
        tk.Button(bf, text="🔌  Test Connection", command=test,
                  font=("Segoe UI", 11, "bold"), bg=self.ACCENT3, fg="#fff",
                  activebackground=self.BORDER2, relief="flat",
                  cursor="hand2", padx=15, pady=10, bd=0).pack(side="left", padx=(0,15))
        tk.Button(bf, text="Cancel", command=win.destroy,
                  font=("Segoe UI", 11), bg=self.BORDER2, fg=self.TEXT,
                  activebackground=self.BORDER, relief="flat",
                  cursor="hand2", padx=15, pady=10, bd=0).pack(side="left")

        # Links
        lf2 = tk.Frame(scrollable_frame, bg=self.BG); lf2.pack(anchor="w", padx=20, pady=(0,20))
        tk.Label(lf2, text="Get keys: ", font=("Segoe UI", 10), bg=self.BG, fg=self.TEXT2).pack(side="left")
        link = tk.Label(lf2, text="NVIDIA NIM",
                         font=("Segoe UI", 10, "underline"), bg=self.BG, fg=self.INFO, cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: self._open_url("https://build.nvidia.com/"))
        tk.Label(lf2, text="  |  ", font=("Segoe UI", 10), bg=self.BG, fg=self.TEXT2).pack(side="left")
        link2 = tk.Label(lf2, text="Gemini", font=("Segoe UI", 10, "underline"),
                         bg=self.BG, fg=self.INFO, cursor="hand2")
        link2.pack(side="left")
        link2.bind("<Button-1>", lambda e: self._open_url("https://aistudio.google.com/app/apikey"))

    def _open_url(self, url):
        import webbrowser; webbrowser.open(url)

    # ══════════════════════════════════════════════════════════════════════════
    # FILE QUEUE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def _add_files(self):
        # Get last file location from config
        initial_dir = self.cfg.get("last_file_dir", "")
        if not initial_dir and self.files:
            # If no saved location but we have files, use the directory of the last file
            initial_dir = str(Path(self.files[-1]).parent)
        
        all_exts = ("*.pdf *.docx *.xlsx *.xls *.xlsm *.pptx *.ppt *.csv *.tsv "
                    "*.txt *.html *.htm "
                    "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.ico *.svg "
                    "*.mp4 *.avi *.mov *.mkv *.webm *.mp3 *.wav *.ogg *.flac *.aac *.m4a")
        
        # Enhanced file dialog with better layout
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(
            title="📁 Select files for AI FileMat",
            initialdir=initial_dir,
            filetypes=[
                ("📄 All supported files", all_exts),
                ("📋 PDF Documents", "*.pdf"), 
                ("📊 Excel Spreadsheets", "*.xlsx *.xls *.xlsm *.ods"),
                ("📈 PowerPoint Presentations", "*.pptx *.ppt"), 
                ("📝 CSV/TSV Data", "*.csv *.tsv"),
                ("📄 Word Documents", "*.docx"),
                ("🖼️ Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.ico *.svg"),
                ("🎵 Audio Files", "*.mp3 *.wav *.ogg *.flac *.aac *.m4a"),
                ("🎬 Video Files", "*.mp4 *.avi *.mov *.mkv *.webm"),
                ("📁 All files", "*.*")
            ])
        
        if paths:
            # Save the last used directory
            last_dir = str(Path(paths[0]).parent)
            self.cfg["last_file_dir"] = last_dir
            save_config(self.cfg)
            
            existing = set(self.files)
            new_items = [p for p in paths if p not in existing]
            if new_items:
                self.files.extend(new_items)
                rows = [f"  {cat_icon(cat(p))}  {Path(p).name}  [{cat(p)}]" for p in new_items]
                self.queue_lb.insert("end", *rows)
                self._status(f"✅ Added {len(new_items)} file{'s' if len(new_items) > 1 else ''}")
            else:
                self._status("ℹ️ No new files to add (duplicates skipped)")
        
        self._update_after_files()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Add all files from folder")
        if not folder: return
        exts = IMAGE_EXTS|AUDIO_EXTS|VIDEO_EXTS|EXCEL_EXTS|PPTX_EXTS|CSV_EXTS|{".pdf",".docx",".txt",".html",".htm"}
        existing = set(self.files)
        added_paths = []
        for path in sorted(Path(folder).iterdir()):
            p = str(path)
            if path.suffix.lower() in exts and p not in existing:
                added_paths.append(p)
        if added_paths:
            self.files.extend(added_paths)
            rows = [f"  {cat_icon(cat(p))}  {Path(p).name}  [{cat(p)}]" for p in added_paths]
            self.queue_lb.insert("end", *rows)
        self._log(f"Added {len(added_paths)} file(s) from folder.")
        self._update_after_files()

    def _update_after_files(self):
        n = len(self.files)
        self._status(f"{n} file(s) in queue")
        if not self.out_dir.get() and self.files:
            self.out_dir.set(str(Path(self.files[0]).parent/"workshop_output"))
        by_type = {}
        for fp in self.files:
            c = cat(fp)
            by_type.setdefault(c, []).append(fp)

        pdfs = by_type.get("pdf", [])
        if pdfs and HAS_PYPDF:
            try:
                pc = pdf_page_count(pdfs[0]); self.page_count = pc; self.active_pdf = pdfs[0]
                name = Path(pdfs[0]).name
                self.file_badge.config(text=f"📄 {name}\n   {pc} pages", fg=self.SUCCESS)
                self.split_info_lbl.config(text=f"Active PDF: {name} · {pc} pages", fg=self.SUCCESS)
                self.org_lbl_var.set(f"Active PDF: {name}  ·  {pc} pages")
            except: pass
        pptxs = by_type.get("pptx", [])
        if pptxs and HAS_PPTX:
            try:
                sc = pptx_slide_count(pptxs[0])
                self.split_info_lbl.config(
                    text=f"Active PPTX: {Path(pptxs[0]).name} · {sc} slides", fg=self.SUCCESS)
            except: pass
        images = by_type.get("image", [])
        if images:
            self.upscale_info_lbl.config(
                text=f"{len(images)} image(s) ready to upscale. Click 'Preview Info' to inspect.",
                fg=self.SUCCESS)
        av = by_type.get("video", []) + by_type.get("audio", [])
        if av:
            self.video_info_lbl.config(
                text=f"{len(av)} video/audio file(s) loaded. First: {Path(av[0]).name}",
                fg=self.SUCCESS)
            self.video_duration_lbl.config(text="")
        if n > 0:
            self.file_badge.config(text=f"{n} file(s) loaded", fg=self.TEXT2)
        # Update queue selection label
        if hasattr(self, "queue_count_lbl"):
            self.queue_count_lbl.config(text=f"{n} file(s)" if n else "")
        self._update_ai_file_menu()
        self._refresh_merge_preview()
        self._refresh_home_files()

    def _update_ai_file_menu(self):
        if not hasattr(self, "ai_file_var"): return
        menu = self.ai_file_menu["menu"]; menu.delete(0,"end")
        for fp in self.files:
            name = Path(fp).name
            menu.add_command(label=name, command=lambda n=name, p=fp: (
                self.ai_file_var.set(n), setattr(self,"ai_context_file",p)))
        if not self.files:
            menu.add_command(label="(none)", command=lambda: None)

    def _resolve_ai_file(self, selected_name: str) -> Optional[str]:
        if self.ai_context_file and Path(self.ai_context_file).name == selected_name:
            return self.ai_context_file
        for fp in self.files:
            if Path(fp).name == selected_name: return fp
        return self.files[0] if self.files else None

    def _refresh_merge_preview(self):
        if not hasattr(self,"merge_preview"): return
        self.merge_preview.config(state="normal")
        self.merge_preview.delete("1.0","end")
        if not self.files:
            self.merge_preview.insert("end","  No files in queue.")
        else:
            show_n = min(140, len(self.files))
            for i,fp in enumerate(self.files[:show_n],1):
                self.merge_preview.insert("end",f"  {i:2d}.  {cat_icon(cat(fp))}  {Path(fp).name}\n")
            if len(self.files) > show_n:
                self.merge_preview.insert("end", f"\n  ... and {len(self.files)-show_n} more")
        self.merge_preview.config(state="disabled")

    def _move_up(self):
        sel = list(self.queue_lb.curselection())
        if not sel or sel[0]==0: return
        for i in sel:
            self.files[i-1],self.files[i]=self.files[i],self.files[i-1]
            a=self.queue_lb.get(i-1); b=self.queue_lb.get(i)
            self.queue_lb.delete(i-1,i); self.queue_lb.insert(i-1,b); self.queue_lb.insert(i,a)
        self.queue_lb.selection_clear(0,"end")
        for i in sel: self.queue_lb.selection_set(i-1)
        self._refresh_merge_preview()

    def _move_down(self):
        sel = list(self.queue_lb.curselection())
        if not sel or sel[-1]==len(self.files)-1: return
        for i in reversed(sel):
            self.files[i],self.files[i+1]=self.files[i+1],self.files[i]
            a=self.queue_lb.get(i); b=self.queue_lb.get(i+1)
            self.queue_lb.delete(i,i+1); self.queue_lb.insert(i,b); self.queue_lb.insert(i+1,a)
        self.queue_lb.selection_clear(0,"end")
        for i in sel: self.queue_lb.selection_set(i+1)
        self._refresh_merge_preview()

    def _remove_selected(self):
        sel = list(self.queue_lb.curselection())
        if not sel:
            self._status("Nothing selected — use Ctrl+click to select files first")
            return
        for i in reversed(sel):
            self.files.pop(i)
            self.queue_lb.delete(i)
        n = len(sel)
        self._log(f"Removed {n} file(s) from queue.", "info")
        self._update_after_files()
        self._on_queue_select()  # reset selection label

    def _on_queue_select(self, _=None):
        """Update the selection count label whenever selection changes."""
        sel = self.queue_lb.curselection()
        total = len(self.files)
        if sel:
            self.queue_sel_lbl.config(
                text=f"{len(sel)} selected — click ✖ Remove Selected to remove them",
                fg=self.WARN)
            self.queue_count_lbl.config(text=f"{len(sel)} / {total} selected")
            self.remove_sel_btn.config(bg=self.ACCENT2, fg="#ffffff")
        else:
            self.queue_sel_lbl.config(
                text="Tip: Ctrl+click to select multiple, then click ✖ Remove Selected",
                fg=self.TEXT2)
            self.queue_count_lbl.config(text=f"{total} file(s)" if total else "")
            self.remove_sel_btn.config(bg="#5a1a1a", fg="#ff9999")

    def _queue_right_click(self, event):
        """Show context menu on right-click in queue listbox."""
        # Select the item under cursor if nothing selected
        idx = self.queue_lb.nearest(event.y)
        if idx >= 0:
            cur_sel = self.queue_lb.curselection()
            if idx not in cur_sel:
                self.queue_lb.selection_clear(0, "end")
                self.queue_lb.selection_set(idx)
                self._on_queue_select()
        try:
            self._queue_ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._queue_ctx_menu.grab_release()

    def _select_all_queue(self):
        """Select all items in the queue listbox."""
        self.queue_lb.selection_set(0, "end")
        self._on_queue_select()

    def _clear_queue(self):
        self.files.clear(); self.queue_lb.delete(0,"end")
        self.page_count=0; self.active_pdf=""
        self.file_badge.config(text="No files loaded",fg=self.TEXT2)
        self._status("Queue cleared"); self._refresh_merge_preview()
        self._refresh_home_files()

    def _browse_output(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p: self.out_dir.set(p); self.cfg["output_dir"]=p; save_config(self.cfg)

    def _browse_stamp_pdf(self):
        p = filedialog.askopenfilename(title="Select watermark PDF",filetypes=[("PDF","*.pdf")])
        if p: self.stamp_wm_path.set(p)

    def _open_output(self):
        folder = self.out_dir.get()
        if not folder: return
        os.makedirs(folder, exist_ok=True)
        try:
            if sys.platform=="win32":    os.startfile(folder)
            elif sys.platform=="darwin": subprocess.run(["open",folder])
            else:                        subprocess.run(["xdg-open",folder])
        except Exception as e: self._log(f"Could not open folder: {e}","err")

    def _load_metadata(self):
        src = self._require_pdf("Metadata")
        if not src: return
        try:
            meta = get_metadata(src)
            self.meta_display.config(state="normal")
            self.meta_display.delete("1.0","end")
            for k,v in meta.items(): self.meta_display.insert("end",f"  {k:12s}: {v}\n")
            self.meta_display.config(state="disabled")
            mapping={"Title":"title","Author":"author","Subject":"subject","Creator":"creator"}
            for dk,fk in mapping.items():
                val=meta.get(dk,"")
                if val!="—" and fk in self.meta_fields: self.meta_fields[fk].set(val)
        except Exception as e: self._log(f"Metadata error: {e}","err")

    # ══════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ══════════════════════════════════════════════════════════════════════════

    def _make_ai_client(self):
        provider = (self.cfg.get("ai_provider", "nvidia") or "nvidia").lower()
        
        # Debug: Log API key loading
        if provider == "gemini":
            api_key = self.cfg.get("gemini_api_key", "")
            model = self.cfg.get("gemini_model", "gemini-1.5-flash")
            print(f"[DEBUG] Creating Gemini client - Key length: {len(api_key)}, Key starts with: {api_key[:10] if api_key else 'None'}...")
            return GeminiClient(api_key, model)
        else:
            api_key = self.cfg.get("nvidia_api_key", "")
            model = self.cfg.get("nvidia_model", "meta/llama-3.1-70b-instruct")
            print(f"[DEBUG] Creating NIM client - Key length: {len(api_key)}, Key starts with: {api_key[:10] if api_key else 'None'}...")
            return NIMClient(api_key, model)

    def _reload_config_and_ai(self):
        """Reload configuration from file and environment, then update AI client"""
        print("[DEBUG] Reloading configuration...")
        
        # Reload config (this will pick up env vars)
        from config import load_config
        old_cfg = self.cfg.copy()
        self.cfg = load_config()
        
        # Check if API keys changed
        provider = (self.cfg.get("ai_provider", "nvidia") or "nvidia").lower()
        if provider == "gemini":
            old_key = old_cfg.get("gemini_api_key", "")
            new_key = self.cfg.get("gemini_api_key", "")
            if old_key != new_key:
                print(f"[DEBUG] Gemini API key changed, updating client...")
                if hasattr(self.ai, 'reconfigure'):
                    self.ai.reconfigure(new_key, self.cfg.get("gemini_model", "gemini-1.5-flash"))
                else:
                    self.ai = self._make_ai_client()
        else:
            old_key = old_cfg.get("nvidia_api_key", "")
            new_key = self.cfg.get("nvidia_api_key", "")
            if old_key != new_key:
                print(f"[DEBUG] NVIDIA API key changed, updating client...")
                if hasattr(self.ai, 'reconfigure'):
                    self.ai.reconfigure(new_key, self.cfg.get("nvidia_model", "meta/llama-3.1-70b-instruct"))
                else:
                    self.ai = self._make_ai_client()
        
        self._update_ai_status()

    def _apply_zoom(self, scale: float):
        """Apply zoom uniformly across all windows and dialogs"""
        scale = min(2.0, max(0.5, float(scale)))
        old_scale = self.ui_scale
        self.ui_scale = scale
        
        # Update global font system with scaled fonts
        self._update_font_system(scale)
        
        # Apply scaling to all existing widgets
        self._scale_all_windows_absolute(scale)
        
        # Update zoom indicator
        if hasattr(self, 'zoom_indicator'):
            self.zoom_indicator.config(text=f"🔍 Zoom: {int(scale * 100)}%")
        
        # Save and update status
        self.cfg["ui_scale"] = scale
        save_config(self.cfg)
        self._status(f"Zoom: {int(scale * 100)}% - {'🔍 Zoomed In' if scale > old_scale else '🔍 Zoomed Out' if scale < old_scale else '🔍 Reset'}")
    
    def _update_font_system(self, scale: float):
        """Update the font system with scaled fonts for this app instance"""
        # Get base fonts from config
        from config import FONTS as BASE_FONTS
        
        # Create scaled fonts
        scaled_fonts = {}
        for key, font_def in BASE_FONTS.items():
            if isinstance(font_def, (tuple, list)) and len(font_def) >= 2:
                family = font_def[0]
                base_size = font_def[1]
                style = font_def[2] if len(font_def) > 2 else "normal"
                
                # Scale the size
                new_size = max(8, int(base_size * scale))
                
                if style == "normal":
                    scaled_fonts[key] = (family, new_size)
                else:
                    scaled_fonts[key] = (family, new_size, style)
            else:
                # Keep as-is if not a proper font definition
                scaled_fonts[key] = font_def
        
        # Store reference for this app instance
        self._scaled_fonts = scaled_fonts
        self._base_fonts = BASE_FONTS  # Keep reference to original fonts
    
    def _get_scaled_font(self, font_key: str):
        """Get a scaled font by key"""
        if hasattr(self, '_scaled_fonts') and font_key in self._scaled_fonts:
            return self._scaled_fonts[font_key]
        
        # Fallback to global F
        return F.get(font_key, ("Segoe UI", 10))
    
    def _scale_all_windows_absolute(self, target_scale: float):
        """Scale all windows using absolute scale factor to avoid cumulative errors"""
        # Scale main window
        self._scale_window_content_absolute(self, target_scale)
        
        # Find and scale all Toplevel windows (dialogs)
        all_windows = self.winfo_children()
        for widget in all_windows:
            if isinstance(widget, tk.Toplevel):
                self._scale_window_content_absolute(widget, target_scale)
            # Also recursively check children
            self._scale_recursive_children_absolute(widget, target_scale)
    
    def _scale_window_content_absolute(self, window, target_scale: float):
        """Scale content of a specific window using absolute scale"""
        # Scale fonts
        self._scale_fonts_in_window_absolute(window, target_scale)
        
        # Scale dimensions
        self._scale_dimensions_in_window_absolute(window, target_scale)
    
    def _scale_recursive_children_absolute(self, widget, target_scale: float):
        """Recursively scale all child widgets using absolute scale"""
        for child in widget.winfo_children():
            if isinstance(child, tk.Toplevel):
                self._scale_window_content_absolute(child, target_scale)
            else:
                self._scale_fonts_in_widget_absolute(child, target_scale)
                self._scale_dimensions_in_widget_absolute(child, target_scale)
                self._scale_recursive_children_absolute(child, target_scale)
    
    def _scale_fonts_in_window_absolute(self, window, target_scale: float):
        """Scale fonts in a specific window using absolute scale"""
        def update_widget_font(widget):
            try:
                self._scale_fonts_in_widget_absolute(widget, target_scale)
                # Recursively update children
                for child in widget.winfo_children():
                    update_widget_font(child)
            except:
                pass
        
        update_widget_font(window)
    
    def _scale_fonts_in_widget_absolute(self, widget, target_scale: float):
        """Scale fonts in a specific widget using absolute scale"""
        try:
            current_font = widget.cget("font")
            if isinstance(current_font, (tuple, list)):
                font_family = current_font[0] if len(current_font) > 0 else "Segoe UI"
                current_size = current_font[1] if len(current_font) > 1 else 10
                
                # Find the matching base font from our font system
                base_size = self._find_base_font_size(font_family, current_size)
                new_size = max(8, int(base_size * target_scale))
                
                if len(current_font) > 2:
                    new_font = (font_family, new_size) + tuple(current_font[2:])
                else:
                    new_font = (font_family, new_size)
                widget.config(font=new_font)
            elif isinstance(current_font, str):
                # Handle named fonts - update them directly
                import tkinter.font as tkfont
                try:
                    font_obj = tkfont.nametofont(current_font)
                    if font_obj:
                        base_size = self._find_base_named_font_size(current_font)
                        new_size = max(8, int(base_size * target_scale))
                        font_obj.config(size=new_size)
                except:
                    pass
        except:
            pass
    
    def _find_base_font_size(self, font_family, current_size):
        """Find the base font size from our font system"""
        # Use stored base fonts if available
        base_fonts = getattr(self, '_base_fonts', None)
        if not base_fonts:
            from config import FONTS as BASE_FONTS
            base_fonts = BASE_FONTS
        
        # Look for matching font in our base font system
        for key, font_def in base_fonts.items():
            if isinstance(font_def, (tuple, list)) and len(font_def) >= 2:
                base_family = font_def[0]
                base_size = font_def[1]
                
                # Check if this matches the current font family
                if base_family.lower() == font_family.lower():
                    # Check if current size is close to scaled version of base
                    scaled_size = int(base_size * self.ui_scale)
                    if abs(current_size - scaled_size) <= 1:  # Allow 1px tolerance
                        return base_size
                    
                    # If current size looks like base size, return it
                    if abs(current_size - base_size) <= 1:
                        return base_size
        
        # Fallback: estimate base size by dividing by current scale if it looks scaled
        if current_size > 15 and self.ui_scale != 1.0:
            estimated = current_size / self.ui_scale
            if 8 <= estimated <= 20:  # Reasonable font size range
                return estimated
        
        # Default fallback
        return current_size if current_size <= 15 else 10
    
    def _find_base_named_font_size(self, font_name):
        """Find base size for named fonts"""
        try:
            import tkinter.font as tkfont
            font_obj = tkfont.nametofont(font_name)
            if font_obj:
                current_size = font_obj.cget("size")
                
                # Use stored base fonts if available
                base_fonts = getattr(self, '_base_fonts', None)
                if not base_fonts:
                    from config import FONTS as BASE_FONTS
                    base_fonts = BASE_FONTS
                
                for key, font_def in base_fonts.items():
                    if isinstance(font_def, (tuple, list)) and len(font_def) >= 2:
                        base_size = font_def[1]
                        scaled_size = int(base_size * self.ui_scale)
                        
                        if abs(current_size - scaled_size) <= 1:
                            return base_size
                        elif abs(current_size - base_size) <= 1:
                            return base_size
                
                # Fallback: normalize if it looks scaled
                if abs(current_size) > 15 and self.ui_scale != 1.0:
                    estimated = abs(current_size) / self.ui_scale
                    if 8 <= estimated <= 20:
                        return estimated
                
                return abs(current_size)
        except:
            pass
        return 10
    
    def _scale_dimensions_in_window_absolute(self, window, target_scale: float):
        """Scale dimensions in a specific window using absolute scale"""
        def update_widget_dimensions(widget):
            try:
                self._scale_dimensions_in_widget_absolute(widget, target_scale)
                # Recursively update children
                for child in widget.winfo_children():
                    update_widget_dimensions(child)
            except:
                pass
        
        update_widget_dimensions(window)
    
    def _scale_dimensions_in_widget_absolute(self, widget, target_scale: float):
        """Scale dimensions in a specific widget using absolute scale"""
        try:
            # Scale padding
            for option in ["padx", "pady", "ipadx", "ipady"]:
                try:
                    current = widget.cget(option)
                    if isinstance(current, (tuple, list)):
                        # Calculate base padding and scale
                        base_vals = [self._normalize_dimension(x) for x in current]
                        new_val = tuple(int(x * target_scale) for x in base_vals)
                    elif isinstance(current, int):
                        base_val = self._normalize_dimension(current)
                        new_val = int(base_val * target_scale)
                    else:
                        continue
                    widget.config(**{option: new_val})
                except:
                    pass
            
            # Scale width/height for certain widgets
            widget_class = widget.winfo_class()
            if widget_class in ["Entry", "Button", "Label"]:
                try:
                    width = widget.cget("width")
                    if isinstance(width, int) and width > 0:
                        base_width = self._normalize_dimension(width)
                        new_width = max(5, int(base_width * target_scale))
                        widget.config(width=new_width)
                except:
                    pass
        except:
            pass
    
    def _normalize_dimension(self, value):
        """Normalize a dimension value back to base size"""
        try:
            # If value looks like it's already scaled, normalize it
            if value > 50:  # Likely already scaled padding
                return value / self.ui_scale if self.ui_scale != 0 else value
            return value
        except:
            return value
    
    def _on_mousewheel_zoom(self, event):
        """Handle mouse wheel zooming with Ctrl+Wheel"""
        try:
            if event.delta:
                # Windows
                if event.delta > 0:
                    self._zoom_in()
                else:
                    self._zoom_out()
            else:
                # Linux
                if event.num == 4:
                    self._zoom_in()
                else:
                    self._zoom_out()
        except Exception as e:
            print(f"Mouse wheel zoom error: {e}")
            pass
    
    def _zoom_in(self):
        """Zoom in by 0.1 increments, respecting maximum limit"""
        if self.ui_scale < 2.0:  # Only zoom if not at max
            new_scale = min(2.0, self.ui_scale + 0.1)
            self._apply_zoom(new_scale)
        else:
            self._status("Already at maximum zoom (200%)")

    def _zoom_out(self):
        """Zoom out by 0.1 increments, respecting minimum limit"""
        if self.ui_scale > 0.5:  # Only zoom if not at min
            new_scale = max(0.5, self.ui_scale - 0.1)
            self._apply_zoom(new_scale)
        else:
            self._status("Already at minimum zoom (50%)")

    def _zoom_reset(self):
        """Reset zoom to default 100%"""
        if self.ui_scale != 1.0:
            self._apply_zoom(1.0)
        else:
            self._status("Zoom already at default (100%)")

    def _select_fmt(self, fmt: str):
        self.out_fmt.set(fmt)
        for f2, b in self._fmt_btns.items():
            b.config(bg=self.ACCENT if f2==fmt else self.CARD2,
                     fg="#ffffff" if f2==fmt else self.TEXT2)
        notes = {
            "png": "" if (HAS_PDF2IMAGE and HAS_CAIROSVG) else "⚠  For PDF/SVG exports install: pip install pdf2image cairosvg (+ poppler-utils for PDF)",
            "jpg": "" if (HAS_PDF2IMAGE and HAS_CAIROSVG) else "⚠  For PDF/SVG exports install: pip install pdf2image cairosvg (+ poppler-utils for PDF)",
            "docx": "" if HAS_DOCX else "⚠  pip install python-docx",
            "xlsx": "" if HAS_OPENPYXL else "⚠  pip install openpyxl",
            "pptx": "" if HAS_PPTX else "⚠  pip install python-pptx",
            "mp3":  "" if HAS_FFMPEG else "⚠  sudo apt install ffmpeg",
            "mp4":  "" if HAS_FFMPEG else "⚠  sudo apt install ffmpeg",
        }
        if hasattr(self,"conv_note"):
            self.conv_note.config(text=notes.get(fmt,""))

    def _switch_tab(self, key: str):
        """Switch to a specific tab with enhanced selection highlighting"""
        # Update active tab tracking
        self.active_tab = key
        
        # Update button states with proper active state styling
        for k, b in self.tab_btns.items():
            if k == key:
                # Active tab: accent background with white text and 3px left border
                b.config(bg=self.ACCENT, fg="#ffffff", 
                        relief="flat", bd=3, 
                        cursor="hand2",
                        borderwidth=3,
                        highlightbackground=self.ACCENT,
                        highlightthickness=0)
            else:
                # Inactive tabs: normal state with hover effects
                b.config(bg=self.SIDEBAR, fg=self.TEXT2, 
                        relief="flat", bd=0, 
                        cursor="hand2",
                        borderwidth=0,
                        highlightthickness=0)
        
        # Show/hide pages
        for k, page in self.pages.items():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        
        # Reapply zoom to ensure it persists across tab switches
        if self.ui_scale != 1.0:
            self._scale_window_content_absolute(self.pages[key], self.ui_scale)
        
        # Update mode for AI chat if needed
        if key == "aichat":
            self._set_ai_mode(self.ai_mode.get())
        
        # Update status
        tab_names = {k: f"{icon} {label}" for icon, label, k in self.TABS}
        self._status(f"Switched to {tab_names.get(key, key)}")
        if key == "video":  self._refresh_video_merge_preview()
        if key == "queue":  self._on_queue_select()
        if key == "log":    self._apply_log_filter()

    def _update_ai_status(self):
        provider = (self.cfg.get("ai_provider", "nvidia") or "nvidia").lower()
        if self.ai.is_ready:
            model = self.cfg.get("nvidia_model", "?") if provider == "nvidia" else self.cfg.get("gemini_model", "?")
            prefix = "NIM" if provider == "nvidia" else "Gemini"
            self.ai_status_lbl.config(text=f"🟢 AI ({prefix}): {model}", fg=self.SUCCESS)
            if hasattr(self, "ai_model_lbl"):
                self.ai_model_lbl.config(text=f"· {model}", fg=self.ACCENT3)
        else:
            if provider == "nvidia" and not HAS_NIM:
                self.ai_status_lbl.config(text="🔴 AI: pip install openai", fg=self.ERROR)
                if hasattr(self, "ai_model_lbl"):
                    self.ai_model_lbl.config(text="· NVIDIA client unavailable", fg=self.ERROR)
                return
            if provider == "gemini" and not HAS_GENAI:
                self.ai_status_lbl.config(text="🔴 AI: pip install google-genai", fg=self.ERROR)
                if hasattr(self, "ai_model_lbl"):
                    self.ai_model_lbl.config(text="· Gemini client unavailable", fg=self.ERROR)
                return
            self.ai_status_lbl.config(text="⚪ AI: open ⚙ to configure", fg=self.TEXT2)
            if hasattr(self, "ai_model_lbl"):
                self.ai_model_lbl.config(text="· open ⚙ Settings to connect", fg=self.TEXT2)

    # ══════════════════════════════════════════════════════════════════════════
    # LOG SYSTEM  —  thread-safe, timestamped, filterable
    # ══════════════════════════════════════════════════════════════════════════

    def _log(self, msg: str, kind: str = "", op: str = ""):
        """
        Append a log entry. Thread-safe — can be called from any thread.
        kind: ok | err | warn | info | ai  (controls colour)
        op:   operation name for grouping (optional)
        """
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {"ts": ts, "msg": msg, "kind": kind, "op": op}

        def _do():
            # Store entry
            if not hasattr(self, "_log_entries"):
                self._log_entries = []
            self._log_entries.append(entry)

            # Update stats
            if not hasattr(self, "_log_count"):
                self._log_count = {"ok": 0, "err": 0, "warn": 0, "total": 0}
            self._log_count["total"] += 1
            if kind in ("ok", "err", "warn"):
                self._log_count[kind] += 1
            self._update_log_stats()

            # Write to display
            self._write_log_entry(entry)

            # Flash the Log tab button if not currently on log page
            if hasattr(self, "tab_btns") and "log" in self.tab_btns:
                if self.pages["log"].winfo_ismapped() is False:
                    self._flash_log_badge(kind)

            # Update status bar with last message
            icon = {"ok":"✔","err":"✖","warn":"⚠","info":"ℹ","ai":"🤖"}.get(kind,"·")
            self.status_var.set(f"  {icon}  {msg[:90]}")

        self.after(0, _do)

    def _write_log_entry(self, entry: dict):
        """Write a single entry to the log_box widget."""
        if not hasattr(self, "log_box"): return

        # Apply current filter
        ftype = self.log_filter_var.get().strip().lower() if hasattr(self, "log_filter_var") else ""
        fkind = self.log_filter_type.get() if hasattr(self, "log_filter_type") else "all"

        # Text filter
        if ftype and ftype not in entry["msg"].lower() and ftype not in entry["kind"]:
            return
        # Kind filter
        if fkind != "all" and entry["kind"] != fkind:
            return

        tag = {"ok":"ok","err":"err","warn":"warn","info":"info","ai":"ai"}.get(entry["kind"],"")
        prefix = {"ok":"✔ ","err":"✖ ","warn":"⚠ ","info":"  ","ai":"🤖 "}.get(entry["kind"],"  ")

        self.log_box.config(state="normal")
        self.log_box.insert("end", f"[{entry['ts']}] ", "ts")
        self.log_box.insert("end", f"{prefix}{entry['msg']}\n", tag or "info")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _update_log_stats(self):
        """Refresh the stats labels at the top of the log page."""
        if not hasattr(self, "log_stats_ok"): return
        c = self._log_count
        self.log_stats_ok.config(   text=f"✔ {c['ok']}")
        self.log_stats_err.config(  text=f"✖ {c['err']}")
        self.log_stats_warn.config( text=f"⚠ {c['warn']}")
        self.log_stats_total.config(text=f"Total: {c['total']}")

    def _apply_log_filter(self, _=None):
        """Re-render the log box applying current filter settings."""
        if not hasattr(self, "log_box") or not hasattr(self, "_log_entries"): return
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")
        for entry in self._log_entries:
            self._write_log_entry(entry)

    def _clear_log(self):
        if not hasattr(self, "log_box"): return
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")
        if hasattr(self, "_log_entries"):
            self._log_entries.clear()
        if hasattr(self, "_log_count"):
            self._log_count = {"ok": 0, "err": 0, "warn": 0, "total": 0}
            self._update_log_stats()

    def _copy_log(self):
        """Copy the full log to clipboard."""
        if not hasattr(self, "_log_entries"): return
        lines = [f"[{e['ts']}] {e['msg']}" for e in self._log_entries]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self._log("Log copied to clipboard.", "info")

    def _op_start(self, name: str):
        """
        Call at the start of any background operation.
        Increments the running counter and shows the badge.
        """
        self._running_ops = getattr(self, "_running_ops", 0) + 1
        self._update_ops_badge()
        self._log(f"▶  {name} started …", "info", op=name)

    def _op_done(self, name: str, success: bool = True):
        """Call when a background operation finishes."""
        self._running_ops = max(0, getattr(self, "_running_ops", 0) - 1)
        self._update_ops_badge()
        kind = "ok" if success else "err"
        symbol = "✔" if success else "✖"
        self._log(f"{symbol}  {name} finished.", kind, op=name)

    def _update_ops_badge(self):
        """Show/hide/update the topbar badge."""
        def _do():
            n = getattr(self, "_running_ops", 0)
            if n > 0:
                self.ops_badge.config(
                    text=f"⚙  {n} running — click for log",
                    bg=self.ACCENT4, fg="#000000")
                self.ops_badge.pack(side="left", padx=(0, 8))
            else:
                self.ops_badge.config(text="", bg=self.SIDEBAR)
                self.ops_badge.pack_forget()
            if hasattr(self, "log_running_lbl"):
                self.log_running_lbl.config(
                    text=f"⚙  {n} operation(s) running" if n > 0 else "All operations complete ✔",
                    fg=self.ACCENT4 if n > 0 else self.SUCCESS)
        self.after(0, _do)

    def _flash_log_badge(self, kind: str):
        """Briefly highlight the Log tab button when new entries arrive."""
        if not hasattr(self, "tab_btns") or "log" not in self.tab_btns: return
        btn = self.tab_btns["log"]
        color = {"ok": self.SUCCESS, "err": self.ERROR, "warn": self.WARN}.get(kind, self.ACCENT)
        orig = self.SIDEBAR
        btn.config(fg=color)
        self.after(1200, lambda: btn.config(fg=self.TEXT2 if btn.cget("bg") == self.SIDEBAR else "#ffffff"))

    def _status(self, msg: str):
        self.after(0, lambda: self.status_var.set("  " + msg))

    def _refresh_deps(self):
        deps=[HAS_PYPDF,HAS_PDFPLUMBER,HAS_DOCX,HAS_PIL,
              HAS_PDF2IMAGE,HAS_FFMPEG,HAS_OPENPYXL,HAS_PPTX,HAS_LIBREOFFICE]
        n=sum(deps)
        self.dep_lbl.config(text=f"deps {n}/{len(deps)} ✓",
                             fg=self.SUCCESS if n==len(deps) else self.WARN)
        Tooltip(self.dep_lbl,
                f"pypdf:       {'✔' if HAS_PYPDF else '✖'}\n"
                f"pdfplumber:  {'✔' if HAS_PDFPLUMBER else '✖'}\n"
                f"python-docx: {'✔' if HAS_DOCX else '✖'}\n"
                f"Pillow:      {'✔' if HAS_PIL else '✖'}\n"
                f"pdf2image:   {'✔' if HAS_PDF2IMAGE else '✖'}\n"
                f"ffmpeg:      {'✔' if HAS_FFMPEG else '✖'}\n"
                f"openpyxl:    {'✔' if HAS_OPENPYXL else '✖'}\n"
                f"python-pptx: {'✔' if HAS_PPTX else '✖'}\n"
                f"LibreOffice: {'✔' if HAS_LIBREOFFICE else '✖'}")
