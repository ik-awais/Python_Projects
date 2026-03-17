"""
core/processor.py — All file conversion, split, merge, organise operations.
Identical logic to File Workshop v4 but as clean importable functions.
"""

import os, re, csv, shutil, tempfile
from pathlib import Path
from typing import List, Dict, Optional

def _try(pkg):
    try: __import__(pkg); return True
    except ImportError: return False

HAS_PYPDF      = _try("pypdf")
HAS_PDFPLUMBER = _try("pdfplumber")
HAS_DOCX       = _try("docx")
HAS_PIL        = _try("PIL")
HAS_PDF2IMAGE  = _try("pdf2image")
HAS_REPORTLAB  = _try("reportlab")
HAS_WEASYPRINT = _try("weasyprint")
HAS_OPENPYXL   = _try("openpyxl")
HAS_PPTX       = _try("pptx")
HAS_FFMPEG     = bool(shutil.which("ffmpeg"))
HAS_LIBREOFFICE = bool(shutil.which("libreoffice") or shutil.which("soffice"))

import subprocess
if HAS_PYPDF:
    from pypdf import PdfReader, PdfWriter
if HAS_PDFPLUMBER: import pdfplumber
if HAS_DOCX:
    from docx import Document
    from docx.shared import Pt, Inches
if HAS_PIL: from PIL import Image, ImageDraw, ImageFont
if HAS_PDF2IMAGE: from pdf2image import convert_from_path
if HAS_OPENPYXL: import openpyxl
if HAS_PPTX:
    from pptx import Presentation
    from pptx.util import Inches as PInches, Pt as PPt

IMAGE_EXTS = {".png",".jpg",".jpeg",".webp",".bmp",".gif",".tiff",".tif",".ico"}
AUDIO_EXTS = {".mp3",".wav",".ogg",".flac",".aac",".m4a",".wma"}
VIDEO_EXTS = {".mp4",".avi",".mov",".mkv",".webm",".flv",".wmv",".m4v"}
EXCEL_EXTS = {".xlsx",".xls",".xlsm",".ods"}
PPTX_EXTS  = {".pptx",".ppt",".odp"}
CSV_EXTS   = {".csv",".tsv"}

def cat(path):
    e = Path(path).suffix.lower()
    if e in IMAGE_EXTS: return "image"
    if e in AUDIO_EXTS: return "audio"
    if e in VIDEO_EXTS: return "video"
    if e in EXCEL_EXTS: return "excel"
    if e in PPTX_EXTS:  return "pptx"
    if e in CSV_EXTS:   return "csv"
    if e == ".pdf":     return "pdf"
    if e == ".docx":    return "docx"
    if e == ".txt":     return "txt"
    if e in {".html",".htm"}: return "html"
    return "unknown"

def cat_icon(c):
    return {"pdf":"📄","image":"🖼","audio":"🎵","video":"🎬",
            "docx":"📝","txt":"📃","html":"🌐","excel":"📊",
            "pptx":"📽","csv":"📋"}.get(c,"📎")

def parse_pages(s, total):
    pages = set()
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a,b = part.split("-",1)
            try: pages.update(range(int(a),int(b)+1))
            except: pass
        else:
            try: pages.add(int(part))
            except: pass
    return sorted(p for p in pages if 1<=p<=total)

def parse_groups(s, total):
    return [g for g in (parse_pages(c.strip(),total) for c in s.split("|")) if g]

# ── LibreOffice ───────────────────────────────────────────────────────────────

def lo_convert(src, dst_fmt, out_dir):
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if not lo:
        raise RuntimeError("LibreOffice not found.\n  sudo apt install libreoffice")
    os.makedirs(out_dir, exist_ok=True)
    r = subprocess.run([lo,"--headless","--convert-to",dst_fmt,"--outdir",out_dir,src],
                       capture_output=True, text=True)
    expected = Path(out_dir)/(Path(src).stem+"."+dst_fmt)
    if not expected.exists():
        raise RuntimeError(f"LibreOffice failed:\n{r.stderr[-400:]}")
    return str(expected)

# ── PDF ───────────────────────────────────────────────────────────────────────

def pdf_page_count(src): return len(PdfReader(src).pages)

def pdf_to_txt(src,dst,pages=None):
    if not HAS_PDFPLUMBER: raise ImportError("pip install pdfplumber")
    with pdfplumber.open(src) as pdf:
        total=len(pdf.pages); target=pages or list(range(1,total+1))
        lines=[]
        for p in target:
            if 1<=p<=total:
                lines.append(f"\n{'='*50}\nPAGE {p}\n{'='*50}\n")
                lines.append(pdf.pages[p-1].extract_text() or "")
    Path(dst).write_text("\n".join(lines),encoding="utf-8"); return dst

def pdf_to_docx(src,dst,pages=None):
    if not(HAS_PDFPLUMBER and HAS_DOCX): raise ImportError("pip install pdfplumber python-docx")
    doc=Document(); doc.add_heading(Path(src).stem,0)
    with pdfplumber.open(src) as pdf:
        total=len(pdf.pages); target=pages or list(range(1,total+1))
        for p in target:
            if 1<=p<=total:
                doc.add_heading(f"Page {p}",2)
                text=pdf.pages[p-1].extract_text() or ""
                for para in text.split("\n\n"):
                    if para.strip(): doc.add_paragraph(para.strip())
                doc.add_page_break()
    doc.save(dst); return dst

def pdf_to_images(src,dst_dir,fmt="png",pages=None,dpi=150):
    if not HAS_PDF2IMAGE: raise ImportError("pip install pdf2image (+poppler)")
    os.makedirs(dst_dir,exist_ok=True)
    kw={"dpi":dpi,"fmt":fmt}
    if pages: kw["first_page"],kw["last_page"]=min(pages),max(pages)
    imgs=convert_from_path(src,**kw); out=[]
    for i,img in enumerate(imgs):
        pg=pages[i] if pages and i<len(pages) else i+1
        p=os.path.join(dst_dir,f"page_{pg}.{fmt}"); img.save(p); out.append(p)
    return out

def pdf_to_html(src,dst,pages=None):
    if not HAS_PDFPLUMBER: raise ImportError("pip install pdfplumber")
    with pdfplumber.open(src) as pdf:
        total=len(pdf.pages); target=pages or list(range(1,total+1))
        parts=[f"<html><head><meta charset='utf-8'><title>{Path(src).stem}</title>"
               f"<style>body{{font-family:Georgia,serif;max-width:860px;margin:auto;padding:2em}}"
               f"h2{{border-bottom:2px solid #7c6af7}}</style></head><body>"]
        for p in target:
            if 1<=p<=total:
                text=pdf.pages[p-1].extract_text() or ""
                safe=text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                parts.append(f"<h2>Page {p}</h2><pre style='white-space:pre-wrap'>{safe}</pre><hr>")
        parts.append("</body></html>")
    Path(dst).write_text("\n".join(parts),encoding="utf-8"); return dst

def pdf_to_xlsx(src,dst):
    if not(HAS_PDFPLUMBER and HAS_OPENPYXL): raise ImportError("pip install pdfplumber openpyxl")
    wb=openpyxl.Workbook(); wb.remove(wb.active)
    with pdfplumber.open(src) as pdf:
        for i,page in enumerate(pdf.pages):
            ws=wb.create_sheet(title=f"Page_{i+1}")
            tables=page.extract_tables()
            if tables:
                for table in tables:
                    for row in table: ws.append([c or "" for c in row])
                    ws.append([])
            else:
                for line in (page.extract_text() or "").split("\n"): ws.append([line])
    wb.save(dst); return dst

def pdf_to_pptx(src,dst,dpi=150):
    if not(HAS_PDF2IMAGE and HAS_PPTX): raise ImportError("pip install pdf2image python-pptx (+poppler)")
    imgs=convert_from_path(src,dpi=dpi); prs=Presentation()
    blank=prs.slide_layouts[6]
    for img in imgs:
        slide=prs.slides.add_slide(blank)
        with tempfile.NamedTemporaryFile(suffix=".png",delete=False) as tf: tmp=tf.name
        img.save(tmp)
        slide.shapes.add_picture(tmp,0,0,width=prs.slide_width,height=prs.slide_height)
        os.unlink(tmp)
    prs.save(dst); return dst

# ── Excel ─────────────────────────────────────────────────────────────────────

def excel_to_pdf(src,dst):
    out_dir=str(Path(dst).parent); result=lo_convert(src,"pdf",out_dir)
    if str(result)!=str(dst): shutil.move(result,dst); return dst

def excel_to_csv(src,dst,sheet_index=0):
    if not HAS_OPENPYXL: raise ImportError("pip install openpyxl")
    wb=openpyxl.load_workbook(src,read_only=True,data_only=True)
    sheet=wb.worksheets[sheet_index]; os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        for row in sheet.iter_rows(values_only=True): writer.writerow([v if v is not None else "" for v in row])
    wb.close(); return dst

def excel_to_txt(src,dst):
    if not HAS_OPENPYXL: raise ImportError("pip install openpyxl")
    wb=openpyxl.load_workbook(src,read_only=True,data_only=True); lines=[]
    for ws in wb.worksheets:
        lines.append(f"\n{'='*50}\nSHEET: {ws.title}\n{'='*50}")
        for row in ws.iter_rows(values_only=True):
            lines.append("\t".join(str(v) if v is not None else "" for v in row))
    wb.close(); Path(dst).write_text("\n".join(lines),encoding="utf-8"); return dst

def excel_to_html(src,dst):
    if not HAS_OPENPYXL: raise ImportError("pip install openpyxl")
    wb=openpyxl.load_workbook(src,read_only=True,data_only=True)
    parts=[f"<html><head><meta charset='utf-8'><title>{Path(src).stem}</title>"
           f"<style>body{{font-family:sans-serif;padding:2em}}"
           f"table{{border-collapse:collapse;margin-bottom:2em}}"
           f"td,th{{border:1px solid #ccc;padding:4px 10px;font-size:13px}}"
           f"th{{background:#f0f0f0}}</style></head><body>"]
    for ws in wb.worksheets:
        parts.append(f"<h2>{ws.title}</h2><table>"); first=True
        for row in ws.iter_rows(values_only=True):
            tag="th" if first else "td"
            cells="".join(f"<{tag}>{str(v) if v is not None else ''}</{tag}>" for v in row)
            parts.append(f"<tr>{cells}</tr>"); first=False
        parts.append("</table>")
    wb.close(); Path(dst).write_text("\n".join(parts),encoding="utf-8"); return dst

def excel_to_docx(src,dst):
    if not(HAS_OPENPYXL and HAS_DOCX): raise ImportError("pip install openpyxl python-docx")
    wb=openpyxl.load_workbook(src,read_only=True,data_only=True); doc=Document()
    doc.add_heading(Path(src).stem,0)
    for ws in wb.worksheets:
        doc.add_heading(ws.title,2); rows=list(ws.iter_rows(values_only=True))
        if not rows: continue
        ncols=max(len(r) for r in rows)
        table=doc.add_table(rows=len(rows),cols=ncols); table.style="Table Grid"
        for ri,row in enumerate(rows):
            for ci,val in enumerate(row):
                cell=table.cell(ri,ci); cell.text=str(val) if val is not None else ""
                if ri==0:
                    for run in cell.paragraphs[0].runs: run.bold=True
        doc.add_paragraph()
    wb.close(); doc.save(dst); return dst

# ── CSV ───────────────────────────────────────────────────────────────────────

def csv_to_xlsx(src,dst):
    if not HAS_OPENPYXL: raise ImportError("pip install openpyxl")
    wb=openpyxl.Workbook(); ws=wb.active; ws.title="Sheet1"
    delim="\t" if src.lower().endswith(".tsv") else ","
    with open(src,newline="",encoding="utf-8",errors="replace") as f:
        for row in csv.reader(f,delimiter=delim): ws.append(row)
    os.makedirs(str(Path(dst).parent),exist_ok=True); wb.save(dst); return dst

def csv_to_pdf(src,dst):
    if not HAS_REPORTLAB: raise ImportError("pip install reportlab")
    from reportlab.lib.pagesizes import A4,landscape
    from reportlab.platypus import SimpleDocTemplate,Table,TableStyle,Paragraph,Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    rows=[]; delim="\t" if src.lower().endswith(".tsv") else ","
    with open(src,newline="",encoding="utf-8",errors="replace") as f:
        for row in csv.reader(f,delimiter=delim): rows.append(row)
    if not rows: raise ValueError("CSV empty")
    doc=SimpleDocTemplate(dst,pagesize=landscape(A4),leftMargin=10*mm,rightMargin=10*mm,topMargin=10*mm,bottomMargin=10*mm)
    styles=getSampleStyleSheet(); story=[Paragraph(Path(src).stem,styles["Title"]),Spacer(1,6)]
    ncols=max(len(r) for r in rows); padded=[r+[""]*(ncols-len(r)) for r in rows]
    t=Table(padded,repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#7c6af7")),
                            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                            ("FONTSIZE",(0,0),(-1,-1),8),
                            ("GRID",(0,0),(-1,-1),0.5,colors.grey),
                            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f5f5")]),
                            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("PADDING",(0,0),(-1,-1),4)]))
    story.append(t); doc.build(story); return dst

def csv_to_html(src,dst):
    rows=[]; delim="\t" if src.lower().endswith(".tsv") else ","
    with open(src,newline="",encoding="utf-8",errors="replace") as f:
        for row in csv.reader(f,delimiter=delim): rows.append(row)
    parts=[f"<html><head><meta charset='utf-8'><style>body{{font-family:sans-serif;padding:2em}}"
           f"table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:5px 12px;"
           f"font-size:13px}}th{{background:#e8e8f0}}</style></head><body>"
           f"<h2>{Path(src).stem}</h2><table>"]
    for i,row in enumerate(rows):
        tag="th" if i==0 else "td"
        cells="".join(f"<{tag}>{str(v).replace('&','&amp;').replace('<','&lt;')}</{tag}>" for v in row)
        parts.append(f"<tr>{cells}</tr>")
    parts.append("</table></body></html>")
    Path(dst).write_text("\n".join(parts),encoding="utf-8"); return dst

def csv_to_docx(src,dst):
    if not HAS_DOCX: raise ImportError("pip install python-docx")
    rows=[]; delim="\t" if src.lower().endswith(".tsv") else ","
    with open(src,newline="",encoding="utf-8",errors="replace") as f:
        for row in csv.reader(f,delimiter=delim): rows.append(row)
    if not rows: raise ValueError("CSV empty")
    doc=Document(); doc.add_heading(Path(src).stem,0)
    ncols=max(len(r) for r in rows); padded=[r+[""]*(ncols-len(r)) for r in rows]
    table=doc.add_table(rows=len(padded),cols=ncols); table.style="Table Grid"
    for ri,row in enumerate(padded):
        for ci,val in enumerate(row):
            cell=table.cell(ri,ci); cell.text=val
            if ri==0:
                for run in cell.paragraphs[0].runs: run.bold=True
    doc.save(dst); return dst

# ── PPTX ──────────────────────────────────────────────────────────────────────

def pptx_to_pdf(src,dst):
    out_dir=str(Path(dst).parent); result=lo_convert(src,"pdf",out_dir)
    if str(result)!=str(dst): shutil.move(result,dst); return dst

def pptx_to_images(src,dst_dir,fmt="png",dpi=150):
    if not HAS_PDF2IMAGE: raise ImportError("pip install pdf2image (+poppler)")
    os.makedirs(dst_dir,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_pdf=os.path.join(tmp,Path(src).stem+".pdf")
        pptx_to_pdf(src,tmp_pdf)
        imgs=convert_from_path(tmp_pdf,dpi=dpi,fmt=fmt); out=[]
        for i,img in enumerate(imgs):
            p=os.path.join(dst_dir,f"slide_{i+1}.{fmt}"); img.save(p); out.append(p)
    return out

def pptx_to_txt(src,dst):
    if not HAS_PPTX: raise ImportError("pip install python-pptx")
    prs=Presentation(src); lines=[]
    for i,slide in enumerate(prs.slides,1):
        lines.append(f"\n{'='*50}\nSLIDE {i}\n{'='*50}")
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t=para.text.strip()
                    if t: lines.append(t)
    Path(dst).write_text("\n".join(lines),encoding="utf-8"); return dst

def pptx_to_html(src,dst):
    if not HAS_PPTX: raise ImportError("pip install python-pptx")
    prs=Presentation(src)
    parts=[f"<html><head><meta charset='utf-8'><title>{Path(src).stem}</title>"
           f"<style>body{{font-family:Georgia,serif;max-width:900px;margin:auto;padding:2em}}"
           f".slide{{border:1px solid #ddd;margin-bottom:2em;padding:1.5em;border-radius:4px}}"
           f"h2{{color:#7c6af7}}</style></head><body><h1>{Path(src).stem}</h1>"]
    for i,slide in enumerate(prs.slides,1):
        parts.append(f'<div class="slide"><h2>Slide {i}</h2>')
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t=para.text.strip()
                    if t:
                        safe=t.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
                        parts.append(f"<p>{safe}</p>")
        parts.append("</div>")
    parts.append("</body></html>")
    Path(dst).write_text("\n".join(parts),encoding="utf-8"); return dst

def pptx_to_docx(src,dst):
    if not(HAS_PPTX and HAS_DOCX): raise ImportError("pip install python-pptx python-docx")
    prs=Presentation(src); doc=Document(); doc.add_heading(Path(src).stem,0)
    for i,slide in enumerate(prs.slides,1):
        doc.add_heading(f"Slide {i}",2)
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t=para.text.strip()
                    if t: doc.add_paragraph(t)
        doc.add_page_break()
    doc.save(dst); return dst

def pptx_slide_count(src):
    if not HAS_PPTX: return 0
    return len(Presentation(src).slides)

def pptx_split_slides(src,out_dir,prefix="slide"):
    if not HAS_PPTX: raise ImportError("pip install python-pptx")
    import copy
    os.makedirs(out_dir,exist_ok=True); prs=Presentation(src); out=[]
    for i,slide in enumerate(prs.slides):
        new_prs=Presentation(); new_prs.slide_width=prs.slide_width; new_prs.slide_height=prs.slide_height
        new_slide=new_prs.slides.add_slide(new_prs.slide_layouts[6])
        for shape in slide.shapes:
            new_slide.shapes._spTree.insert(2,copy.deepcopy(shape.element))
        p=os.path.join(out_dir,f"{prefix}_{i+1}.pptx"); new_prs.save(p); out.append(p)
    return out

def pptx_merge(src_list,dst):
    if not HAS_PPTX: raise ImportError("pip install python-pptx")
    import copy
    base_prs=Presentation(src_list[0])
    for src in src_list[1:]:
        src_prs=Presentation(src)
        for slide in src_prs.slides:
            new_slide=base_prs.slides.add_slide(base_prs.slide_layouts[6])
            for shape in slide.shapes:
                new_slide.shapes._spTree.insert(2,copy.deepcopy(shape.element))
    os.makedirs(str(Path(dst).parent),exist_ok=True); base_prs.save(dst); return dst

# ── DOCX ──────────────────────────────────────────────────────────────────────

def docx_to_txt(src,dst):
    if not HAS_DOCX: raise ImportError("pip install python-docx")
    doc=Document(src)
    Path(dst).write_text("\n".join(p.text for p in doc.paragraphs),encoding="utf-8"); return dst

def docx_to_html(src,dst):
    if not HAS_DOCX: raise ImportError("pip install python-docx")
    doc=Document(src)
    parts=[f"<html><head><meta charset='utf-8'><title>{Path(src).stem}</title>"
           f"<style>body{{font-family:Georgia,serif;max-width:860px;margin:auto;padding:2em}}</style></head><body>"]
    for p in doc.paragraphs:
        if p.style.name.startswith("Heading"):
            lvl=p.style.name[-1] if p.style.name[-1].isdigit() else "2"
            parts.append(f"<h{lvl}>{p.text}</h{lvl}>")
        else:
            safe=p.text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            parts.append(f"<p>{safe}</p>")
    parts.append("</body></html>")
    Path(dst).write_text("\n".join(parts),encoding="utf-8"); return dst

def docx_to_pdf(src,dst):
    out_dir=str(Path(dst).parent); result=lo_convert(src,"pdf",out_dir)
    if str(result)!=str(dst): shutil.move(result,dst); return dst

# ── TXT ───────────────────────────────────────────────────────────────────────

def txt_to_pdf(src,dst):
    if not HAS_REPORTLAB: raise ImportError("pip install reportlab")
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
    from reportlab.lib.units import mm
    text=Path(src).read_text(encoding="utf-8",errors="replace")
    doc=SimpleDocTemplate(dst,pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=20*mm,bottomMargin=20*mm)
    styles=getSampleStyleSheet(); story=[]
    for line in text.split("\n"):
        safe=line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") or "&nbsp;"
        story.append(Paragraph(safe,styles["Normal"])); story.append(Spacer(1,2))
    doc.build(story); return dst

def txt_to_docx(src,dst):
    if not HAS_DOCX: raise ImportError("pip install python-docx")
    doc=Document(); doc.add_heading(Path(src).stem,0)
    for line in Path(src).read_text(encoding="utf-8",errors="replace").split("\n"): doc.add_paragraph(line)
    doc.save(dst); return dst

def txt_to_html(src,dst):
    text=Path(src).read_text(encoding="utf-8",errors="replace")
    safe=text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    Path(dst).write_text(f"<html><head><meta charset='utf-8'>"
                          f"<style>body{{font-family:monospace;max-width:900px;margin:auto;padding:2em}}</style></head>"
                          f"<body><pre>{safe}</pre></body></html>",encoding="utf-8"); return dst

# ── HTML ──────────────────────────────────────────────────────────────────────

def html_to_txt(src,dst):
    html=Path(src).read_text(encoding="utf-8",errors="replace")
    text=re.sub(r"<[^>]+>","",html)
    for ent,rep in [("&nbsp;"," "),("&amp;","&"),("&lt;","<"),("&gt;",">")]: text=text.replace(ent,rep)
    Path(dst).write_text(text.strip(),encoding="utf-8"); return dst

def html_to_pdf(src,dst):
    if HAS_WEASYPRINT:
        from weasyprint import HTML; HTML(filename=src).write_pdf(dst); return dst
    wk=shutil.which("wkhtmltopdf")
    if wk:
        r=subprocess.run([wk,src,dst],capture_output=True)
        if Path(dst).exists(): return dst
    raise ImportError("HTML→PDF needs:  pip install weasyprint")

# ── Image ─────────────────────────────────────────────────────────────────────

def image_convert(src,dst):
    if not HAS_PIL: raise ImportError("pip install Pillow")
    img=Image.open(src); ext=Path(dst).suffix.lower()
    if ext in (".jpg",".jpeg",".bmp") and img.mode in ("RGBA","P","LA"): img=img.convert("RGB")
    if ext==".ico": img=img.resize((256,256),Image.LANCZOS)
    img.save(dst); return dst

def images_to_pdf(src_list,dst):
    if not HAS_PIL: raise ImportError("pip install Pillow")
    imgs=[Image.open(p).convert("RGB") for p in src_list]
    if imgs: imgs[0].save(dst,save_all=True,append_images=imgs[1:]); return dst

# ── Audio/Video ───────────────────────────────────────────────────────────────

def ffmpeg_convert(src,dst,extra=None):
    if not HAS_FFMPEG: raise RuntimeError("ffmpeg not found.\n  sudo apt install ffmpeg")
    cmd=["ffmpeg","-y","-i",src]+(extra or [])+[dst]
    r=subprocess.run(cmd,capture_output=True,text=True)
    if not Path(dst).exists(): raise RuntimeError(f"ffmpeg failed:\n{r.stderr[-400:]}")
    return dst

# ── Video / Audio operations ──────────────────────────────────────────────────

def video_get_duration(src: str) -> float:
    """Return video/audio duration in seconds using ffprobe."""
    if not HAS_FFMPEG:
        raise RuntimeError("ffmpeg not found.")
    cmd = ["ffprobe", "-v", "error",
           "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1",
           src]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except (ValueError, TypeError):
        raise RuntimeError(f"Could not read duration from: {Path(src).name}\n{r.stderr[:300]}")

def _parse_time(t: str) -> float:
    """
    Parse a time string into seconds.
    Accepts:  HH:MM:SS  |  MM:SS  |  SS  |  SS.ms
    e.g.  "1:30:00" → 5400.0   "2:45" → 165.0   "90" → 90.0
    """
    t = t.strip()
    parts = t.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0])*60 + float(parts[1])
        else:
            return float(parts[0])
    except (ValueError, IndexError):
        raise ValueError(
            f"Invalid time format: '{t}'\n"
            "Use HH:MM:SS, MM:SS, or seconds (e.g. 90 or 1:30)"
        )

def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS string."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"

def video_split(src: str, segments: list, out_dir: str,
                prefix: str = "segment", fmt: str = "") -> list:
    """
    Split a video into segments by time.

    segments: list of (start, end) tuples — each a time string or float seconds.
              e.g. [("0", "1:30"), ("1:30", "3:00"), ("3:00", "end")]
              Use "end" or "" as end time to mean the rest of the file.
    out_dir:  output directory
    prefix:   filename prefix
    fmt:      output extension (e.g. "mp4"); defaults to same as input

    Returns list of output file paths.
    """
    if not HAS_FFMPEG:
        raise RuntimeError("ffmpeg not found.\n  sudo apt install ffmpeg")
    os.makedirs(out_dir, exist_ok=True)
    ext = fmt.lstrip(".") if fmt else Path(src).suffix.lstrip(".")
    duration = video_get_duration(src)
    out_files = []

    for i, (start_raw, end_raw) in enumerate(segments, 1):
        start_sec = _parse_time(str(start_raw))

        # "end" or empty string means until the end of the file
        if str(end_raw).strip().lower() in ("end", "", "0"):
            end_sec = duration
        else:
            end_sec = _parse_time(str(end_raw))

        if end_sec <= start_sec:
            raise ValueError(
                f"Segment {i}: end time ({end_raw}) must be after start time ({start_raw})"
            )

        seg_dur = end_sec - start_sec
        start_fmt = start_raw.replace(":", "-")
        end_fmt   = str(end_raw).replace(":", "-")
        out_path = os.path.join(out_dir, f"{prefix}_{i:02d}_{start_fmt}_to_{end_fmt}.{ext}")

        cmd = [
            "ffmpeg", "-y",
            "-i", src,
            "-ss", str(start_sec),
            "-t",  str(seg_dur),
            "-c",  "copy",          # stream copy = fast, no re-encode
            out_path
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if not Path(out_path).exists():
            raise RuntimeError(
                f"ffmpeg failed on segment {i}:\n{r.stderr[-400:]}"
            )
        out_files.append(out_path)

    return out_files

def video_merge(src_list: list, dst: str, log=None) -> str:
    """
    Merge multiple video (or audio) files into one using ffmpeg concat demuxer.
    All files should have the same codec/resolution for best results.
    Falls back to re-encode if streams differ.
    """
    if not HAS_FFMPEG:
        raise RuntimeError("ffmpeg not found.\n  sudo apt install ffmpeg")
    if not src_list:
        raise ValueError("No files provided for merge.")

    def L(m):
        if log: log(m)

    os.makedirs(str(Path(dst).parent), exist_ok=True)

    # Write concat list file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                     delete=False, encoding="utf-8") as tf:
        list_path = tf.name
        for s in src_list:
            # ffmpeg concat requires escaped paths
            escaped = s.replace("'", "'\\''")
            tf.write(f"file '{escaped}'\n")

    L(f"Merging {len(src_list)} files …")
    try:
        # First try stream-copy (fast, no quality loss)
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            dst
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if Path(dst).exists():
            L("Merged with stream copy (fast, lossless).")
            return dst

        # Fall back to re-encode if stream copy failed
        L("Stream copy failed — re-encoding (slower but compatible) …")
        cmd2 = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            dst
        ]
        r2 = subprocess.run(cmd2, capture_output=True, text=True)
        if not Path(dst).exists():
            raise RuntimeError(f"ffmpeg merge failed:\n{r2.stderr[-600:]}")
        L("Merged with re-encode.")
        return dst
    finally:
        try:
            os.unlink(list_path)
        except OSError:
            pass

def audio_split(src: str, segments: list, out_dir: str,
                prefix: str = "segment", fmt: str = "") -> list:
    """Split an audio file by time — identical logic to video_split."""
    return video_split(src, segments, out_dir, prefix, fmt)

# ── PDF operations ────────────────────────────────────────────────────────────

def split_each(src,out_dir,prefix="page"):
    os.makedirs(out_dir,exist_ok=True); reader=PdfReader(src); out=[]
    for i,page in enumerate(reader.pages):
        w=PdfWriter(); w.add_page(page)
        p=os.path.join(out_dir,f"{prefix}_{i+1}.pdf")
        with open(p,"wb") as f: w.write(f); out.append(p)
    return out

def split_range(src,start,end,out_dir,prefix="range"):
    os.makedirs(out_dir,exist_ok=True); reader=PdfReader(src); total=len(reader.pages)
    start,end=max(1,start),min(total,end); w=PdfWriter()
    for i in range(start-1,end): w.add_page(reader.pages[i])
    p=os.path.join(out_dir,f"{prefix}_pages{start}-{end}.pdf")
    with open(p,"wb") as f: w.write(f); return p

def split_custom(src,groups,out_dir,prefix="group"):
    os.makedirs(out_dir,exist_ok=True); reader=PdfReader(src); total=len(reader.pages); out=[]
    for idx,group in enumerate(groups):
        w=PdfWriter(); valid=[p for p in group if 1<=p<=total]
        for pg in valid: w.add_page(reader.pages[pg-1])
        if valid:
            label="_".join(str(p) for p in valid)
            p=os.path.join(out_dir,f"{prefix}{idx+1}_p{label}.pdf")
            with open(p,"wb") as f: w.write(f); out.append(p)
    return out

def merge_pdfs(src_list,dst):
    if not HAS_PYPDF: raise ImportError("pip install pypdf")
    w=PdfWriter()
    for src in src_list:
        c=cat(src)
        if c=="pdf":
            for page in PdfReader(src).pages: w.add_page(page)
        elif c=="image":
            with tempfile.NamedTemporaryFile(suffix=".pdf",delete=False) as tf: tmp=tf.name
            images_to_pdf([src],tmp)
            for page in PdfReader(tmp).pages: w.add_page(page); os.unlink(tmp)
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def resequence_pdf(src,order,dst):
    reader=PdfReader(src); total=len(reader.pages); w=PdfWriter()
    for pg in order:
        if 1<=pg<=total: w.add_page(reader.pages[pg-1])
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def delete_pages(src,pages_to_delete,dst):
    reader=PdfReader(src); total=len(reader.pages); remove=set(pages_to_delete); w=PdfWriter()
    for i in range(total):
        if (i+1) not in remove: w.add_page(reader.pages[i])
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def rotate_pages(src,degrees,pages_to_rotate,dst):
    reader=PdfReader(src); total=len(reader.pages)
    target=set(pages_to_rotate) if pages_to_rotate else set(range(1,total+1)); w=PdfWriter()
    for i,page in enumerate(reader.pages):
        if (i+1) in target: page.rotate(degrees); w.add_page(page)
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def reverse_pdf(src,dst):
    reader=PdfReader(src)
    return resequence_pdf(src,list(range(len(reader.pages),0,-1)),dst)

def compress_pdf(src,dst):
    reader=PdfReader(src); w=PdfWriter()
    for page in reader.pages: page.compress_content_streams(); w.add_page(page)
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def encrypt_pdf(src,dst,user_pw,owner_pw=""):
    reader=PdfReader(src); w=PdfWriter()
    for page in reader.pages: w.add_page(page)
    w.encrypt(user_pw,owner_pw or user_pw)
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def decrypt_pdf(src,dst,password):
    reader=PdfReader(src)
    if reader.is_encrypted:
        if reader.decrypt(password)==0: raise ValueError("Wrong password")
    w=PdfWriter()
    for page in reader.pages: w.add_page(page)
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def watermark_text(src,dst,text,opacity=0.3,fontsize=48,color="#888888",angle=45,pages=None):
    if not(HAS_PIL and HAS_PDF2IMAGE): raise ImportError("pip install Pillow pdf2image (+poppler)")
    reader=PdfReader(src); total=len(reader.pages)
    target=set(pages) if pages else set(range(1,total+1)); w=PdfWriter()
    imgs=convert_from_path(src,dpi=150)
    for i,img in enumerate(imgs):
        pg=i+1
        if pg in target:
            try: font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",fontsize)
            except:
                try: font=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",fontsize)
                except: font=ImageFont.load_default()
            try: r,g,b=int(color[1:3],16),int(color[3:5],16),int(color[5:7],16)
            except: r,g,b=128,128,128
            alpha=int(opacity*255); txt_img=Image.new("RGBA",img.size,(0,0,0,0))
            draw=ImageDraw.Draw(txt_img); bbox=draw.textbbox((0,0),text,font=font)
            tw,th=bbox[2]-bbox[0],bbox[3]-bbox[1]
            draw.text((img.size[0]//2-tw//2,img.size[1]//2-th//2),text,font=font,fill=(r,g,b,alpha))
            txt_img=txt_img.rotate(angle,expand=False)
            img=Image.alpha_composite(img.convert("RGBA"),txt_img)
        with tempfile.NamedTemporaryFile(suffix=".pdf",delete=False) as tf: tmp=tf.name
        img.convert("RGB").save(tmp,"PDF")
        for page in PdfReader(tmp).pages: w.add_page(page); os.unlink(tmp)
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def watermark_pdf_overlay(src,wm_pdf,dst,pages=None):
    reader=PdfReader(src); wm_page=PdfReader(wm_pdf).pages[0]
    total=len(reader.pages); target=set(pages) if pages else set(range(1,total+1)); w=PdfWriter()
    for i,page in enumerate(reader.pages):
        if (i+1) in target: page.merge_page(wm_page); w.add_page(page)
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

def get_metadata(src):
    reader=PdfReader(src); meta=reader.metadata or {}; size=os.path.getsize(src)
    return {"File":Path(src).name,"Pages":len(reader.pages),
            "Size":f"{size/1024:.1f} KB","Title":meta.get("/Title","—"),
            "Author":meta.get("/Author","—"),"Subject":meta.get("/Subject","—"),
            "Creator":meta.get("/Creator","—"),"Producer":meta.get("/Producer","—")}

def set_metadata(src,dst,fields):
    reader=PdfReader(src); w=PdfWriter()
    for page in reader.pages: w.add_page(page)
    existing=dict(reader.metadata or {})
    mapping={"title":"/Title","author":"/Author","subject":"/Subject","creator":"/Creator"}
    for k,v in fields.items():
        pk=mapping.get(k.lower())
        if pk and v.strip(): existing[pk]=v.strip()
    w.add_metadata(existing)
    os.makedirs(str(Path(dst).parent),exist_ok=True)
    with open(dst,"wb") as f: w.write(f); return dst

# ── Master dispatch ───────────────────────────────────────────────────────────

def do_convert(src,out_fmt,out_dir,pages_str="",dpi=150,log=None):
    def L(m): log(m) if log else None
    c=cat(src); stem=Path(src).stem; out_fmt=out_fmt.lower().lstrip(".")
    os.makedirs(out_dir,exist_ok=True)
    total=pdf_page_count(src) if c=="pdf" and HAS_PYPDF else 0
    pages=parse_pages(pages_str,total) if pages_str.strip() and total else None
    if c=="pdf":
        dst=os.path.join(out_dir,stem+f".{out_fmt}")
        if out_fmt=="txt": L("PDF→TXT"); return [pdf_to_txt(src,dst,pages)]
        if out_fmt=="docx": L("PDF→DOCX"); return [pdf_to_docx(src,dst,pages)]
        if out_fmt in("png","jpg","jpeg"):
            L(f"PDF→{out_fmt.upper()}"); return pdf_to_images(src,os.path.join(out_dir,stem+"_images"),out_fmt,pages,dpi)
        if out_fmt=="html": L("PDF→HTML"); return [pdf_to_html(src,dst,pages)]
        if out_fmt in("xlsx","xls"): L("PDF→XLSX"); return [pdf_to_xlsx(src,dst.replace(f".{out_fmt}",".xlsx"))]
        if out_fmt=="pptx": L("PDF→PPTX"); return [pdf_to_pptx(src,dst,dpi)]
        if out_fmt=="csv": xls=dst.replace(".csv",".xlsx"); pdf_to_xlsx(src,xls); return [excel_to_csv(xls,dst)]
    if c=="excel":
        dst=os.path.join(out_dir,stem+f".{out_fmt}")
        if out_fmt=="pdf": L("XLSX→PDF"); return [excel_to_pdf(src,dst)]
        if out_fmt=="csv": L("XLSX→CSV"); return [excel_to_csv(src,dst)]
        if out_fmt=="txt": L("XLSX→TXT"); return [excel_to_txt(src,dst)]
        if out_fmt=="html": L("XLSX→HTML"); return [excel_to_html(src,dst)]
        if out_fmt=="docx": L("XLSX→DOCX"); return [excel_to_docx(src,dst)]
        if out_fmt in("xlsx","xls","ods"): return [lo_convert(src,out_fmt,out_dir)]
    if c=="csv":
        dst=os.path.join(out_dir,stem+f".{out_fmt}")
        if out_fmt in("xlsx","xls"): L("CSV→XLSX"); return [csv_to_xlsx(src,dst.replace(f".{out_fmt}",".xlsx"))]
        if out_fmt=="pdf": L("CSV→PDF"); return [csv_to_pdf(src,dst)]
        if out_fmt=="html": L("CSV→HTML"); return [csv_to_html(src,dst)]
        if out_fmt=="txt": shutil.copy(src,dst); return [dst]
        if out_fmt=="docx": L("CSV→DOCX"); return [csv_to_docx(src,dst)]
    if c=="pptx":
        dst=os.path.join(out_dir,stem+f".{out_fmt}")
        if out_fmt=="pdf": L("PPTX→PDF"); return [pptx_to_pdf(src,dst)]
        if out_fmt in("png","jpg","jpeg"): L(f"PPTX→{out_fmt.upper()}"); return pptx_to_images(src,os.path.join(out_dir,stem+"_slides"),out_fmt,dpi)
        if out_fmt=="txt": L("PPTX→TXT"); return [pptx_to_txt(src,dst)]
        if out_fmt=="html": L("PPTX→HTML"); return [pptx_to_html(src,dst)]
        if out_fmt=="docx": L("PPTX→DOCX"); return [pptx_to_docx(src,dst)]
    if c=="docx":
        dst=os.path.join(out_dir,stem+f".{out_fmt}")
        if out_fmt=="pdf": L("DOCX→PDF"); return [docx_to_pdf(src,dst)]
        if out_fmt=="txt": L("DOCX→TXT"); return [docx_to_txt(src,dst)]
        if out_fmt=="html": L("DOCX→HTML"); return [docx_to_html(src,dst)]
    if c=="txt":
        dst=os.path.join(out_dir,stem+f".{out_fmt}")
        if out_fmt=="pdf": L("TXT→PDF"); return [txt_to_pdf(src,dst)]
        if out_fmt=="docx": L("TXT→DOCX"); return [txt_to_docx(src,dst)]
        if out_fmt=="html": L("TXT→HTML"); return [txt_to_html(src,dst)]
    if c=="html":
        dst=os.path.join(out_dir,stem+f".{out_fmt}")
        if out_fmt=="pdf": L("HTML→PDF"); return [html_to_pdf(src,dst)]
        if out_fmt=="txt": L("HTML→TXT"); return [html_to_txt(src,dst)]
    if c=="image":
        if out_fmt=="pdf": dst=os.path.join(out_dir,stem+".pdf"); L("Image→PDF"); return [images_to_pdf([src],dst)]
        dst=os.path.join(out_dir,stem+"."+out_fmt); L(f"Image→{out_fmt.upper()}"); return [image_convert(src,dst)]
    if c in("video","audio"):
        dst=os.path.join(out_dir,stem+"."+out_fmt); L(f"{c.upper()}→{out_fmt.upper()}")
        if out_fmt=="gif": return [ffmpeg_convert(src,dst,["-vf","fps=10,scale=480:-1:flags=lanczos","-loop","0"])]
        return [ffmpeg_convert(src,dst)]
    raise ValueError(f"No conversion: {c} → {out_fmt}")
