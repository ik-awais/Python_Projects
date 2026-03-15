"""
File Workshop — Universal Local Converter & PDF Toolkit
========================================================
Supports:
  PDF      → docx, txt, png, jpg, html
  Images   → png, jpg, webp, bmp, gif, tiff, ico, pdf
  Word     → pdf, txt, html
  Text     → pdf, html, docx
  Video    → mp4, avi, mov, mkv, webm, gif, mp3, wav (via ffmpeg)
  Audio    → mp3, wav, ogg, flac, aac, m4a (via ffmpeg)
  HTML     → pdf, txt

PDF TOOLS (dedicated tab):
  Split every page | Range | Custom groups

Requirements: see requirements.txt
"""

import os
import sys
import threading
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# ─── Optional dependency flags ────────────────────────────────────────────────

def _try(pkg):
    try:
        __import__(pkg)
        return True
    except ImportError:
        return False

HAS_PYPDF       = _try("pypdf")
HAS_PDFPLUMBER  = _try("pdfplumber")
HAS_DOCX        = _try("docx")
HAS_PIL         = _try("PIL")
HAS_PDF2IMAGE   = _try("pdf2image")
HAS_FFMPEG      = shutil.which("ffmpeg") is not None
HAS_WEASYPRINT  = _try("weasyprint")

if HAS_PYPDF:
    from pypdf import PdfReader, PdfWriter
if HAS_PDFPLUMBER:
    import pdfplumber
if HAS_DOCX:
    from docx import Document
if HAS_PIL:
    from PIL import Image
if HAS_PDF2IMAGE:
    from pdf2image import convert_from_path

# ─── Conversion Matrix ────────────────────────────────────────────────────────
# Maps (input_category, output_ext) → function name

IMAGE_EXTS  = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif", ".ico"}
AUDIO_EXTS  = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".wma"}
VIDEO_EXTS  = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
DOC_EXTS    = {".pdf", ".docx", ".txt", ".html", ".htm"}

def categorize(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTS:  return "image"
    if ext in AUDIO_EXTS:  return "audio"
    if ext in VIDEO_EXTS:  return "video"
    if ext == ".pdf":      return "pdf"
    if ext == ".docx":     return "docx"
    if ext in {".txt"}:    return "txt"
    if ext in {".html", ".htm"}: return "html"
    return "unknown"

# ─── Available output formats per input ───────────────────────────────────────

FORMAT_MAP = {
    "pdf":   ["txt", "docx", "png", "jpg", "html"],
    "docx":  ["pdf", "txt", "html"],
    "txt":   ["pdf", "docx", "html"],
    "html":  ["pdf", "txt"],
    "image": ["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff", "ico", "pdf"],
    "audio": ["mp3", "wav", "ogg", "flac", "aac", "m4a"],
    "video": ["mp4", "avi", "mov", "mkv", "webm", "gif", "mp3", "wav"],
}

NEEDS = {
    # (in_cat, out_ext): list of requirement strings
    ("pdf",   "txt"):   ["pdfplumber"],
    ("pdf",   "docx"):  ["pdfplumber", "python-docx"],
    ("pdf",   "png"):   ["pdf2image", "poppler"],
    ("pdf",   "jpg"):   ["pdf2image", "poppler"],
    ("pdf",   "html"):  ["pdfplumber"],
    ("docx",  "pdf"):   ["libreoffice OR docx2pdf"],
    ("docx",  "txt"):   ["python-docx"],
    ("docx",  "html"):  ["python-docx"],
    ("txt",   "pdf"):   ["reportlab"],
    ("txt",   "docx"):  ["python-docx"],
    ("txt",   "html"):  [],
    ("html",  "pdf"):   ["weasyprint OR wkhtmltopdf"],
    ("html",  "txt"):   [],
    ("image", "pdf"):   ["Pillow"],
    ("image", "*"):     ["Pillow"],
    ("audio", "*"):     ["ffmpeg"],
    ("video", "*"):     ["ffmpeg"],
}

# ─── Core conversion functions ────────────────────────────────────────────────

# ── PDF ──────────────────────────────────────────────────────────────────────

def pdf_to_txt(src, dst, pages=None):
    if not HAS_PDFPLUMBER:
        raise ImportError("pip install pdfplumber")
    with pdfplumber.open(src) as pdf:
        total = len(pdf.pages)
        target = pages or list(range(1, total + 1))
        lines = []
        for p in target:
            if 1 <= p <= total:
                lines.append(f"\n{'='*60}\nPAGE {p}\n{'='*60}\n")
                lines.append(pdf.pages[p-1].extract_text() or "")
    Path(dst).write_text("\n".join(lines), encoding="utf-8")
    return dst

def pdf_to_docx(src, dst, pages=None):
    if not HAS_PDFPLUMBER or not HAS_DOCX:
        raise ImportError("pip install pdfplumber python-docx")
    doc = Document()
    doc.add_heading(Path(src).stem, 0)
    with pdfplumber.open(src) as pdf:
        total = len(pdf.pages)
        target = pages or list(range(1, total + 1))
        for p in target:
            if 1 <= p <= total:
                doc.add_heading(f"Page {p}", 2)
                text = pdf.pages[p-1].extract_text() or ""
                for para in text.split("\n\n"):
                    if para.strip():
                        doc.add_paragraph(para.strip())
                doc.add_page_break()
    doc.save(dst)
    return dst

def pdf_to_images(src, dst_dir, fmt="png", pages=None, dpi=150):
    if not HAS_PDF2IMAGE:
        raise ImportError("pip install pdf2image  (also install poppler)")
    os.makedirs(dst_dir, exist_ok=True)
    kw = {"dpi": dpi, "fmt": fmt}
    if pages:
        kw["first_page"] = min(pages)
        kw["last_page"]  = max(pages)
    imgs = convert_from_path(src, **kw)
    out = []
    for i, img in enumerate(imgs):
        pg = (pages[i] if pages and i < len(pages) else i + 1)
        p = os.path.join(dst_dir, f"page_{pg}.{fmt}")
        img.save(p)
        out.append(p)
    return out

def pdf_to_html(src, dst, pages=None):
    if not HAS_PDFPLUMBER:
        raise ImportError("pip install pdfplumber")
    with pdfplumber.open(src) as pdf:
        total = len(pdf.pages)
        target = pages or list(range(1, total + 1))
        html_parts = [f"<html><head><meta charset='utf-8'>"
                      f"<title>{Path(src).stem}</title>"
                      f"<style>body{{font-family:Georgia,serif;max-width:860px;margin:auto;padding:2em}}"
                      f"h2{{border-bottom:2px solid #c00;padding-bottom:.3em}}</style></head><body>"]
        for p in target:
            if 1 <= p <= total:
                text = pdf.pages[p-1].extract_text() or ""
                safe = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                html_parts.append(f"<h2>Page {p}</h2><pre style='white-space:pre-wrap'>{safe}</pre><hr>")
        html_parts.append("</body></html>")
    Path(dst).write_text("\n".join(html_parts), encoding="utf-8")
    return dst

# ── PDF Split ────────────────────────────────────────────────────────────────

def pdf_page_count(src):
    return len(PdfReader(src).pages)

def split_each(src, out_dir, prefix="page"):
    os.makedirs(out_dir, exist_ok=True)
    reader = PdfReader(src)
    out = []
    for i, page in enumerate(reader.pages):
        w = PdfWriter(); w.add_page(page)
        p = os.path.join(out_dir, f"{prefix}_{i+1}.pdf")
        with open(p, "wb") as f: w.write(f)
        out.append(p)
    return out

def split_range(src, start, end, out_dir, prefix="range"):
    os.makedirs(out_dir, exist_ok=True)
    reader = PdfReader(src)
    total = len(reader.pages)
    start, end = max(1, start), min(total, end)
    w = PdfWriter()
    for i in range(start-1, end): w.add_page(reader.pages[i])
    p = os.path.join(out_dir, f"{prefix}_pages{start}-{end}.pdf")
    with open(p, "wb") as f: w.write(f)
    return p

def split_custom(src, groups, out_dir, prefix="group"):
    os.makedirs(out_dir, exist_ok=True)
    reader = PdfReader(src)
    total = len(reader.pages)
    out = []
    for idx, group in enumerate(groups):
        w = PdfWriter()
        valid = [p for p in group if 1 <= p <= total]
        for pg in valid: w.add_page(reader.pages[pg-1])
        if valid:
            label = "_".join(str(p) for p in valid)
            p = os.path.join(out_dir, f"{prefix}{idx+1}_p{label}.pdf")
            with open(p, "wb") as f: w.write(f)
            out.append(p)
    return out

# ── Image ────────────────────────────────────────────────────────────────────

def image_convert(src, dst):
    if not HAS_PIL:
        raise ImportError("pip install Pillow")
    img = Image.open(src)
    ext = Path(dst).suffix.lower()
    # Handle modes for special formats
    if ext in (".jpg", ".jpeg"):
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
    elif ext == ".bmp":
        img = img.convert("RGB")
    elif ext == ".ico":
        img = img.resize((256, 256), Image.LANCZOS)
    img.save(dst)
    return dst

def images_to_pdf(src_list, dst):
    if not HAS_PIL:
        raise ImportError("pip install Pillow")
    imgs = []
    for p in src_list:
        img = Image.open(p).convert("RGB")
        imgs.append(img)
    if imgs:
        imgs[0].save(dst, save_all=True, append_images=imgs[1:])
    return dst

# ── DOCX ─────────────────────────────────────────────────────────────────────

def docx_to_txt(src, dst):
    if not HAS_DOCX:
        raise ImportError("pip install python-docx")
    doc = Document(src)
    text = "\n".join(p.text for p in doc.paragraphs)
    Path(dst).write_text(text, encoding="utf-8")
    return dst

def docx_to_html(src, dst):
    if not HAS_DOCX:
        raise ImportError("pip install python-docx")
    doc = Document(src)
    parts = [f"<html><head><meta charset='utf-8'><title>{Path(src).stem}</title>"
             f"<style>body{{font-family:Georgia,serif;max-width:860px;margin:auto;padding:2em}}</style></head><body>"]
    for p in doc.paragraphs:
        if p.style.name.startswith("Heading"):
            lvl = p.style.name[-1] if p.style.name[-1].isdigit() else "2"
            parts.append(f"<h{lvl}>{p.text}</h{lvl}>")
        else:
            safe = p.text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            parts.append(f"<p>{safe}</p>")
    parts.append("</body></html>")
    Path(dst).write_text("\n".join(parts), encoding="utf-8")
    return dst

def docx_to_pdf(src, dst):
    # Try LibreOffice first (cross-platform), then docx2pdf (Windows/Mac)
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if lo:
        out_dir = str(Path(dst).parent)
        result = subprocess.run(
            [lo, "--headless", "--convert-to", "pdf", "--outdir", out_dir, src],
            capture_output=True, text=True
        )
        # LibreOffice names the file itself
        expected = Path(out_dir) / (Path(src).stem + ".pdf")
        if expected.exists() and str(expected) != dst:
            os.rename(expected, dst)
        if not Path(dst).exists():
            raise RuntimeError(f"LibreOffice conversion failed:\n{result.stderr}")
        return dst
    try:
        from docx2pdf import convert as d2p
        d2p(src, dst)
        return dst
    except ImportError:
        raise ImportError(
            "DOCX→PDF needs LibreOffice (free) or docx2pdf.\n"
            "  Linux/Mac: install LibreOffice from libreoffice.org\n"
            "  Windows:   pip install docx2pdf"
        )

# ── TXT ──────────────────────────────────────────────────────────────────────

def txt_to_pdf(src, dst):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.units import mm
    except ImportError:
        raise ImportError("pip install reportlab")
    text = Path(src).read_text(encoding="utf-8", errors="replace")
    doc = SimpleDocTemplate(dst, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []
    for line in text.split("\n"):
        story.append(Paragraph(line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                               or "&nbsp;", styles["Normal"]))
        story.append(Spacer(1, 2))
    doc.build(story)
    return dst

def txt_to_docx(src, dst):
    if not HAS_DOCX:
        raise ImportError("pip install python-docx")
    text = Path(src).read_text(encoding="utf-8", errors="replace")
    doc = Document()
    doc.add_heading(Path(src).stem, 0)
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(dst)
    return dst

def txt_to_html(src, dst):
    text = Path(src).read_text(encoding="utf-8", errors="replace")
    safe = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    html = (f"<html><head><meta charset='utf-8'><title>{Path(src).stem}</title>"
            f"<style>body{{font-family:monospace;max-width:900px;margin:auto;padding:2em}}</style></head>"
            f"<body><pre>{safe}</pre></body></html>")
    Path(dst).write_text(html, encoding="utf-8")
    return dst

# ── HTML ─────────────────────────────────────────────────────────────────────

def html_to_txt(src, dst):
    html = Path(src).read_text(encoding="utf-8", errors="replace")
    import re
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    Path(dst).write_text(text.strip(), encoding="utf-8")
    return dst

def html_to_pdf(src, dst):
    if HAS_WEASYPRINT:
        from weasyprint import HTML
        HTML(filename=src).write_pdf(dst)
        return dst
    wk = shutil.which("wkhtmltopdf")
    if wk:
        result = subprocess.run([wk, src, dst], capture_output=True, text=True)
        if Path(dst).exists():
            return dst
        raise RuntimeError(result.stderr)
    raise ImportError(
        "HTML→PDF needs weasyprint or wkhtmltopdf.\n"
        "  pip install weasyprint\n"
        "  OR: https://wkhtmltopdf.org/downloads.html"
    )

# ── Audio / Video via ffmpeg ──────────────────────────────────────────────────

def ffmpeg_convert(src, dst, extra_args=None):
    if not HAS_FFMPEG:
        raise RuntimeError(
            "ffmpeg not found.\n"
            "  Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  Mac:           brew install ffmpeg\n"
            "  Windows:       https://ffmpeg.org/download.html"
        )
    cmd = ["ffmpeg", "-y", "-i", src]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(dst)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not Path(dst).exists():
        raise RuntimeError(f"ffmpeg error:\n{result.stderr[-800:]}")
    return dst

def video_to_gif(src, dst, fps=10, scale=480):
    return ffmpeg_convert(src, dst, [
        "-vf", f"fps={fps},scale={scale}:-1:flags=lanczos",
        "-loop", "0"
    ])

# ─── Page string parser ───────────────────────────────────────────────────────

def parse_pages(s: str, total: int) -> List[int]:
    pages = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            try: pages.update(range(int(a), int(b)+1))
            except: pass
        else:
            try: pages.add(int(part))
            except: pass
    return sorted(p for p in pages if 1 <= p <= total)

def parse_groups(s: str, total: int) -> List[List[int]]:
    groups = []
    for chunk in s.split("|"):
        pg = parse_pages(chunk.strip(), total)
        if pg: groups.append(pg)
    return groups

# ─── Dispatch ─────────────────────────────────────────────────────────────────

def do_convert(src: str, out_fmt: str, out_dir: str,
               pages_str: str = "", dpi: int = 150, log=None) -> List[str]:
    """Master dispatch. Returns list of output paths."""
    def L(msg): log(msg) if log else None

    in_cat = categorize(src)
    stem   = Path(src).stem
    out_fmt = out_fmt.lower().lstrip(".")
    os.makedirs(out_dir, exist_ok=True)

    total = 0
    if in_cat == "pdf" and HAS_PYPDF:
        total = pdf_page_count(src)
    pages = parse_pages(pages_str, total) if pages_str.strip() and total else None

    # ── PDF source ────────────────────────────────────────────────────────────
    if in_cat == "pdf":
        if out_fmt == "txt":
            dst = os.path.join(out_dir, stem + ".txt")
            L(f"PDF → TXT …"); pdf_to_txt(src, dst, pages); return [dst]
        if out_fmt == "docx":
            dst = os.path.join(out_dir, stem + ".docx")
            L(f"PDF → DOCX …"); pdf_to_docx(src, dst, pages); return [dst]
        if out_fmt in ("png", "jpg", "jpeg"):
            img_dir = os.path.join(out_dir, stem + "_images")
            L(f"PDF → {out_fmt.upper()} (DPI={dpi}) …")
            return pdf_to_images(src, img_dir, out_fmt, pages, dpi)
        if out_fmt == "html":
            dst = os.path.join(out_dir, stem + ".html")
            L("PDF → HTML …"); pdf_to_html(src, dst, pages); return [dst]

    # ── Image source ──────────────────────────────────────────────────────────
    if in_cat == "image":
        if out_fmt == "pdf":
            dst = os.path.join(out_dir, stem + ".pdf")
            L("Image → PDF …"); images_to_pdf([src], dst); return [dst]
        dst = os.path.join(out_dir, stem + "." + out_fmt)
        L(f"Image → {out_fmt.upper()} …"); image_convert(src, dst); return [dst]

    # ── DOCX source ───────────────────────────────────────────────────────────
    if in_cat == "docx":
        if out_fmt == "pdf":
            dst = os.path.join(out_dir, stem + ".pdf")
            L("DOCX → PDF …"); docx_to_pdf(src, dst); return [dst]
        if out_fmt == "txt":
            dst = os.path.join(out_dir, stem + ".txt")
            L("DOCX → TXT …"); docx_to_txt(src, dst); return [dst]
        if out_fmt == "html":
            dst = os.path.join(out_dir, stem + ".html")
            L("DOCX → HTML …"); docx_to_html(src, dst); return [dst]

    # ── TXT source ────────────────────────────────────────────────────────────
    if in_cat == "txt":
        if out_fmt == "pdf":
            dst = os.path.join(out_dir, stem + ".pdf")
            L("TXT → PDF …"); txt_to_pdf(src, dst); return [dst]
        if out_fmt == "docx":
            dst = os.path.join(out_dir, stem + ".docx")
            L("TXT → DOCX …"); txt_to_docx(src, dst); return [dst]
        if out_fmt == "html":
            dst = os.path.join(out_dir, stem + ".html")
            L("TXT → HTML …"); txt_to_html(src, dst); return [dst]

    # ── HTML source ───────────────────────────────────────────────────────────
    if in_cat == "html":
        if out_fmt == "pdf":
            dst = os.path.join(out_dir, stem + ".pdf")
            L("HTML → PDF …"); html_to_pdf(src, dst); return [dst]
        if out_fmt == "txt":
            dst = os.path.join(out_dir, stem + ".txt")
            L("HTML → TXT …"); html_to_txt(src, dst); return [dst]

    # ── Video / Audio via ffmpeg ──────────────────────────────────────────────
    if in_cat in ("video", "audio"):
        out_is_gif = out_fmt == "gif"
        dst = os.path.join(out_dir, stem + "." + out_fmt)
        L(f"{in_cat.upper()} → {out_fmt.upper()} …")
        if out_is_gif:
            video_to_gif(src, dst)
        else:
            ffmpeg_convert(src, dst)
        return [dst]

    raise ValueError(f"No conversion available: {in_cat} → {out_fmt}")


# ═══════════════════════════════════════════════════════════════════════════════
# GUI
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Colour palette & fonts ───────────────────────────────────────────────────
C = dict(
    bg       = "#1c1c2e",
    panel    = "#252540",
    card     = "#2e2e4a",
    border   = "#3a3a5c",
    accent   = "#7c6af7",       # purple
    accent2  = "#f7706a",       # coral
    success  = "#4ecdc4",
    warning  = "#ffd166",
    text     = "#e8e8f0",
    dim      = "#8888aa",
    dim2     = "#555577",
    log_bg   = "#12121e",
    tag_ok   = "#4ecdc4",
    tag_err  = "#f7706a",
    tag_info = "#7c6af7",
    sidebar  = "#1a1a30",
)
F = dict(
    title  = ("Consolas", 20, "bold"),
    head   = ("Consolas", 12, "bold"),
    label  = ("Consolas", 10),
    body   = ("Consolas", 10),
    small  = ("Consolas", 9),
    log    = ("Consolas", 9),
    btn    = ("Consolas", 10, "bold"),
    btnbig = ("Consolas", 11, "bold"),
    tab    = ("Consolas", 10, "bold"),
)

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        x, y, _, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0,0,0,0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(tw, text=self.text, font=F["small"],
                       bg="#2a2a3e", fg=C["text"], relief="flat",
                       padx=8, pady=4, wraplength=300, justify="left")
        lbl.pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class FileWorkshop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Workshop")
        self.configure(bg=C["bg"])
        self.geometry("1020x720")
        self.minsize(880, 600)

        # state
        self.files: List[str] = []
        self.out_dir = tk.StringVar()
        self.page_count = 0

        self._build()
        self._status("Ready — drag files or click Add Files")

    # ─── Top-level layout ─────────────────────────────────────────────────────

    def _build(self):
        # ── Header bar ────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["sidebar"], pady=0)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⬛ FILE WORKSHOP", font=F["title"],
                 bg=C["sidebar"], fg=C["accent"]).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="convert · split · transform",
                 font=("Consolas", 10), bg=C["sidebar"], fg=C["dim"]).pack(side="left", pady=14)

        # dep indicator
        self.dep_lbl = tk.Label(hdr, text="", font=F["small"],
                                bg=C["sidebar"], fg=C["dim"])
        self.dep_lbl.pack(side="right", padx=18)
        self._refresh_dep_badge()

        # ── Main body (sidebar | content) ────────────────────────────────────
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True)

        self.pages = {}
        self._build_sidebar(body)
        self._build_content(body)
        self._switch_tab("convert")

    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=C["sidebar"], width=200)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        tk.Label(sb, text="NAVIGATION", font=F["small"],
                 bg=C["sidebar"], fg=C["dim2"]).pack(anchor="w", padx=16, pady=(18, 6))

        self.active_tab = tk.StringVar(value="convert")
        tabs = [
            ("🔄  Convert",  "convert"),
            ("✂️  PDF Split",  "split"),
            ("📋  File Queue", "queue"),
            ("ℹ️  Help",       "help"),
        ]
        self.tab_btns = {}
        for label, key in tabs:
            b = tk.Button(sb, text=label, font=F["tab"],
                          bg=C["sidebar"], fg=C["dim"],
                          relief="flat", bd=0, cursor="hand2",
                          anchor="w", padx=16, pady=10,
                          activebackground=C["card"],
                          command=lambda k=key: self._switch_tab(k))
            b.pack(fill="x")
            self.tab_btns[key] = b

        # separator
        tk.Frame(sb, bg=C["border"], height=1).pack(fill="x", padx=10, pady=12)

        # output dir in sidebar
        tk.Label(sb, text="OUTPUT FOLDER", font=F["small"],
                 bg=C["sidebar"], fg=C["dim2"]).pack(anchor="w", padx=16, pady=(0,4))
        od_frame = tk.Frame(sb, bg=C["sidebar"])
        od_frame.pack(fill="x", padx=10, pady=(0, 6))
        self.od_entry = tk.Entry(od_frame, textvariable=self.out_dir,
                                 font=("Consolas", 8),
                                 bg=C["card"], fg=C["text"],
                                 insertbackground=C["text"],
                                 relief="flat", bd=0)
        self.od_entry.pack(fill="x", ipady=4, padx=2)
        self._mkbtn(sb, "📁  Choose Folder", self._browse_output,
                    color=C["dim2"]).pack(fill="x", padx=10, pady=(0, 8))

        tk.Frame(sb, bg=C["border"], height=1).pack(fill="x", padx=10, pady=4)
        self._mkbtn(sb, "📂  Open Output", self._open_output,
                    color=C["dim2"]).pack(fill="x", padx=10, pady=(4, 2))
        self._mkbtn(sb, "🗑  Clear Queue", self._clear_queue,
                    color=C["dim2"]).pack(fill="x", padx=10, pady=(2, 8))

    def _build_content(self, parent):
        self.content = tk.Frame(parent, bg=C["bg"])
        self.content.pack(side="left", fill="both", expand=True)

        # ── File drop zone ────────────────────────────────────────────────────
        drop = tk.Frame(self.content, bg=C["card"], pady=12, padx=16)
        drop.pack(fill="x", padx=18, pady=(14, 6))

        left = tk.Frame(drop, bg=C["card"])
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="📥  Add files to process",
                 font=F["head"], bg=C["card"], fg=C["text"]).pack(anchor="w")
        tk.Label(left, text="PDF, images (PNG/JPG/WEBP…), Word, TXT, HTML, audio, video",
                 font=F["small"], bg=C["card"], fg=C["dim"]).pack(anchor="w", pady=(2,0))

        right = tk.Frame(drop, bg=C["card"])
        right.pack(side="right")
        self._mkbtn(right, "+ Add Files", self._add_files, big=True).pack(side="left", padx=(0,6))
        self._mkbtn(right, "+ Add Folder", self._add_folder, color=C["border"], big=True).pack(side="left")

        # ── Tab pages container ───────────────────────────────────────────────
        self.pages: Dict[str, tk.Frame] = {}
        for key in ("convert", "split", "queue", "help"):
            f = tk.Frame(self.content, bg=C["bg"])
            self.pages[key] = f

        self._build_convert_page()
        self._build_split_page()
        self._build_queue_page()
        self._build_help_page()

        # ── Log / status bar ─────────────────────────────────────────────────
        log_outer = tk.Frame(self.content, bg=C["log_bg"])
        log_outer.pack(fill="x", padx=18, pady=(0, 10), side="bottom")

        log_hdr = tk.Frame(log_outer, bg=C["log_bg"])
        log_hdr.pack(fill="x")
        tk.Label(log_hdr, text="LOG", font=F["small"],
                 bg=C["log_bg"], fg=C["dim2"]).pack(side="left", padx=8, pady=(4,2))
        self._mkbtn(log_hdr, "Clear", self._clear_log,
                    color=C["dim2"]).pack(side="right", padx=8)

        self.log_box = scrolledtext.ScrolledText(
            log_outer, height=6, font=F["log"],
            bg=C["log_bg"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", state="disabled", bd=0
        )
        self.log_box.pack(fill="x", padx=2, pady=(0, 4))
        self.log_box.tag_config("ok",   foreground=C["tag_ok"])
        self.log_box.tag_config("err",  foreground=C["tag_err"])
        self.log_box.tag_config("info", foreground=C["tag_info"])
        self.log_box.tag_config("warn", foreground=C["warning"])

        # status bar
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.content, textvariable=self.status_var,
                 font=F["small"], bg=C["border"], fg=C["dim"],
                 anchor="w", padx=10, pady=3).pack(fill="x", side="bottom")

    # ─── Convert page ─────────────────────────────────────────────────────────

    def _build_convert_page(self):
        f = self.pages["convert"]
        f.columnconfigure(0, weight=1)

        # Format picker card
        fmt_card = tk.Frame(f, bg=C["panel"], padx=18, pady=14)
        fmt_card.pack(fill="x", padx=18, pady=(10, 6))

        tk.Label(fmt_card, text="OUTPUT FORMAT", font=F["head"],
                 bg=C["panel"], fg=C["accent"]).grid(row=0, column=0, sticky="w", columnspan=10)

        cats = [
            ("Documents", ["txt", "docx", "pdf", "html"]),
            ("Images",    ["png", "jpg", "webp", "bmp", "gif", "tiff", "ico"]),
            ("Audio",     ["mp3", "wav", "ogg", "flac", "aac", "m4a"]),
            ("Video",     ["mp4", "avi", "mov", "mkv", "webm", "gif"]),
        ]

        self.out_fmt = tk.StringVar(value="pdf")
        row = 1
        for cat_name, fmts in cats:
            tk.Label(fmt_card, text=cat_name + ":", font=F["small"],
                     bg=C["panel"], fg=C["dim"], width=10, anchor="w").grid(
                row=row, column=0, sticky="w", pady=(6, 2))
            for col, fmt in enumerate(fmts, start=1):
                rb = tk.Radiobutton(
                    fmt_card, text=fmt.upper(), variable=self.out_fmt,
                    value=fmt, font=F["btn"],
                    bg=C["panel"], fg=C["dim"],
                    selectcolor=C["accent"],
                    activebackground=C["panel"],
                    indicatoron=0,
                    relief="flat", padx=8, pady=3,
                    cursor="hand2",
                    command=self._on_fmt_change,
                )
                rb.grid(row=row, column=col, padx=3, pady=(6,2), sticky="w")
                self._fmt_rb_style(rb, fmt)
            row += 1

        # Options card
        opt_card = tk.Frame(f, bg=C["panel"], padx=18, pady=12)
        opt_card.pack(fill="x", padx=18, pady=6)

        tk.Label(opt_card, text="OPTIONS", font=F["head"],
                 bg=C["panel"], fg=C["accent"]).grid(row=0, column=0, sticky="w", columnspan=6, pady=(0,8))

        # Pages filter
        tk.Label(opt_card, text="Pages (PDF):", font=F["label"],
                 bg=C["panel"], fg=C["dim"], width=14, anchor="w").grid(row=1, column=0, sticky="w")
        self.conv_pages = tk.StringVar()
        pg_e = tk.Entry(opt_card, textvariable=self.conv_pages, font=F["body"],
                        bg=C["card"], fg=C["text"], insertbackground=C["text"],
                        relief="flat", bd=0, width=22)
        pg_e.grid(row=1, column=1, sticky="w", padx=(6,0), ipady=3)
        tk.Label(opt_card, text='e.g. "1,3,5-8" — blank = all',
                 font=F["small"], bg=C["panel"], fg=C["dim2"]).grid(row=1, column=2, sticky="w", padx=10)
        Tooltip(pg_e, "Applies to PDF→anything conversions.\nComma-separated, ranges with dash.\nBlank = all pages.")

        # DPI
        tk.Label(opt_card, text="DPI (images):", font=F["label"],
                 bg=C["panel"], fg=C["dim"], width=14, anchor="w").grid(row=2, column=0, sticky="w", pady=(8,0))
        self.conv_dpi = tk.StringVar(value="150")
        dpi_frame = tk.Frame(opt_card, bg=C["panel"])
        dpi_frame.grid(row=2, column=1, columnspan=2, sticky="w", padx=(6,0), pady=(8,0))
        for val, label in [("72","72 draft"), ("150","150 normal"), ("300","300 print")]:
            rb = tk.Radiobutton(dpi_frame, text=label, variable=self.conv_dpi,
                                value=val, font=F["small"],
                                bg=C["panel"], fg=C["dim"],
                                selectcolor=C["accent"],
                                activebackground=C["panel"],
                                cursor="hand2")
            rb.pack(side="left", padx=(0, 14))

        # Notes
        self.conv_note = tk.Label(opt_card, text="", font=F["small"],
                                   bg=C["panel"], fg=C["warning"],
                                   wraplength=600, justify="left")
        self.conv_note.grid(row=3, column=0, columnspan=6, sticky="w", pady=(8,0))

        # Run button
        self._mkbtn(f, "▶   RUN CONVERSION", self._run_convert, big=True,
                    color=C["accent"]).pack(pady=14)

    def _fmt_rb_style(self, rb, fmt):
        """Style radiobutton to look like a tag/pill."""
        def on_sel(*_):
            if self.out_fmt.get() == fmt:
                rb.config(bg=C["accent"], fg="#ffffff")
            else:
                rb.config(bg=C["card"], fg=C["dim"])
        rb.config(bg=C["card"], fg=C["dim"],
                  command=lambda f=fmt: [self.out_fmt.set(f), self._on_fmt_change()])
        rb.bind("<ButtonRelease-1>", on_sel)
        self.out_fmt.trace_add("write", lambda *_: on_sel())

    def _on_fmt_change(self, *_):
        fmt = self.out_fmt.get()
        notes = {
            "docx": "" if HAS_DOCX else "⚠  pip install python-docx",
            "pdf":  "",
            "png":  "" if HAS_PDF2IMAGE else "⚠  pip install pdf2image  +  install poppler",
            "jpg":  "" if HAS_PDF2IMAGE else "⚠  pip install pdf2image  +  install poppler",
            "gif":  "" if HAS_FFMPEG else "⚠  ffmpeg not found (needed for video→gif and audio/video conversions)",
            "mp3":  "" if HAS_FFMPEG else "⚠  ffmpeg not found",
            "mp4":  "" if HAS_FFMPEG else "⚠  ffmpeg not found",
            "wav":  "" if HAS_FFMPEG else "⚠  ffmpeg not found",
        }
        self.conv_note.config(text=notes.get(fmt, ""))

    # ─── Split page ───────────────────────────────────────────────────────────

    def _build_split_page(self):
        f = self.pages["split"]

        info = tk.Frame(f, bg=C["panel"], padx=18, pady=10)
        info.pack(fill="x", padx=18, pady=(10, 6))
        tk.Label(info, text="PDF SPLIT", font=F["head"],
                 bg=C["panel"], fg=C["accent"]).pack(anchor="w")
        self.split_info_lbl = tk.Label(info, text="Load a PDF first using Add Files",
                                        font=F["small"], bg=C["panel"], fg=C["dim"])
        self.split_info_lbl.pack(anchor="w", pady=(4,0))

        # Mode
        mode_card = tk.Frame(f, bg=C["panel"], padx=18, pady=14)
        mode_card.pack(fill="x", padx=18, pady=6)
        tk.Label(mode_card, text="MODE", font=F["head"],
                 bg=C["panel"], fg=C["accent"]).pack(anchor="w", pady=(0,8))

        self.split_mode = tk.StringVar(value="each")
        modes = [
            ("each",   "Each page → own PDF",    "10-page PDF → 10 separate files"),
            ("range",  "Page range → one PDF",   "Extract pages 3–8 into one file"),
            ("custom", "Custom groups",           "Define any grouping:  1,10 | 3,5 | 2-4,7"),
        ]
        for val, label, tip in modes:
            row = tk.Frame(mode_card, bg=C["panel"])
            row.pack(anchor="w", pady=2)
            rb = tk.Radiobutton(row, text=label, variable=self.split_mode,
                                value=val, font=F["body"],
                                bg=C["panel"], fg=C["text"],
                                selectcolor=C["accent2"],
                                activebackground=C["panel"],
                                command=self._update_split_ui,
                                cursor="hand2")
            rb.pack(side="left")
            tk.Label(row, text=f"  — {tip}", font=F["small"],
                     bg=C["panel"], fg=C["dim"]).pack(side="left")

        # Dynamic options
        self.split_opts = tk.Frame(f, bg=C["panel"], padx=18, pady=10)
        self.split_opts.pack(fill="x", padx=18, pady=6)
        self._update_split_ui()

        # Prefix
        prow = tk.Frame(f, bg=C["panel"], padx=18, pady=8)
        prow.pack(fill="x", padx=18, pady=2)
        tk.Label(prow, text="File prefix:", font=F["label"],
                 bg=C["panel"], fg=C["dim"], width=12, anchor="w").pack(side="left")
        self.split_prefix = tk.StringVar(value="split")
        tk.Entry(prow, textvariable=self.split_prefix, font=F["body"],
                 bg=C["card"], fg=C["text"], insertbackground=C["text"],
                 relief="flat", bd=0, width=18).pack(side="left", padx=(6,0), ipady=3)

        self._mkbtn(f, "▶   RUN SPLIT", self._run_split, big=True,
                    color=C["accent2"]).pack(pady=14)

    def _update_split_ui(self):
        for w in self.split_opts.winfo_children():
            w.destroy()
        mode = self.split_mode.get()
        f = self.split_opts

        if mode == "each":
            tk.Label(f, text="Every page saved as its own numbered PDF.",
                     font=F["body"], bg=C["panel"], fg=C["text"]).pack(anchor="w")

        elif mode == "range":
            row = tk.Frame(f, bg=C["panel"])
            row.pack(anchor="w")
            tk.Label(row, text="Start:", font=F["label"],
                     bg=C["panel"], fg=C["dim"]).pack(side="left")
            self.range_start = tk.StringVar(value="1")
            tk.Entry(row, textvariable=self.range_start, font=F["body"],
                     bg=C["card"], fg=C["text"], insertbackground=C["text"],
                     relief="flat", bd=0, width=5).pack(side="left", padx=(4,12), ipady=3)
            tk.Label(row, text="End:", font=F["label"],
                     bg=C["panel"], fg=C["dim"]).pack(side="left")
            self.range_end = tk.StringVar(value="5")
            tk.Entry(row, textvariable=self.range_end, font=F["body"],
                     bg=C["card"], fg=C["text"], insertbackground=C["text"],
                     relief="flat", bd=0, width=5).pack(side="left", padx=(4,0), ipady=3)

        elif mode == "custom":
            tk.Label(f, text='Groups separated by  |   ·   Pages separated by  ,   ·   Ranges with  -',
                     font=F["small"], bg=C["panel"], fg=C["dim"]).pack(anchor="w")
            tk.Label(f, text='Example:   1,10 | 3,5 | 2-4,7',
                     font=("Consolas", 10, "bold"), bg=C["panel"], fg=C["accent"]).pack(anchor="w", pady=(2,4))
            self.custom_groups = tk.StringVar(value="1,2 | 3,4 | 5-7")
            tk.Entry(f, textvariable=self.custom_groups, font=F["body"],
                     bg=C["card"], fg=C["text"], insertbackground=C["text"],
                     relief="flat", bd=0).pack(fill="x", ipady=4)

    # ─── Queue page ───────────────────────────────────────────────────────────

    def _build_queue_page(self):
        f = self.pages["queue"]

        tk.Label(f, text="FILE QUEUE", font=F["head"],
                 bg=C["bg"], fg=C["accent"]).pack(anchor="w", padx=18, pady=(12,4))
        tk.Label(f, text="Files staged for conversion or splitting",
                 font=F["small"], bg=C["bg"], fg=C["dim"]).pack(anchor="w", padx=18)

        list_frame = tk.Frame(f, bg=C["panel"])
        list_frame.pack(fill="both", expand=True, padx=18, pady=8)

        self.queue_lb = tk.Listbox(
            list_frame, font=F["body"],
            bg=C["card"], fg=C["text"],
            selectbackground=C["accent"],
            activestyle="none",
            relief="flat", bd=0,
            selectmode="extended"
        )
        sb = tk.Scrollbar(list_frame, orient="vertical",
                          command=self.queue_lb.yview)
        self.queue_lb.config(yscrollcommand=sb.set)
        self.queue_lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        btn_row = tk.Frame(f, bg=C["bg"])
        btn_row.pack(fill="x", padx=18, pady=(0,6))
        self._mkbtn(btn_row, "Remove Selected",
                    self._remove_selected).pack(side="left", padx=(0,6))
        self._mkbtn(btn_row, "Clear All",
                    self._clear_queue, color=C["dim2"]).pack(side="left")

    # ─── Help page ────────────────────────────────────────────────────────────

    def _build_help_page(self):
        f = self.pages["help"]
        txt = scrolledtext.ScrolledText(
            f, font=("Consolas", 10), bg=C["panel"],
            fg=C["text"], relief="flat", state="normal",
            padx=18, pady=14, wrap="word"
        )
        txt.pack(fill="both", expand=True, padx=18, pady=10)
        help_text = """FILE WORKSHOP — QUICK GUIDE
════════════════════════════════════════════════════════════

HOW TO USE
──────────
1. Click "+ Add Files" to stage one or more files.
2. Set your Output Folder (sidebar).
3. Go to CONVERT tab, pick output format, click ▶ RUN.
   OR go to PDF SPLIT tab to split a PDF.
4. Output folder opens automatically when done.

SUPPORTED CONVERSIONS
─────────────────────
PDF      →  TXT, DOCX, PNG, JPG, HTML
Images   →  PNG, JPG, WEBP, BMP, GIF, TIFF, ICO, PDF
Word     →  PDF*, TXT, HTML
TXT      →  PDF, DOCX, HTML
HTML     →  PDF**, TXT
Video    →  MP4, AVI, MOV, MKV, WEBM, GIF, MP3, WAV  (needs ffmpeg)
Audio    →  MP3, WAV, OGG, FLAC, AAC, M4A             (needs ffmpeg)

* DOCX→PDF  needs LibreOffice OR  pip install docx2pdf
** HTML→PDF needs  pip install weasyprint  OR  wkhtmltopdf

DEPENDENCIES
────────────
Core (already installed):
  pypdf          — PDF read/write
  pdfplumber     — PDF text extraction
  python-docx    — Word document support
  reportlab      — TXT→PDF

Optional:
  pdf2image      — PDF→image  (also needs poppler system package)
  Pillow         — Image conversions
  ffmpeg         — Audio/video conversions (system install)
  weasyprint     — HTML→PDF

Install missing packages:
  pip install pypdf pdfplumber python-docx reportlab pdf2image Pillow

Install ffmpeg (audio/video):
  Ubuntu/Debian:   sudo apt install ffmpeg
  macOS:           brew install ffmpeg
  Windows:         https://ffmpeg.org/download.html

Install poppler (PDF→image):
  Ubuntu/Debian:   sudo apt install poppler-utils
  macOS:           brew install poppler
  Windows:         https://github.com/oschwartz10612/poppler-windows

PDF SPLIT — CUSTOM GROUPS SYNTAX
──────────────────────────────────
Separate groups with |  and pages with , (ranges with -)
  1,10 | 3,5 | 2-4,7
  → File 1: pages 1 and 10
  → File 2: pages 3 and 5
  → File 3: pages 2, 3, 4, and 7

PAGE FILTER (Convert tab)
──────────────────────────
  1,3,5-8    →  pages 1, 3, 5, 6, 7, 8
  2-10       →  pages 2 through 10
  (blank)    →  all pages
"""
        txt.insert("1.0", help_text)
        txt.config(state="disabled")

    # ─── Tab switching ────────────────────────────────────────────────────────

    def _switch_tab(self, key: str):
        for k, btn in self.tab_btns.items():
            if k == key:
                btn.config(bg=C["accent"], fg="#ffffff")
            else:
                btn.config(bg=C["sidebar"], fg=C["dim"])
        for k, page in self.pages.items():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        self.active_tab.set(key)

    # ─── File management ─────────────────────────────────────────────────────

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select files",
            filetypes=[
                ("All supported", "*.pdf *.docx *.txt *.html *.htm "
                                  "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.tif *.ico "
                                  "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv "
                                  "*.mp3 *.wav *.ogg *.flac *.aac *.m4a"),
                ("PDF",      "*.pdf"),
                ("Images",   "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff *.ico"),
                ("Documents","*.docx *.txt *.html *.htm"),
                ("Audio",    "*.mp3 *.wav *.ogg *.flac *.aac *.m4a"),
                ("Video",    "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv"),
                ("All files","*.*"),
            ]
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.queue_lb.insert("end", f"  {Path(p).name}  [{categorize(p)}]")
        self._update_after_files()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Select folder to add all files from")
        if not folder:
            return
        exts = IMAGE_EXTS | AUDIO_EXTS | VIDEO_EXTS | {".pdf",".docx",".txt",".html",".htm"}
        added = 0
        for path in Path(folder).iterdir():
            if path.suffix.lower() in exts and str(path) not in self.files:
                self.files.append(str(path))
                self.queue_lb.insert("end", f"  {path.name}  [{categorize(str(path))}]")
                added += 1
        self._log(f"Added {added} file(s) from folder.")
        self._update_after_files()

    def _update_after_files(self):
        n = len(self.files)
        self._status(f"{n} file(s) in queue")
        if not self.out_dir.get() and self.files:
            self.out_dir.set(str(Path(self.files[0]).parent / "workshop_output"))
        # update split info
        pdfs = [f for f in self.files if categorize(f) == "pdf"]
        if pdfs and HAS_PYPDF:
            try:
                pc = pdf_page_count(pdfs[0])
                self.page_count = pc
                self.split_info_lbl.config(
                    text=f"Active PDF: {Path(pdfs[0]).name}  ·  {pc} pages",
                    fg=C["success"])
            except Exception:
                pass

    def _remove_selected(self):
        sel = list(self.queue_lb.curselection())
        for i in reversed(sel):
            self.files.pop(i)
            self.queue_lb.delete(i)

    def _clear_queue(self):
        self.files.clear()
        self.queue_lb.delete(0, "end")
        self.page_count = 0
        self._status("Queue cleared")

    def _browse_output(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.out_dir.set(p)

    def _open_output(self):
        folder = self.out_dir.get()
        if not folder:
            messagebox.showinfo("No folder", "Set an output folder first.")
            return
        os.makedirs(folder, exist_ok=True)
        try:
            if sys.platform == "win32":   os.startfile(folder)
            elif sys.platform == "darwin": subprocess.run(["open", folder])
            else:                          subprocess.run(["xdg-open", folder])
        except Exception as e:
            self._log(f"Could not open folder: {e}", "err")

    # ─── Run convert ─────────────────────────────────────────────────────────

    def _run_convert(self):
        if not self.files:
            messagebox.showwarning("No files", "Add files to the queue first.")
            return
        out = self.out_dir.get()
        if not out:
            messagebox.showwarning("No output", "Set an output folder first.")
            return
        fmt = self.out_fmt.get()
        pages_str = self.conv_pages.get().strip()
        try:
            dpi = int(self.conv_dpi.get())
        except ValueError:
            dpi = 150

        def task():
            total = len(self.files)
            ok = 0
            for idx, src in enumerate(list(self.files)):
                self._status(f"Processing {idx+1}/{total}: {Path(src).name}")
                try:
                    results = do_convert(src, fmt, out, pages_str, dpi, log=self._log)
                    for r in results:
                        self._log(f"✔  {Path(r).name}", "ok")
                    ok += 1
                except Exception as e:
                    self._log(f"✖  {Path(src).name}: {e}", "err")
            self._log(f"Done — {ok}/{total} files converted.", "info")
            self._status(f"Done — {ok}/{total} converted")
            self.after(200, lambda: self._open_output())

        threading.Thread(target=task, daemon=True).start()

    # ─── Run split ────────────────────────────────────────────────────────────

    def _run_split(self):
        pdfs = [f for f in self.files if categorize(f) == "pdf"]
        if not pdfs:
            messagebox.showwarning("No PDF", "Add a PDF file to the queue first.")
            return
        if not HAS_PYPDF:
            messagebox.showerror("Missing", "Install pypdf:  pip install pypdf")
            return
        out = self.out_dir.get()
        if not out:
            messagebox.showwarning("No output", "Set an output folder first.")
            return
        mode = self.split_mode.get()
        prefix = self.split_prefix.get().strip() or "split"
        src = pdfs[0]

        def task():
            try:
                if mode == "each":
                    self._log(f"Splitting every page of {Path(src).name} …")
                    files = split_each(src, out, prefix)
                    self._log(f"✔  {len(files)} files created.", "ok")

                elif mode == "range":
                    try:
                        s, e = int(self.range_start.get()), int(self.range_end.get())
                    except ValueError:
                        self._log("⚠  Enter valid integers for start/end.", "err")
                        return
                    self._log(f"Extracting pages {s}–{e} …")
                    p = split_range(src, s, e, out, prefix)
                    self._log(f"✔  Saved: {Path(p).name}", "ok")

                elif mode == "custom":
                    raw = self.custom_groups.get()
                    groups = parse_groups(raw, self.page_count or 9999)
                    if not groups:
                        self._log("⚠  No valid groups parsed.", "err"); return
                    self._log(f"Splitting into {len(groups)} groups …")
                    files = split_custom(src, groups, out, prefix)
                    for fp in files:
                        self._log(f"  → {Path(fp).name}")
                    self._log(f"✔  {len(files)} files created.", "ok")

                self.after(200, self._open_output)
            except Exception as ex:
                self._log(f"ERROR: {ex}", "err")

        threading.Thread(target=task, daemon=True).start()

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _log(self, msg: str, kind: str = ""):
        def _do():
            self.log_box.config(state="normal")
            tag = {"ok":"ok","err":"err","info":"info","warn":"warn"}.get(kind, "")
            self.log_box.insert("end", "  " + msg + "\n", tag)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _do)

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _status(self, msg: str):
        self.after(0, lambda: self.status_var.set("  " + msg))

    def _mkbtn(self, parent, text, cmd, color=None, big=False):
        bg = color or C["accent2"]
        fn = F["btnbig"] if big else F["btn"]
        return tk.Button(
            parent, text=text, command=cmd,
            bg=bg, fg="#ffffff",
            activebackground=C["border"],
            relief="flat", cursor="hand2",
            font=fn, padx=12 if big else 10,
            pady=7 if big else 4, bd=0
        )

    def _refresh_dep_badge(self):
        installed = sum([HAS_PYPDF, HAS_PDFPLUMBER, HAS_DOCX, HAS_PIL,
                         HAS_PDF2IMAGE, HAS_FFMPEG])
        total = 6
        color = C["success"] if installed == total else C["warning"]
        self.dep_lbl.config(
            text=f"deps: {installed}/{total} ✓",
            fg=color
        )
        Tooltip(self.dep_lbl,
                f"pypdf: {'✔' if HAS_PYPDF else '✖  pip install pypdf'}\n"
                f"pdfplumber: {'✔' if HAS_PDFPLUMBER else '✖  pip install pdfplumber'}\n"
                f"python-docx: {'✔' if HAS_DOCX else '✖  pip install python-docx'}\n"
                f"Pillow: {'✔' if HAS_PIL else '✖  pip install Pillow'}\n"
                f"pdf2image: {'✔' if HAS_PDF2IMAGE else '✖  pip install pdf2image'}\n"
                f"ffmpeg: {'✔' if HAS_FFMPEG else '✖  sudo apt install ffmpeg'}")


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not HAS_PYPDF:
        print("pypdf is required:  pip install pypdf")
        sys.exit(1)
    app = FileWorkshop()
    app.mainloop()
