"""
ui/app.py — File Workshop AI  v2
Chat-first interface: AI lives at the centre, tools slide in as needed.

Layout:
  ┌──────────────────────────────────────────────────────────────┐
  │  TOPBAR:  Logo · AI status · Drop zone · Settings            │
  ├────────────┬─────────────────────────────────┬───────────────┤
  │  SIDEBAR   │   CENTRE (tool panel / chat)    │  CHAT PANEL   │
  │  nav tabs  │   switches based on active tab  │  always live  │
  └────────────┴─────────────────────────────────┴───────────────┘
"""

import os, sys, threading, subprocess, shutil, time
from pathlib import Path
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DARK as C, FONTS as F, load_config, save_config, GEMINI_MODELS
from core.processor import (
    cat, cat_icon, parse_pages, parse_groups, do_convert,
    pdf_page_count, pptx_slide_count,
    split_each, split_range, split_custom,
    merge_pdfs, pptx_merge, pptx_split_slides,
    resequence_pdf, delete_pages, rotate_pages, reverse_pdf,
    compress_pdf, encrypt_pdf, decrypt_pdf,
    watermark_text, watermark_pdf_overlay,
    get_metadata, set_metadata,
    HAS_PYPDF, HAS_PDFPLUMBER, HAS_DOCX, HAS_PIL,
    HAS_PDF2IMAGE, HAS_FFMPEG, HAS_OPENPYXL, HAS_PPTX, HAS_LIBREOFFICE,
    IMAGE_EXTS, AUDIO_EXTS, VIDEO_EXTS, EXCEL_EXTS, PPTX_EXTS, CSV_EXTS
)
from ai.gemini import GeminiClient, HAS_GENAI
from ai.extractor import extract_text, get_file_summary_context, is_image, is_text_extractable
from utils.upscaler import upscale_image, batch_upscale, get_image_info, SCALE_METHODS, HAS_PIL as UP_PIL

# ── Palette shortcuts ──────────────────────────────────────────────────────────
BG      = C["bg"]
PANEL   = C["panel"]
CARD    = C["card"]
CARD2   = C["card2"]
BORDER  = C["border"]
BORDER2 = C["border2"]
ACCENT  = C["accent"]
ACCENT2 = C["accent2"]
ACCENT3 = C["accent3"]
ACCENT4 = C["accent4"]
TEXT    = C["text"]
TEXT2   = C["text2"]
DIM2    = C["dim2"]
SUCCESS = C["success"]
WARN    = C["warning"]
ERROR   = C["error"]
SIDEBAR = C["sidebar"]
LOG_BG  = C["log_bg"]
INPUT_BG= C["input_bg"]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

class Tooltip:
    def __init__(self, w, text):
        self.w=w; self.text=text; self.tip=None
        w.bind("<Enter>", self.show); w.bind("<Leave>", self.hide)
    def show(self, _=None):
        x=self.w.winfo_rootx()+24; y=self.w.winfo_rooty()+20
        self.tip=tw=tk.Toplevel(self.w); tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, font=F["small"], bg="#1a1a2e",
                 fg=TEXT, relief="flat", padx=10, pady=6,
                 wraplength=340, justify="left").pack()
    def hide(self, _=None):
        if self.tip: self.tip.destroy(); self.tip=None


def mk_btn(parent, text, cmd, bg=None, fg="#ffffff", font=None, padx=10, pady=5):
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg or ACCENT2, fg=fg,
                     activebackground=BORDER2, activeforeground=fg,
                     relief="flat", cursor="hand2", bd=0,
                     font=font or F["btn"], padx=padx, pady=pady)

def mk_big_btn(parent, text, cmd, bg=None):
    return mk_btn(parent, text, cmd, bg=bg or ACCENT,
                  font=F["btnbig"], padx=18, pady=10)

def sep(parent, vertical=False):
    orient = "vertical" if vertical else "horizontal"
    c = BORDER
    if vertical:
        return tk.Frame(parent, bg=c, width=1)
    return tk.Frame(parent, bg=c, height=1)

def card(parent, **kw):
    f = tk.Frame(parent, bg=PANEL, padx=16, pady=12, **kw)
    f.pack(fill="x", padx=14, pady=(0, 8))
    return f

def section_hdr(parent, title, subtitle=""):
    h = tk.Frame(parent, bg=BG); h.pack(fill="x", padx=14, pady=(14, 6))
    tk.Label(h, text=title, font=F["head"], bg=BG, fg=ACCENT).pack(side="left")
    if subtitle:
        tk.Label(h, text=f"  —  {subtitle}", font=F["small"],
                 bg=BG, fg=TEXT2).pack(side="left")

def lbl(parent, text, head=False, dim=False, w=None, wrap=None, mono=False):
    bg = PANEL
    try: bg = parent.cget("bg")
    except: pass
    kw = dict(bg=bg, fg=TEXT2 if dim else TEXT, anchor="w",
              font=F["head"] if head else (F["mono"] if mono else F["body"]))
    if w: kw["width"] = w
    if wrap: kw["wraplength"] = wrap; kw["justify"] = "left"
    return tk.Label(parent, text=text, **kw)

def entry(parent, var, width=22, show=None, mono=True):
    kw = dict(textvariable=var, font=F["mono"] if mono else F["body"],
              bg=CARD2, fg=TEXT, insertbackground=TEXT,
              relief="flat", bd=0, width=width)
    if show: kw["show"] = show
    return tk.Entry(parent, **kw)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════

class AIWorkshopApp(tk.Tk):

    TABS = [
        ("🏠", "Home",      "home"),
        ("🔄", "Convert",   "convert"),
        ("✂️",  "Split",     "split"),
        ("🔗", "Merge",     "merge"),
        ("📐", "Organise",  "organise"),
        ("🖼",  "Upscale",   "upscale"),
        ("💧", "Stamp",     "stamp"),
        ("🔒", "Protect",   "protect"),
        ("📦", "Compress",  "compress"),
        ("🏷",  "Metadata",  "metadata"),
        ("📋", "Queue",     "queue"),
    ]

    def __init__(self):
        super().__init__()
        self.title("File Workshop AI")
        self.configure(bg=BG)
        self.geometry("1480x860")
        self.minsize(1100, 720)

        self.cfg    = load_config()
        self.files: List[str] = []
        self.out_dir = tk.StringVar(value=self.cfg.get("output_dir", ""))
        self.page_count = 0
        self.active_pdf = ""
        self.ai_context_file = ""

        self.ai = GeminiClient(
            self.cfg.get("gemini_api_key", ""),
            self.cfg.get("gemini_model", "gemini-1.5-flash")
        )

        self.pages: Dict[str, tk.Frame] = {}
        self.tab_btns: Dict[str, tk.Button] = {}

        self._build()
        self._switch_tab("home")
        self._status("Welcome — drop files or type a command to the AI")
        self._update_ai_status()

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build(self):
        self._build_topbar()
        body = tk.Frame(self, bg=BG); body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_chat_rail(body)   # pack RIGHT first
        self._build_centre(body)

    # ── Topbar ────────────────────────────────────────────────────────────────

    def _build_topbar(self):
        bar = tk.Frame(self, bg=SIDEBAR, height=56)
        bar.pack(fill="x"); bar.pack_propagate(False)

        # Logo
        logo = tk.Frame(bar, bg=SIDEBAR); logo.pack(side="left", padx=18, pady=10)
        tk.Label(logo, text="⬛ FILE WORKSHOP",
                 font=("Segoe UI", 15, "bold"), bg=SIDEBAR, fg=ACCENT).pack(side="left")
        tk.Label(logo, text=" AI",
                 font=("Segoe UI", 15, "bold"), bg=SIDEBAR, fg=ACCENT3).pack(side="left")

        # Drop hint
        tk.Label(bar, text="Drop files anywhere or type a command →",
                 font=("Segoe UI", 9), bg=SIDEBAR, fg=TEXT2).pack(side="left", padx=20)

        # Right controls
        right = tk.Frame(bar, bg=SIDEBAR); right.pack(side="right", padx=14)
        self.ai_status_lbl = tk.Label(right, text="", font=F["small"], bg=SIDEBAR, fg=TEXT2)
        self.ai_status_lbl.pack(side="left", padx=(0, 14))
        mk_btn(right, "⚙  Settings",   self._open_settings, BORDER2).pack(side="left", padx=4)
        mk_btn(right, "📂 Open Output", self._open_output,   BORDER2).pack(side="left", padx=4)
        mk_btn(right, "+ Add Files",    self._add_files,     ACCENT).pack(side="left", padx=4)

    # ── Left sidebar ──────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=SIDEBAR, width=176)
        sb.pack(side="left", fill="y"); sb.pack_propagate(False)

        tk.Label(sb, text="TOOLS", font=("Consolas", 8, "bold"),
                 bg=SIDEBAR, fg=DIM2).pack(anchor="w", padx=14, pady=(18, 6))

        for icon, label, key in self.TABS:
            b = tk.Button(sb, text=f"  {icon}  {label}",
                          font=("Segoe UI", 10),
                          bg=SIDEBAR, fg=TEXT2,
                          relief="flat", bd=0, cursor="hand2",
                          anchor="w", padx=12, pady=8,
                          activebackground=CARD,
                          command=lambda k=key: self._switch_tab(k))
            b.pack(fill="x")
            self.tab_btns[key] = b

        sep(sb).pack(fill="x", padx=10, pady=10)

        # Output folder
        tk.Label(sb, text="OUTPUT", font=("Consolas", 8, "bold"),
                 bg=SIDEBAR, fg=DIM2).pack(anchor="w", padx=14, pady=(0, 4))
        od = tk.Frame(sb, bg=SIDEBAR); od.pack(fill="x", padx=8, pady=(0, 2))
        tk.Entry(od, textvariable=self.out_dir, font=("Consolas", 8),
                 bg=CARD, fg=TEXT, insertbackground=TEXT,
                 relief="flat", bd=0).pack(fill="x", ipady=3, padx=2)
        mk_btn(sb, "📁 Set Folder", self._browse_output, BORDER2).pack(fill="x", padx=8, pady=2)

        sep(sb).pack(fill="x", padx=10, pady=8)

        self.file_badge = tk.Label(sb, text="No files loaded",
                                    font=("Consolas", 8), bg=SIDEBAR, fg=TEXT2,
                                    wraplength=158, justify="left")
        self.file_badge.pack(anchor="w", padx=12)

        sep(sb).pack(fill="x", padx=10, pady=8)

        self.dep_lbl = tk.Label(sb, text="", font=("Consolas", 8),
                                 bg=SIDEBAR, fg=TEXT2)
        self.dep_lbl.pack(anchor="w", padx=12, pady=(0, 6))
        self._refresh_deps()

    # ── Centre panel ──────────────────────────────────────────────────────────

    def _build_centre(self, parent):
        self._centre = tk.Frame(parent, bg=BG)
        self._centre.pack(side="left", fill="both", expand=True)

        for _, _, key in self.TABS:
            f = tk.Frame(self._centre, bg=BG)
            self.pages[key] = f

        self._build_home_page()
        self._build_convert_page()
        self._build_split_page()
        self._build_merge_page()
        self._build_organise_page()
        self._build_upscale_page()
        self._build_stamp_page()
        self._build_protect_page()
        self._build_compress_page()
        self._build_metadata_page()
        self._build_queue_page()

        # Log bar
        log_wrap = tk.Frame(self._centre, bg=LOG_BG)
        log_wrap.pack(fill="x", padx=12, pady=(0, 6), side="bottom")
        lhdr2 = tk.Frame(log_wrap, bg=LOG_BG); lhdr2.pack(fill="x")
        tk.Label(lhdr2, text="LOG", font=("Consolas", 8, "bold"),
                 bg=LOG_BG, fg=DIM2).pack(side="left", padx=8, pady=(4, 2))
        mk_btn(lhdr2, "Clear", self._clear_log, BORDER2).pack(side="right", padx=6, pady=2)

        self.log_box = scrolledtext.ScrolledText(
            log_wrap, height=4, font=F["mono_sm"],
            bg=LOG_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", state="disabled", bd=0)
        self.log_box.pack(fill="x", padx=2, pady=(0, 4))
        for tag, col in [("ok", SUCCESS), ("err", ERROR),
                          ("info", ACCENT), ("warn", WARN), ("ai", ACCENT3)]:
            self.log_box.tag_config(tag, foreground=col)

        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self._centre, textvariable=self.status_var,
                 font=F["small"], bg=BORDER, fg=TEXT2,
                 anchor="w", padx=10, pady=3).pack(fill="x", side="bottom")

    # ── AI Chat Rail (right panel) ────────────────────────────────────────────

    def _build_chat_rail(self, parent):
        rail = tk.Frame(parent, bg=PANEL, width=380)
        rail.pack(side="right", fill="y"); rail.pack_propagate(False)

        # Header
        hdr = tk.Frame(rail, bg=CARD, pady=12); hdr.pack(fill="x")
        tk.Label(hdr, text="🤖  AI ASSISTANT",
                 font=("Segoe UI", 11, "bold"), bg=CARD, fg=ACCENT3).pack(side="left", padx=14)
        mk_btn(hdr, "🗑", self._clear_chat, BORDER2, pady=3, padx=6).pack(side="right", padx=8)

        # Mode pills
        mode_bar = tk.Frame(rail, bg=PANEL); mode_bar.pack(fill="x", padx=10, pady=(8, 4))
        self.ai_mode = tk.StringVar(value="chat")
        self._mode_btns: Dict[str, tk.Button] = {}
        modes = [("💬", "chat", "Chat"), ("📄", "qa", "Doc Q&A"),
                 ("📋", "summarise", "Summarise"), ("🗂", "plan", "Plan")]
        for icon, val, tip in modes:
            b = tk.Button(mode_bar, text=f"{icon} {tip}",
                          font=("Segoe UI", 9),
                          bg=CARD2, fg=TEXT2,
                          relief="flat", cursor="hand2",
                          padx=8, pady=4, bd=0,
                          activebackground=ACCENT3,
                          command=lambda v=val: self._set_ai_mode(v))
            b.pack(side="left", padx=(0, 4))
            self._mode_btns[val] = b
        self._set_ai_mode("chat", init=True)

        # Active file selector (for Doc Q&A / Summarise)
        self.ai_file_frame = tk.Frame(rail, bg=PANEL)
        self.ai_file_frame.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(self.ai_file_frame, text="File:", font=F["small"],
                 bg=PANEL, fg=TEXT2).pack(side="left")
        self.ai_file_var = tk.StringVar(value="(double-click file in queue)")
        self.ai_file_menu = tk.OptionMenu(self.ai_file_frame, self.ai_file_var, "(none)")
        self.ai_file_menu.config(font=F["small"], bg=CARD2, fg=TEXT,
                                  activebackground=BORDER,
                                  relief="flat", bd=0, highlightthickness=0)
        self.ai_file_menu.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Chat history display
        self.chat_display = scrolledtext.ScrolledText(
            rail, font=("Segoe UI", 10),
            bg=LOG_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", state="disabled", bd=0, wrap="word")
        self.chat_display.pack(fill="both", expand=True, padx=0, pady=0)

        self.chat_display.tag_config("user_lbl",  foreground=ACCENT,  font=("Segoe UI", 9, "bold"))
        self.chat_display.tag_config("user_msg",  foreground=TEXT,    lmargin1=14, lmargin2=14)
        self.chat_display.tag_config("ai_lbl",    foreground=ACCENT3, font=("Segoe UI", 9, "bold"))
        self.chat_display.tag_config("ai_msg",    foreground=TEXT,    lmargin1=14, lmargin2=14)
        self.chat_display.tag_config("sys_msg",   foreground=TEXT2,   font=("Segoe UI", 9, "italic"), lmargin1=14)
        self.chat_display.tag_config("err_msg",   foreground=ERROR,   lmargin1=14)
        self.chat_display.tag_config("intent_msg",foreground=ACCENT4, font=("Consolas", 9), lmargin1=14)
        self.chat_display.tag_config("divider",   foreground=DIM2)

        # Quick-action chips
        chip_bar = tk.Frame(rail, bg=PANEL); chip_bar.pack(fill="x", padx=10, pady=(6, 4))
        tk.Label(chip_bar, text="Quick:", font=("Segoe UI", 8),
                 bg=PANEL, fg=TEXT2).pack(side="left")
        for txt, prompt in [
            ("Summarise",      "Summarise the selected file"),
            ("Best format?",   "What is the best output format for my file?"),
            ("What's inside?", "What data or content is in this file?"),
            ("Make a plan",    "Plan the best operations for all my queued files"),
        ]:
            b = tk.Button(chip_bar, text=txt,
                          font=("Segoe UI", 8),
                          bg=CARD2, fg=TEXT2,
                          relief="flat", cursor="hand2",
                          padx=7, pady=2, bd=0,
                          activebackground=BORDER2,
                          command=lambda p=prompt: self._quick_prompt(p))
            b.pack(side="left", padx=(4, 0))

        # Input area
        input_outer = tk.Frame(rail, bg=INPUT_BG)
        input_outer.pack(fill="x", padx=0, pady=0)

        self.chat_input = tk.Text(
            input_outer, height=3, font=("Segoe UI", 10),
            bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=0, wrap="word")
        self.chat_input.pack(fill="x", padx=12, pady=(10, 4))
        self.chat_input.bind("<Return>",       self._on_enter)
        self.chat_input.bind("<Shift-Return>", lambda e: None)

        # placeholder hint
        self._placeholder = "Type a command or question… (Enter to send)"
        self._placeholder_active = False   # flag tracks whether hint text is showing
        self._set_placeholder()
        self.chat_input.bind("<FocusIn>",  self._clear_placeholder)
        self.chat_input.bind("<FocusOut>", self._restore_placeholder)

        input_btns = tk.Frame(input_outer, bg=INPUT_BG)
        input_btns.pack(fill="x", padx=10, pady=(0, 8))
        mk_btn(input_btns, "↑  Send", self._send_btn,
               ACCENT3, padx=14, pady=6).pack(side="left")
        mk_btn(input_btns, "🖼 Analyse Image", self._analyse_image,
               BORDER2, padx=10, pady=6).pack(side="left", padx=(6, 0))

        self._ai_sys("Welcome! I'm your AI assistant.\n"
                     "Add files, then ask me anything — I can convert, summarise,\n"
                     "analyse images, answer questions about documents, and more.\n\n"
                     "💡 Configure your Gemini API key in ⚙ Settings to get started.")

    # ══════════════════════════════════════════════════════════════════════════
    # HOME PAGE  —  the friendly landing experience
    # ══════════════════════════════════════════════════════════════════════════

    def _build_home_page(self):
        f = self.pages["home"]

        # Hero area
        hero = tk.Frame(f, bg=BG); hero.pack(fill="x", padx=30, pady=(30, 0))
        tk.Label(hero, text="Welcome to File Workshop AI",
                 font=("Segoe UI", 22, "bold"), bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(hero, text="Your intelligent file toolkit. Convert · Split · Merge · Upscale · Analyse — all in one place.",
                 font=("Segoe UI", 11), bg=BG, fg=TEXT2).pack(anchor="w", pady=(4, 0))

        sep(f).pack(fill="x", padx=30, pady=20)

        # Quick action cards row
        cards_row = tk.Frame(f, bg=BG); cards_row.pack(fill="x", padx=20, pady=(0, 16))

        quick_actions = [
            ("🔄", "Convert Files",   "PDF · DOCX · XLSX · PPTX · Images · Audio · Video",   "convert", ACCENT),
            ("🖼",  "Upscale Images",  "AI-quality upscaling up to 4×",                          "upscale", "#9b59b6"),
            ("✂️",  "Split Document",  "Break PDF or PPTX into pages/slides",                    "split",   ACCENT2),
            ("🔗", "Merge Files",     "Combine PDFs, images, presentations",                    "merge",   "#27ae60"),
            ("📐", "Organise PDF",    "Resequence · Delete · Rotate pages",                     "organise","#e67e22"),
            ("🔒", "Protect PDF",     "Encrypt or decrypt with password",                       "protect", "#c0392b"),
        ]

        for i, (icon, title, desc, tab, color) in enumerate(quick_actions):
            c2 = tk.Frame(cards_row, bg=CARD, padx=16, pady=14,
                          cursor="hand2")
            c2.grid(row=i//3, column=i%3, padx=8, pady=8, sticky="ew")
            cards_row.columnconfigure(i%3, weight=1)

            tk.Label(c2, text=icon, font=("Segoe UI", 24),
                     bg=CARD, fg=color).pack(anchor="w")
            tk.Label(c2, text=title,
                     font=("Segoe UI", 11, "bold"), bg=CARD, fg=TEXT).pack(anchor="w", pady=(4, 0))
            tk.Label(c2, text=desc, font=("Segoe UI", 9),
                     bg=CARD, fg=TEXT2, wraplength=200, justify="left").pack(anchor="w", pady=(2, 8))

            mk_btn(c2, f"Open {title.split()[0]} →",
                   lambda t=tab: self._switch_tab(t),
                   color, padx=10, pady=5).pack(anchor="w")

            # hover effect
            def on_enter(e, fr=c2): fr.config(bg=CARD2)
            def on_leave(e, fr=c2): fr.config(bg=CARD)
            c2.bind("<Enter>", on_enter); c2.bind("<Leave>", on_leave)

        sep(f).pack(fill="x", padx=30, pady=(4, 16))

        # File drop zone
        drop_zone = tk.Frame(f, bg=CARD, padx=24, pady=18)
        drop_zone.pack(fill="x", padx=20, pady=(0, 10))

        tk.Label(drop_zone, text="📥  Add files to get started",
                 font=("Segoe UI", 12, "bold"), bg=CARD, fg=TEXT).pack(side="left")
        tk.Label(drop_zone,
                 text="  Supports: PDF · Word · Excel · PowerPoint · CSV · Images · Audio · Video",
                 font=("Segoe UI", 9), bg=CARD, fg=TEXT2).pack(side="left", pady=4)

        btn_area = tk.Frame(drop_zone, bg=CARD); btn_area.pack(side="right")
        mk_big_btn(btn_area, "+ Add Files",   self._add_files,  ACCENT).pack(side="left", padx=(0, 8))
        mk_btn(btn_area,     "+ Add Folder",  self._add_folder, BORDER2).pack(side="left")

        # Currently loaded files preview
        self.home_files_frame = tk.Frame(f, bg=BG); self.home_files_frame.pack(fill="x", padx=20)
        self._refresh_home_files()

    def _refresh_home_files(self):
        for w in self.home_files_frame.winfo_children(): w.destroy()
        if not self.files: return
        tk.Label(self.home_files_frame, text=f"📋  {len(self.files)} file(s) loaded:",
                 font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT2).pack(anchor="w", padx=10, pady=(8, 4))
        row = tk.Frame(self.home_files_frame, bg=BG); row.pack(fill="x", padx=10)
        for fp in self.files[:8]:  # show max 8
            c2 = cat(fp)
            color = {"pdf": "#e74c3c", "image": "#9b59b6", "excel": "#27ae60",
                     "pptx": "#e67e22", "docx": "#2980b9", "audio": "#1abc9c",
                     "video": "#e91e8c", "csv": "#16a085"}.get(c2, BORDER2)
            pill = tk.Frame(row, bg=color, padx=8, pady=3)
            pill.pack(side="left", padx=(0, 6), pady=2)
            tk.Label(pill, text=f"{cat_icon(c2)}  {Path(fp).name[:22]}",
                     font=("Segoe UI", 8), bg=color, fg="#ffffff").pack()
        if len(self.files) > 8:
            tk.Label(row, text=f"  +{len(self.files)-8} more",
                     font=("Segoe UI", 8), bg=BG, fg=TEXT2).pack(side="left")

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
            row = tk.Frame(fmt_card, bg=PANEL); row.pack(fill="x", pady=3)
            lbl(row, f"{cat_name}:", dim=True, w=13).pack(side="left")
            for fmt in fmts:
                b = tk.Button(row, text=fmt.upper(), font=("Consolas", 9, "bold"),
                              bg=CARD2, fg=TEXT2, relief="flat",
                              padx=9, pady=4, cursor="hand2",
                              activebackground=ACCENT,
                              command=lambda f2=fmt: self._select_fmt(f2))
                b.pack(side="left", padx=3)
                self._fmt_btns[fmt] = b

        opt_card = card(f)
        lbl(opt_card, "OPTIONS", head=True).pack(anchor="w", pady=(0, 8))

        r1 = tk.Frame(opt_card, bg=PANEL); r1.pack(fill="x", pady=2)
        lbl(r1, "Pages (PDF/PPTX):", w=18).pack(side="left")
        self.conv_pages = tk.StringVar()
        entry(r1, self.conv_pages, width=22).pack(side="left", ipady=4, padx=(6, 6))
        lbl(r1, '"1,3,5-8" — blank = all', dim=True).pack(side="left")

        r2 = tk.Frame(opt_card, bg=PANEL); r2.pack(fill="x", pady=6)
        lbl(r2, "DPI (image export):", w=18).pack(side="left")
        self.conv_dpi = tk.StringVar(value="150")
        for val, label in [("72","72 draft"),("150","150 normal"),("300","300 print")]:
            tk.Radiobutton(r2, text=label, variable=self.conv_dpi, value=val,
                           font=F["small"], bg=PANEL, fg=TEXT2,
                           selectcolor=ACCENT, activebackground=PANEL,
                           cursor="hand2").pack(side="left", padx=(0, 14))

        self.conv_note = tk.Label(opt_card, text="", font=F["small"],
                                   bg=PANEL, fg=WARN, wraplength=580, justify="left")
        self.conv_note.pack(anchor="w", pady=(4, 0))

        # Now safe to set default
        self._select_fmt("pdf")

        btn_row = tk.Frame(f, bg=BG); btn_row.pack(pady=14)
        mk_big_btn(btn_row, "▶  RUN CONVERSION", self._run_convert).pack(side="left", padx=6)
        mk_btn(btn_row, "🤖 AI: Suggest Format", self._ai_suggest_format,
               ACCENT3, pady=10).pack(side="left", padx=6)

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
            font=F["small"], bg=PANEL, fg=TEXT2, wraplength=600, justify="left")
        self.upscale_info_lbl.pack(anchor="w")

        # Preview frame for first image
        self.upscale_preview_frame = tk.Frame(info_card, bg=PANEL)
        self.upscale_preview_frame.pack(anchor="w", pady=(6, 0))

        # Settings card
        settings_card = card(f)
        lbl(settings_card, "UPSCALE SETTINGS", head=True).pack(anchor="w", pady=(0, 12))

        # Scale factor
        scale_row = tk.Frame(settings_card, bg=PANEL); scale_row.pack(fill="x", pady=4)
        lbl(scale_row, "Scale factor:", w=16).pack(side="left")
        self.upscale_factor = tk.StringVar(value="2")
        for val, lbl_txt in [("1.5","1.5×"),("2","2×"),("3","3×"),("4","4×")]:
            tk.Radiobutton(scale_row, text=lbl_txt, variable=self.upscale_factor,
                           value=val, font=("Segoe UI", 10, "bold"),
                           bg=PANEL, fg=TEXT2,
                           selectcolor=ACCENT, activebackground=PANEL,
                           cursor="hand2").pack(side="left", padx=(0, 12))
        lbl(scale_row, "Custom:", w=8, dim=True).pack(side="left", padx=(12, 0))
        self.upscale_custom = tk.StringVar(value="")
        entry(scale_row, self.upscale_custom, width=5).pack(side="left", padx=(4, 0), ipady=4)
        lbl(scale_row, "× (overrides radio)", dim=True).pack(side="left", padx=(4, 0))

        # Method
        method_row = tk.Frame(settings_card, bg=PANEL); method_row.pack(fill="x", pady=6)
        lbl(method_row, "Algorithm:", w=16).pack(side="left")
        self.upscale_method = tk.StringVar(value="lanczos")
        method_cb = ttk.Combobox(method_row, textvariable=self.upscale_method,
                                  values=[m[0] for m in SCALE_METHODS],
                                  font=F["body"], width=14, state="readonly")
        method_cb.pack(side="left", padx=(0, 12))
        self.method_desc_lbl = tk.Label(method_row, text="",
                                         font=("Segoe UI", 9, "italic"),
                                         bg=PANEL, fg=TEXT2, wraplength=340)
        self.method_desc_lbl.pack(side="left")
        method_cb.bind("<<ComboboxSelected>>", self._update_method_desc)
        self._update_method_desc()

        # Sharpening
        sharp_row = tk.Frame(settings_card, bg=PANEL); sharp_row.pack(fill="x", pady=4)
        lbl(sharp_row, "Sharpness boost:", w=16).pack(side="left")
        self.upscale_sharpen = tk.StringVar(value="1.0")
        for val, label in [("1.0","None"),("1.3","Light"),("1.6","Medium"),("2.0","Strong")]:
            tk.Radiobutton(sharp_row, text=label, variable=self.upscale_sharpen,
                           value=val, font=F["small"],
                           bg=PANEL, fg=TEXT2,
                           selectcolor=ACCENT, activebackground=PANEL,
                           cursor="hand2").pack(side="left", padx=(0, 14))

        # Options row
        opts_row = tk.Frame(settings_card, bg=PANEL); opts_row.pack(fill="x", pady=4)
        lbl(opts_row, "Options:", w=16).pack(side="left")
        self.upscale_denoise = tk.BooleanVar(value=False)
        tk.Checkbutton(opts_row, text="Denoise before upscaling",
                        variable=self.upscale_denoise,
                        font=F["small"], bg=PANEL, fg=TEXT2,
                        selectcolor=ACCENT, activebackground=PANEL,
                        cursor="hand2").pack(side="left")

        # Output settings
        out_row = tk.Frame(settings_card, bg=PANEL); out_row.pack(fill="x", pady=(8, 0))
        lbl(out_row, "File suffix:", w=16).pack(side="left")
        self.upscale_suffix = tk.StringVar(value="_upscaled")
        entry(out_row, self.upscale_suffix, width=16).pack(side="left", ipady=4, padx=(6, 10))
        lbl(out_row, 'e.g.  photo_upscaled.png', dim=True).pack(side="left")

        # Progress bar
        self.upscale_progress_frame = tk.Frame(f, bg=BG)
        self.upscale_progress_frame.pack(fill="x", padx=14, pady=(0, 4))
        self.upscale_progress = ttk.Progressbar(self.upscale_progress_frame,
                                                  mode="determinate", length=400)
        self.upscale_progress_lbl = tk.Label(self.upscale_progress_frame,
                                              text="", font=F["small"], bg=BG, fg=TEXT2)

        btn_row = tk.Frame(f, bg=BG); btn_row.pack(pady=12)
        mk_big_btn(btn_row, "▶  UPSCALE IMAGES", self._run_upscale, "#9b59b6").pack(side="left", padx=6)
        mk_btn(btn_row, "🔍 Preview Info", self._upscale_preview_info,
               BORDER2, pady=10).pack(side="left", padx=6)
        mk_btn(btn_row, "🤖 AI Recommend", self._ai_upscale_recommend,
               ACCENT3, pady=10).pack(side="left", padx=6)

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
                                        font=F["small"], bg=PANEL, fg=TEXT2)
        self.split_info_lbl.pack(anchor="w", pady=(0, 4))
        for val, label in [("pdf","PDF — split pages"),("pptx","PPTX — split slides")]:
            tk.Radiobutton(tc, text=label, variable=self.split_type, value=val,
                           font=F["body"], bg=PANEL, fg=TEXT,
                           selectcolor=ACCENT2, activebackground=PANEL,
                           command=self._update_split_ui, cursor="hand2").pack(anchor="w", pady=2)

        mc = card(f)
        lbl(mc, "MODE", head=True).pack(anchor="w", pady=(0, 8))
        self.split_mode = tk.StringVar(value="each")
        for val, label, tip in [
            ("each",   "Each page/slide → own file",  "10-page PDF → 10 files"),
            ("range",  "Range → one file",             "Pages 3–8 → one PDF"),
            ("custom", "Custom groups (PDF only)",     "1,10 | 3,5 | 2-4,7"),
        ]:
            r = tk.Frame(mc, bg=PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.split_mode, value=val,
                           font=F["body"], bg=PANEL, fg=TEXT,
                           selectcolor=ACCENT2, activebackground=PANEL,
                           command=self._update_split_ui, cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")

        self.split_opts = card(f)
        self._update_split_ui()

        pr = tk.Frame(f, bg=BG); pr.pack(fill="x", padx=14, pady=2)
        lbl(pr, "File prefix:", w=12).pack(side="left")
        self.split_prefix = tk.StringVar(value="split")
        entry(pr, self.split_prefix, width=16).pack(side="left", padx=(6, 0), ipady=4)

        mk_big_btn(f, "▶  RUN SPLIT", self._run_split, ACCENT2).pack(pady=12)

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
            r = tk.Frame(tc, bg=PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.merge_type, value=val,
                           font=F["body"], bg=PANEL, fg=TEXT,
                           selectcolor=ACCENT, activebackground=PANEL,
                           cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")

        oc = card(f)
        r = tk.Frame(oc, bg=PANEL); r.pack(fill="x")
        lbl(r, "Output name:", w=14).pack(side="left")
        self.merge_name = tk.StringVar(value="merged_output")
        entry(r, self.merge_name, width=28).pack(side="left", padx=(6, 4), ipady=4)

        pc2 = card(f)
        lbl(pc2, "MERGE ORDER", head=True).pack(anchor="w", pady=(0, 6))
        self.merge_preview = tk.Text(pc2, height=7, font=F["mono_sm"],
                                      bg=LOG_BG, fg=TEXT2,
                                      relief="flat", state="disabled", bd=0)
        self.merge_preview.pack(fill="x")
        mk_btn(pc2, "↻ Refresh", self._refresh_merge_preview, BORDER2).pack(anchor="w", pady=(6, 0))

        mk_big_btn(f, "▶  RUN MERGE", self._run_merge).pack(pady=12)

    def _build_organise_page(self):
        f = self.pages["organise"]
        section_hdr(f, "ORGANISE PDF", "Resequence · Delete · Rotate · Reverse pages")

        self.org_lbl_var = tk.StringVar(value="No PDF loaded — add one to the queue")
        ic = card(f)
        tk.Label(ic, textvariable=self.org_lbl_var, font=F["small"],
                 bg=PANEL, fg=SUCCESS).pack(anchor="w")

        oc = card(f)
        lbl(oc, "OPERATION", head=True).pack(anchor="w", pady=(0, 8))
        self.org_op = tk.StringVar(value="resequence")
        for val, label, tip in [
            ("resequence", "Resequence", "Custom order e.g. 3,1,2"),
            ("delete",     "Delete pages","Remove pages e.g. 2,5,7-9"),
            ("rotate",     "Rotate pages","90/180/270° on selected pages"),
            ("reverse",    "Reverse",     "Flip entire page order"),
        ]:
            r = tk.Frame(oc, bg=PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.org_op, value=val,
                           font=F["body"], bg=PANEL, fg=TEXT,
                           selectcolor=ACCENT, activebackground=PANEL,
                           command=self._update_org_ui, cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")

        self.org_opts = card(f)
        self._update_org_ui()

        row = tk.Frame(f, bg=BG); row.pack(fill="x", padx=14, pady=2)
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
                           font=F["body"], bg=PANEL, fg=TEXT,
                           selectcolor=ACCENT, activebackground=PANEL,
                           command=self._update_stamp_ui, cursor="hand2").pack(anchor="w", pady=2)
        self.stamp_opts = card(f); self._update_stamp_ui()

        pc2 = card(f)
        r = tk.Frame(pc2, bg=PANEL); r.pack(fill="x")
        lbl(r, "Pages (blank=all):", w=18).pack(side="left")
        self.stamp_pages = tk.StringVar()
        entry(r, self.stamp_pages, width=22).pack(side="left", padx=(6, 0), ipady=4)

        row = tk.Frame(f, bg=BG); row.pack(fill="x", padx=14, pady=2)
        lbl(row, "Output name:", w=14).pack(side="left")
        self.stamp_out_name = tk.StringVar(value="stamped")
        entry(row, self.stamp_out_name, width=22).pack(side="left", padx=(6, 4), ipady=4)
        lbl(row, ".pdf", dim=True).pack(side="left")
        mk_big_btn(f, "▶  RUN STAMP", self._run_stamp, ACCENT2).pack(pady=12)

    def _build_protect_page(self):
        f = self.pages["protect"]
        section_hdr(f, "PROTECT / DECRYPT", "Password-protect or unlock a PDF")
        mc = card(f)
        self.protect_mode = tk.StringVar(value="encrypt")
        for val, label, tip in [
            ("encrypt","Encrypt (add password)","Lock with password"),
            ("decrypt","Decrypt (remove password)","Requires current password"),
        ]:
            r = tk.Frame(mc, bg=PANEL); r.pack(anchor="w", pady=2)
            tk.Radiobutton(r, text=label, variable=self.protect_mode, value=val,
                           font=F["body"], bg=PANEL, fg=TEXT,
                           selectcolor=ACCENT, activebackground=PANEL,
                           cursor="hand2").pack(side="left")
            lbl(r, f"  — {tip}", dim=True).pack(side="left")
        pc2 = card(f)
        lbl(pc2, "PASSWORD", head=True).pack(anchor="w", pady=(0, 8))
        for label, attr in [("User password:","protect_pw1"),("Owner password (opt.):","protect_pw2")]:
            r = tk.Frame(pc2, bg=PANEL); r.pack(fill="x", pady=3)
            lbl(r, label, w=22).pack(side="left")
            var = tk.StringVar(); setattr(self, attr, var)
            entry(r, var, width=24, show="•").pack(side="left", padx=(6, 0), ipady=4)
        row = tk.Frame(f, bg=BG); row.pack(fill="x", padx=14, pady=2)
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
        row = tk.Frame(f, bg=BG); row.pack(fill="x", padx=14, pady=10)
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
                                     bg=LOG_BG, fg=TEXT, relief="flat",
                                     state="disabled", bd=0)
        self.meta_display.pack(fill="x")
        br = tk.Frame(vc, bg=PANEL); br.pack(anchor="w", pady=(6, 0))
        mk_btn(br, "↻ Load", self._load_metadata, BORDER2).pack(side="left", padx=(0, 6))
        mk_btn(br, "🤖 AI Analyse", self._ai_analyse_metadata, ACCENT3).pack(side="left")
        ec = card(f)
        lbl(ec, "EDIT FIELDS", head=True).pack(anchor="w", pady=(0, 8))
        self.meta_fields: Dict[str, tk.StringVar] = {}
        for field in ["Title","Author","Subject","Creator"]:
            r = tk.Frame(ec, bg=PANEL); r.pack(fill="x", pady=3)
            lbl(r, field+":", w=10).pack(side="left")
            var = tk.StringVar(); self.meta_fields[field.lower()] = var
            entry(r, var, width=38).pack(side="left", padx=(6, 0), ipady=4)
        row = tk.Frame(f, bg=BG); row.pack(fill="x", padx=14, pady=2)
        lbl(row, "Output name:", w=14).pack(side="left")
        self.meta_out = tk.StringVar(value="updated_metadata")
        entry(row, self.meta_out, width=22).pack(side="left", padx=(6, 4), ipady=4)
        lbl(row, ".pdf", dim=True).pack(side="left")
        mk_big_btn(f, "▶  SAVE METADATA", self._run_metadata).pack(pady=12)

    def _build_queue_page(self):
        f = self.pages["queue"]
        section_hdr(f, "FILE QUEUE", "Manage staged files — double-click to set AI context file")
        lf = tk.Frame(f, bg=PANEL); lf.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.queue_lb = tk.Listbox(lf, font=F["body"],
                                    bg=CARD2, fg=TEXT,
                                    selectbackground=ACCENT,
                                    activestyle="none", relief="flat", bd=0,
                                    selectmode="extended")
        sb2 = tk.Scrollbar(lf, orient="vertical", command=self.queue_lb.yview)
        self.queue_lb.config(yscrollcommand=sb2.set)
        self.queue_lb.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")
        self.queue_lb.bind("<Double-Button-1>", self._queue_select_for_ai)
        br = tk.Frame(f, bg=BG); br.pack(fill="x", padx=12, pady=(0, 4))
        for label, cmd in [("↑ Up",self._move_up),("↓ Down",self._move_down),
                            ("✖ Remove",self._remove_selected),("🗑 Clear",self._clear_queue)]:
            mk_btn(br, label, cmd, BORDER2).pack(side="left", padx=(0, 6))
        mk_btn(br, "🤖 AI Analyse Selected", self._ai_analyse_selected,
               ACCENT3).pack(side="right")

    # ══════════════════════════════════════════════════════════════════════════
    # DYNAMIC SUB-UIs
    # ══════════════════════════════════════════════════════════════════════════

    def _update_split_ui(self):
        for w in self.split_opts.winfo_children(): w.destroy()
        mode = self.split_mode.get(); f = self.split_opts
        if mode == "each":
            lbl(f, "Every page/slide becomes its own numbered file.").pack(anchor="w")
        elif mode == "range":
            r = tk.Frame(f, bg=PANEL); r.pack(anchor="w")
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
            r = tk.Frame(f, bg=PANEL); r.pack(fill="x", pady=2)
            lbl(r, "Degrees:", w=10).pack(side="left")
            self.org_rotate_deg = tk.StringVar(value="90")
            for d in ["90","180","270"]:
                tk.Radiobutton(r, text=d+"°", variable=self.org_rotate_deg, value=d,
                               font=F["btn"], bg=PANEL, fg=TEXT2,
                               selectcolor=ACCENT, activebackground=PANEL,
                               cursor="hand2").pack(side="left", padx=(0,12))
            r2 = tk.Frame(f, bg=PANEL); r2.pack(fill="x", pady=(4,0))
            lbl(r2, "Pages (blank=all):", w=18).pack(side="left")
            self.org_rotate_pages = tk.StringVar(value="")
            entry(r2, self.org_rotate_pages, width=22).pack(side="left", padx=(6,0), ipady=4)
        elif op == "reverse":
            lbl(f, "Entire page order will be reversed.").pack(anchor="w")

    def _update_stamp_ui(self):
        for w in self.stamp_opts.winfo_children(): w.destroy()
        mode = self.stamp_mode.get(); f = self.stamp_opts
        if mode == "text":
            lbl(f, "TEXT WATERMARK", head=True).pack(anchor="w", pady=(0,8))
            for label, attr, default in [
                ("Watermark text:","stamp_text","CONFIDENTIAL"),
                ("Font size:",     "stamp_size","48"),
                ("Color (hex):",   "stamp_color","#888888"),
                ("Opacity (0–1):","stamp_opacity","0.3"),
                ("Angle (°):",    "stamp_angle","45"),
            ]:
                r = tk.Frame(f, bg=PANEL); r.pack(fill="x", pady=2)
                lbl(r, label, w=18).pack(side="left")
                var = tk.StringVar(value=default); setattr(self, attr, var)
                entry(r, var, width=22).pack(side="left", padx=(6,0), ipady=4)
        else:
            lbl(f, "PDF OVERLAY", head=True).pack(anchor="w", pady=(0,8))
            r = tk.Frame(f, bg=PANEL); r.pack(fill="x")
            self.stamp_wm_path = tk.StringVar(value="")
            entry(r, self.stamp_wm_path, width=36).pack(side="left", fill="x", expand=True, ipady=4, padx=(0,6))
            mk_btn(r, "Browse", self._browse_stamp_pdf, BORDER2).pack(side="left")

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
            self.after(300, self._open_output)
        threading.Thread(target=task, daemon=True).start()

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
            self.after(300, self._open_output)

        threading.Thread(target=task, daemon=True).start()

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
                         font=("Consolas", 9), bg=PANEL, fg=TEXT2).pack(anchor="w")
        self.upscale_info_lbl.config(
            text=f"{len(images)} image(s) ready to upscale.", fg=SUCCESS)

    def _run_split(self):
        out = self._require_out()
        if not out: return
        stype = self.split_type.get(); mode = self.split_mode.get()
        prefix = self.split_prefix.get().strip() or "split"
        if stype == "pptx":
            pptxs = [f for f in self.files if cat(f) == "pptx"]
            if not pptxs: messagebox.showwarning("No PPTX","Add a PPTX first."); return
            src = pptxs[0]
            def task():
                try:
                    files = pptx_split_slides(src, out, prefix)
                    self._log(f"✔ {len(files)} slide files created.", "ok")
                    self.after(300, self._open_output)
                except Exception as ex: self._log(f"ERROR: {ex}", "err")
            threading.Thread(target=task, daemon=True).start(); return
        src = self._require_pdf("Split")
        if not src: return
        def task():
            try:
                if mode == "each":
                    files = split_each(src, out, prefix)
                    self._log(f"✔ {len(files)} files.", "ok")
                elif mode == "range":
                    try: s,e = int(self.range_start.get()), int(self.range_end.get())
                    except: self._log("⚠ Invalid range.", "err"); return
                    p = split_range(src, s, e, out, prefix)
                    self._log(f"✔ {Path(p).name}", "ok")
                elif mode == "custom":
                    groups = parse_groups(self.custom_groups.get(), self.page_count or 9999)
                    if not groups: self._log("⚠ No valid groups.", "err"); return
                    files = split_custom(src, groups, out, prefix)
                    for fp in files: self._log(f"  → {Path(fp).name}")
                    self._log(f"✔ {len(files)} files.", "ok")
                self.after(300, self._open_output)
            except Exception as ex: self._log(f"ERROR: {ex}", "err")
        threading.Thread(target=task, daemon=True).start()

    def _run_merge(self):
        if not self.files: messagebox.showwarning("Merge","Add files first."); return
        out = self._require_out()
        if not out: return
        mtype = self.merge_type.get()
        dst = os.path.join(out, (self.merge_name.get().strip() or "merged_output") + "." + mtype)
        srcs = list(self.files)
        def task():
            try:
                merge_pdfs(srcs, dst) if mtype == "pdf" else pptx_merge(srcs, dst)
                self._log(f"✔ {Path(dst).name}  ({os.path.getsize(dst)/1024:.1f} KB)", "ok")
                self.after(300, self._open_output)
            except Exception as ex: self._log(f"ERROR: {ex}", "err")
        threading.Thread(target=task, daemon=True).start()

    def _run_organise(self):
        src = self._require_pdf("Organise"); out = self._require_out()
        if not src or not out: return
        op = self.org_op.get()
        dst = os.path.join(out, (self.org_out_name.get().strip() or "organised") + ".pdf")
        pc = self.page_count or pdf_page_count(src)
        def task():
            try:
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
                self.after(300, self._open_output)
            except Exception as ex: self._log(f"ERROR: {ex}", "err")
        threading.Thread(target=task, daemon=True).start()

    def _run_stamp(self):
        src = self._require_pdf("Stamp"); out = self._require_out()
        if not src or not out: return
        mode = self.stamp_mode.get()
        dst = os.path.join(out, (self.stamp_out_name.get().strip() or "stamped") + ".pdf")
        pc = self.page_count or pdf_page_count(src)
        pstr = self.stamp_pages.get().strip()
        pages = parse_pages(pstr, pc) if pstr else None
        def task():
            try:
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
                self.after(300, self._open_output)
            except Exception as ex: self._log(f"ERROR: {ex}", "err")
        threading.Thread(target=task, daemon=True).start()

    def _run_protect(self):
        src = self._require_pdf("Protect"); out = self._require_out()
        if not src or not out: return
        mode = self.protect_mode.get()
        pw1 = self.protect_pw1.get(); pw2 = self.protect_pw2.get()
        dst = os.path.join(out, (self.protect_out.get().strip() or "protected") + ".pdf")
        def task():
            try:
                if mode == "encrypt":
                    if not pw1: self._log("⚠ Enter a password.", "err"); return
                    encrypt_pdf(src, dst, pw1, pw2)
                else:
                    if not pw1: self._log("⚠ Enter the password.", "err"); return
                    decrypt_pdf(src, dst, pw1)
                self._log(f"✔ {Path(dst).name}", "ok")
                self.after(300, self._open_output)
            except Exception as ex: self._log(f"ERROR: {ex}", "err")
        threading.Thread(target=task, daemon=True).start()

    def _run_compress(self):
        src = self._require_pdf("Compress"); out = self._require_out()
        if not src or not out: return
        dst = os.path.join(out, (self.compress_out.get().strip() or "compressed") + ".pdf")
        def task():
            try:
                before = os.path.getsize(src)/1024
                compress_pdf(src, dst)
                after = os.path.getsize(dst)/1024
                self._log(f"✔ {Path(dst).name}  ({after:.1f} KB)  saved {before-after:.1f} KB", "ok")
                self.after(300, self._open_output)
            except Exception as ex: self._log(f"ERROR: {ex}", "err")
        threading.Thread(target=task, daemon=True).start()

    def _run_metadata(self):
        src = self._require_pdf("Metadata"); out = self._require_out()
        if not src or not out: return
        dst = os.path.join(out, (self.meta_out.get().strip() or "updated") + ".pdf")
        fields = {k: v.get() for k, v in self.meta_fields.items()}
        def task():
            try:
                set_metadata(src, dst, fields)
                self._log(f"✔ Metadata saved: {Path(dst).name}", "ok")
                self.after(300, self._open_output)
            except Exception as ex: self._log(f"ERROR: {ex}", "err")
        threading.Thread(target=task, daemon=True).start()

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
            self._ai_sys("⚠  AI not configured. Open ⚙ Settings and enter your Gemini API key.")
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
            self.chat_input.config(fg=TEXT)
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

    def _ai_response(self, text: str, check_intent: bool = False):
        self.after(0, lambda: self._display_ai(text, check_intent))

    def _display_ai(self, text: str, check_intent: bool = False):
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", "🤖  AI\n", "ai_lbl")
        self.chat_display.insert("end", text + "\n\n", "ai_msg")
        self.chat_display.insert("end", "─"*44+"\n", "divider")
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")
        self._log(f"AI responded ({len(text)} chars)", "ai")
        if check_intent:
            from ai.gemini import _extract_json
            intent = _extract_json(text)
            if intent and intent.get("action") not in (None, "chat", "unknown"):
                self._apply_intent(intent)

    def _apply_intent(self, intent: dict):
        action = intent.get("action",""); fmt = intent.get("format"); msg = intent.get("message","")
        if msg: self._ai_sys(f"🎯 Intent detected: {msg}")
        if action == "convert" and fmt:
            self._select_fmt(fmt); self._switch_tab("convert")
        elif action in ("split","merge","compress","protect","organise","stamp","metadata"):
            self._switch_tab(action)

    def _ai_error(self, msg: str):
        def _do():
            self.chat_display.config(state="normal")
            self.chat_display.insert("end", f"⚠  Error: {msg}\n\n", "err_msg")
            self.chat_display.see("end")
            self.chat_display.config(state="disabled")
        self.after(0, _do)

    def _ai_user(self, text: str):
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", "👤  You\n", "user_lbl")
        self.chat_display.insert("end", text + "\n\n", "user_msg")
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")

    def _ai_sys(self, text: str):
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", text + "\n\n", "sys_msg")
        self.chat_display.see("end")
        self.chat_display.config(state="disabled")

    def _clear_chat(self):
        self.chat_display.config(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.config(state="disabled")
        self.ai.reset_chat()
        self._ai_sys("Chat cleared. New session started.")

    def _set_ai_mode(self, val: str, init=False):
        self.ai_mode.set(val)
        for v, b in self._mode_btns.items():
            if v == val: b.config(bg=ACCENT3, fg="#ffffff")
            else:        b.config(bg=CARD2, fg=TEXT2)
        if not init:
            needs_file = val in ("qa","summarise")
            if needs_file: self.ai_file_frame.pack(fill="x", padx=10, pady=(0,4))
            else:          self.ai_file_frame.pack_forget()

    # ══════════════════════════════════════════════════════════════════════════
    # PLACEHOLDER  — uses a flag to avoid content/placeholder confusion
    # ══════════════════════════════════════════════════════════════════════════

    def _set_placeholder(self):
        """Show placeholder hint text in the input box."""
        self.chat_input.delete("1.0", "end")
        self.chat_input.config(fg="#555577")
        self.chat_input.insert("1.0", self._placeholder)
        self._placeholder_active = True

    def _clear_placeholder(self, _=None):
        """Remove placeholder when user focuses the input."""
        if self._placeholder_active:
            self.chat_input.delete("1.0", "end")
            self.chat_input.config(fg=TEXT)
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
        win.configure(bg=BG)
        win.geometry("600x520")
        win.resizable(False, False)
        win.transient(self); win.grab_set()

        hdr = tk.Frame(win, bg=SIDEBAR, pady=14); hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  SETTINGS", font=("Segoe UI", 14, "bold"),
                 bg=SIDEBAR, fg=ACCENT).pack(side="left", padx=20)

        c2 = tk.Frame(win, bg=PANEL, padx=24, pady=18)
        c2.pack(fill="x", padx=18, pady=(16, 0))
        tk.Label(c2, text="🤖  GEMINI API KEY",
                 font=("Segoe UI", 11, "bold"), bg=PANEL, fg=ACCENT3).pack(anchor="w", pady=(0,12))

        guide_box = tk.Frame(c2, bg=CARD2, padx=14, pady=10)
        guide_box.pack(fill="x", pady=(0,14))
        tk.Label(guide_box, text="How to get your FREE Gemini API key:",
                 font=("Segoe UI", 9, "bold"), bg=CARD2, fg=TEXT).pack(anchor="w")
        for step in ["1.  Go to  https://aistudio.google.com/app/apikey",
                     "2.  Sign in with your Google account",
                     "3.  Click  'Create API key'  and copy it",
                     "4.  Paste below and click  Save & Apply"]:
            tk.Label(guide_box, text=step, font=("Consolas", 9),
                     bg=CARD2, fg=TEXT2).pack(anchor="w")

        tk.Label(c2, text="API Key:", font=("Segoe UI", 10, "bold"),
                 bg=PANEL, fg=TEXT).pack(anchor="w", pady=(0,4))
        key_row = tk.Frame(c2, bg=PANEL); key_row.pack(fill="x", pady=(0,6))
        key_var = tk.StringVar(value=self.cfg.get("gemini_api_key",""))
        key_entry = tk.Entry(key_row, textvariable=key_var,
                              font=("Consolas", 11),
                              bg=CARD2, fg=TEXT, insertbackground=TEXT,
                              show="•", relief="flat", bd=0, width=42)
        key_entry.pack(side="left", ipady=8, padx=(0,8))
        key_entry.focus_set()
        show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(key_row, text="Show", variable=show_var,
                        command=lambda: key_entry.config(show="" if show_var.get() else "•"),
                        font=("Segoe UI",9), bg=PANEL, fg=TEXT2,
                        selectcolor=ACCENT, activebackground=PANEL,
                        cursor="hand2").pack(side="left")

        tk.Label(c2, text="Model:", font=("Segoe UI", 10, "bold"),
                 bg=PANEL, fg=TEXT).pack(anchor="w", pady=(10,4))
        model_var = tk.StringVar(value=self.cfg.get("gemini_model","gemini-1.5-flash"))
        model_row = tk.Frame(c2, bg=PANEL); model_row.pack(fill="x", pady=(0,4))
        for m in GEMINI_MODELS:
            tk.Radiobutton(model_row, text=m, variable=model_var, value=m,
                           font=("Consolas",10), bg=PANEL, fg=TEXT,
                           selectcolor=ACCENT3, activebackground=PANEL,
                           cursor="hand2").pack(side="left", padx=(0,16))
        model_descs = {"gemini-1.5-flash":"⚡ Fast & efficient",
                       "gemini-1.5-pro":"🧠 Powerful analysis",
                       "gemini-2.0-flash":"🚀 Latest & fastest"}
        mdl = tk.Label(c2, text=model_descs.get(model_var.get(),""),
                        font=("Segoe UI",9,"italic"), bg=PANEL, fg=TEXT2)
        mdl.pack(anchor="w")
        model_var.trace_add("write", lambda *_: mdl.config(text=model_descs.get(model_var.get(),"")))

        status_lbl = tk.Label(win, text="", font=("Segoe UI",10), bg=BG, fg=SUCCESS)
        status_lbl.pack(anchor="w", padx=20, pady=(12,0))

        def save():
            key = key_var.get().strip(); model = model_var.get()
            self.cfg["gemini_api_key"] = key; self.cfg["gemini_model"] = model
            self.cfg["output_dir"] = self.out_dir.get()
            save_config(self.cfg)
            if key:
                self.ai.reconfigure(key, model); self._update_ai_status()
                status_lbl.config(text="✔  Saved! AI is now active.", fg=SUCCESS)
                self._ai_sys(f"✔ AI configured with model: {model}")
                win.after(1200, win.destroy)
            else:
                status_lbl.config(text="⚠  No API key — AI features disabled", fg=WARN)

        def test():
            key = key_var.get().strip()
            if not key: status_lbl.config(text="⚠  Paste your API key first", fg=WARN); return
            status_lbl.config(text="⏳  Testing …", fg=TEXT2)
            tmp = GeminiClient(key, model_var.get())
            if tmp.is_ready:
                tmp.chat("Reply with exactly: Connection OK",
                          on_done=lambda r: status_lbl.config(text=f"✔  {r.strip()[:80]}", fg=SUCCESS),
                          on_error=lambda e: status_lbl.config(text=f"✖  {e}", fg=ERROR))
            else:
                status_lbl.config(text=f"✖  {tmp.error}", fg=ERROR)

        bf = tk.Frame(win, bg=BG); bf.pack(fill="x", padx=18, pady=(8,16))
        tk.Button(bf, text="💾  Save & Apply", command=save,
                  font=("Segoe UI",11,"bold"), bg=ACCENT, fg="#fff",
                  activebackground=BORDER2, relief="flat",
                  cursor="hand2", padx=18, pady=9, bd=0).pack(side="left", padx=(0,10))
        tk.Button(bf, text="🔌  Test Connection", command=test,
                  font=("Segoe UI",10,"bold"), bg=ACCENT3, fg="#fff",
                  activebackground=BORDER2, relief="flat",
                  cursor="hand2", padx=14, pady=9, bd=0).pack(side="left", padx=(0,10))
        tk.Button(bf, text="Cancel", command=win.destroy,
                  font=("Segoe UI",10), bg=BORDER2, fg=TEXT,
                  activebackground=BORDER, relief="flat",
                  cursor="hand2", padx=14, pady=9, bd=0).pack(side="left")

        lf2 = tk.Frame(win, bg=BG); lf2.pack(anchor="w", padx=20)
        tk.Label(lf2, text="Get API key: ", font=("Segoe UI",9), bg=BG, fg=TEXT2).pack(side="left")
        link = tk.Label(lf2, text="https://aistudio.google.com/app/apikey",
                         font=("Segoe UI",9,"underline"), bg=BG, fg=C["info"], cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: self._open_url("https://aistudio.google.com/app/apikey"))

    def _open_url(self, url):
        import webbrowser; webbrowser.open(url)

    # ══════════════════════════════════════════════════════════════════════════
    # FILE QUEUE MANAGEMENT
    # ══════════════════════════════════════════════════════════════════════════

    def _add_files(self):
        all_exts = ("*.pdf *.docx *.xlsx *.xls *.xlsm *.pptx *.ppt *.csv *.tsv "
                    "*.txt *.html *.htm "
                    "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.ico "
                    "*.mp4 *.avi *.mov *.mkv *.webm *.mp3 *.wav *.ogg *.flac *.aac *.m4a")
        paths = filedialog.askopenfilenames(
            title="Select files",
            filetypes=[("All supported", all_exts),
                       ("PDF","*.pdf"), ("Excel","*.xlsx *.xls *.xlsm *.ods"),
                       ("PowerPoint","*.pptx *.ppt"), ("CSV","*.csv *.tsv"),
                       ("Word","*.docx"),
                       ("Images","*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.ico"),
                       ("Audio","*.mp3 *.wav *.ogg *.flac *.aac *.m4a"),
                       ("Video","*.mp4 *.avi *.mov *.mkv *.webm"),
                       ("All files","*.*")])
        for p in paths:
            if p not in self.files:
                self.files.append(p); c2 = cat(p)
                self.queue_lb.insert("end", f"  {cat_icon(c2)}  {Path(p).name}  [{c2}]")
        self._update_after_files()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Add all files from folder")
        if not folder: return
        exts = IMAGE_EXTS|AUDIO_EXTS|VIDEO_EXTS|EXCEL_EXTS|PPTX_EXTS|CSV_EXTS|{".pdf",".docx",".txt",".html",".htm"}
        added = 0
        for path in sorted(Path(folder).iterdir()):
            if path.suffix.lower() in exts and str(path) not in self.files:
                self.files.append(str(path)); c2 = cat(str(path))
                self.queue_lb.insert("end", f"  {cat_icon(c2)}  {path.name}  [{c2}]")
                added += 1
        self._log(f"Added {added} file(s) from folder.")
        self._update_after_files()

    def _update_after_files(self):
        n = len(self.files)
        self._status(f"{n} file(s) in queue")
        if not self.out_dir.get() and self.files:
            self.out_dir.set(str(Path(self.files[0]).parent/"workshop_output"))
        pdfs = [f for f in self.files if cat(f)=="pdf"]
        if pdfs and HAS_PYPDF:
            try:
                pc = pdf_page_count(pdfs[0]); self.page_count = pc; self.active_pdf = pdfs[0]
                name = Path(pdfs[0]).name
                self.file_badge.config(text=f"📄 {name}\n   {pc} pages", fg=SUCCESS)
                self.split_info_lbl.config(text=f"Active PDF: {name} · {pc} pages", fg=SUCCESS)
                self.org_lbl_var.set(f"Active PDF: {name}  ·  {pc} pages")
            except: pass
        pptxs = [f for f in self.files if cat(f)=="pptx"]
        if pptxs and HAS_PPTX:
            try:
                sc = pptx_slide_count(pptxs[0])
                self.split_info_lbl.config(
                    text=f"Active PPTX: {Path(pptxs[0]).name} · {sc} slides", fg=SUCCESS)
            except: pass
        images = [f for f in self.files if cat(f)=="image"]
        if images:
            self.upscale_info_lbl.config(
                text=f"{len(images)} image(s) ready to upscale. Click 'Preview Info' to inspect.",
                fg=SUCCESS)
        if n > 0:
            self.file_badge.config(text=f"{n} file(s) loaded", fg=TEXT2)
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
            for i,fp in enumerate(self.files,1):
                self.merge_preview.insert("end",f"  {i:2d}.  {cat_icon(cat(fp))}  {Path(fp).name}\n")
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
        for i in reversed(sel): self.files.pop(i); self.queue_lb.delete(i)
        self._update_after_files()

    def _clear_queue(self):
        self.files.clear(); self.queue_lb.delete(0,"end")
        self.page_count=0; self.active_pdf=""
        self.file_badge.config(text="No files loaded",fg=TEXT2)
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

    def _select_fmt(self, fmt: str):
        self.out_fmt.set(fmt)
        for f2, b in self._fmt_btns.items():
            b.config(bg=ACCENT if f2==fmt else CARD2,
                     fg="#ffffff" if f2==fmt else TEXT2)
        notes = {
            "png": "" if HAS_PDF2IMAGE else "⚠  pip install pdf2image  +  sudo apt install poppler-utils",
            "jpg": "" if HAS_PDF2IMAGE else "⚠  pip install pdf2image  +  sudo apt install poppler-utils",
            "docx": "" if HAS_DOCX else "⚠  pip install python-docx",
            "xlsx": "" if HAS_OPENPYXL else "⚠  pip install openpyxl",
            "pptx": "" if HAS_PPTX else "⚠  pip install python-pptx",
            "mp3":  "" if HAS_FFMPEG else "⚠  sudo apt install ffmpeg",
            "mp4":  "" if HAS_FFMPEG else "⚠  sudo apt install ffmpeg",
        }
        if hasattr(self,"conv_note"):
            self.conv_note.config(text=notes.get(fmt,""))

    def _switch_tab(self, key: str):
        for k, b in self.tab_btns.items():
            b.config(bg=ACCENT if k==key else SIDEBAR,
                     fg="#ffffff" if k==key else TEXT2)
        for k, page in self.pages.items(): page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        if key=="merge": self._refresh_merge_preview()

    def _update_ai_status(self):
        if self.ai.is_ready:
            model = self.cfg.get("gemini_model","?")
            self.ai_status_lbl.config(text=f"🟢 AI: {model}", fg=SUCCESS)
        elif not HAS_GENAI:
            self.ai_status_lbl.config(text="🔴 AI: pip install google-genai", fg=ERROR)
        else:
            self.ai_status_lbl.config(text="⚪ AI: open ⚙ to configure", fg=TEXT2)

    def _log(self, msg: str, kind: str = ""):
        def _do():
            self.log_box.config(state="normal")
            tag={"ok":"ok","err":"err","info":"info","warn":"warn","ai":"ai"}.get(kind,"")
            self.log_box.insert("end","  "+msg+"\n",tag)
            self.log_box.see("end"); self.log_box.config(state="disabled")
        self.after(0,_do)

    def _clear_log(self):
        self.log_box.config(state="normal"); self.log_box.delete("1.0","end")
        self.log_box.config(state="disabled")

    def _status(self, msg: str):
        self.after(0, lambda: self.status_var.set("  "+msg))

    def _refresh_deps(self):
        deps=[HAS_PYPDF,HAS_PDFPLUMBER,HAS_DOCX,HAS_PIL,
              HAS_PDF2IMAGE,HAS_FFMPEG,HAS_OPENPYXL,HAS_PPTX,HAS_LIBREOFFICE]
        n=sum(deps)
        self.dep_lbl.config(text=f"deps {n}/{len(deps)} ✓",
                             fg=SUCCESS if n==len(deps) else WARN)
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
