# PDF Tool — Local Machine Utility

A desktop GUI tool for splitting PDFs and converting them to other formats.
Built with Python + Tkinter (no internet required, runs fully offline).

---

## Features

### Split Tab
| Mode | Description |
|------|-------------|
| **Each page → own PDF** | A 10-page PDF becomes 10 separate files |
| **Page range → one PDF** | Extract pages 3–7 into one file |
| **Custom groups** | Define arbitrary groups, e.g. `1,10 | 3,5 | 2-4,7` → 3 output files |

### Convert Tab
| Format | Notes |
|--------|-------|
| **Plain Text (.txt)** | Fast; extracts all text content |
| **Word Document (.docx)** | Creates a .docx with page headings and paragraphs |
| **PNG Images** | One image per page; adjustable DPI |
| **JPG Images** | Same as PNG but JPEG format |

You can convert all pages or specify a subset (e.g. `1,3,5-8`).

---

## Quick Start

### 1. Install Python
Download from https://python.org (version 3.8 or newer).

### 2. Install dependencies
Open a terminal / command prompt in this folder and run:

```bash
pip install -r requirements.txt
```

### 3. Install Poppler (for PNG/JPG image export only)

**Windows:**
1. Download from: https://github.com/oschwartz10612/poppler-windows/releases
2. Extract the zip (e.g. to `C:\poppler`)
3. Add `C:\poppler\Library\bin` to your system PATH
   - Search "Edit environment variables" in Start Menu
   - Edit `Path` → New → paste the bin path

**macOS:**
```bash
brew install poppler
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install poppler-utils
```

> **Note:** Poppler is only needed for PNG/JPG image export. All other features
> (split, text, docx) work without it.

### 4. Run the tool
```bash
python pdf_tool.py
```

Or on Windows, double-click `run.bat`.

---

## How to Use

### Splitting a PDF
1. Click **Browse** next to "PDF FILE" and select your PDF
2. Choose an output folder (auto-filled from PDF location)
3. Go to the **SPLIT** tab
4. Choose a mode:
   - **Each page** — just click Run
   - **Page range** — enter start and end page numbers
   - **Custom groups** — use the `page1,page2 | page3,page4` syntax
5. Optionally change the file prefix
6. Click **▶ RUN SPLIT**

**Custom groups example:**
```
1,10 | 3,5 | 2-4,7
```
This creates 3 output files:
- `split_group1_pages1_10.pdf` — contains pages 1 and 10
- `split_group2_pages3_5.pdf` — contains pages 3 and 5
- `split_group3_pages2_3_4_7.pdf` — contains pages 2, 3, 4, and 7

### Converting a PDF
1. Select your PDF file
2. Go to the **CONVERT** tab
3. Pick a format (txt / docx / png / jpg)
4. Optionally restrict pages: `1,3,5-8` or leave blank for all
5. For images, set DPI (150 = normal, 300 = print quality)
6. Click **▶ RUN CONVERT**

---

## Folder Structure After Running
```
pdf_tool_output/
├── page_1.pdf              ← from "each page" split
├── page_2.pdf
├── split_group1_pages1_10.pdf  ← from custom split
├── my_document.txt         ← from text conversion
├── my_document.docx        ← from Word conversion
└── my_document_images/     ← from image conversion
    ├── page_1.png
    └── page_2.png
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: pypdf` | Run `pip install pypdf` |
| `ModuleNotFoundError: docx` | Run `pip install python-docx` |
| `ModuleNotFoundError: pdf2image` | Run `pip install pdf2image` |
| Image export fails with "poppler" error | Install poppler (see above) |
| Text extraction gives garbled text | PDF may be scanned/image-based — OCR not supported in this version |
| tkinter not found (Linux) | Run `sudo apt install python3-tk` |

---

## Future Plans (Android / Mobile)
This tool is designed for local use. When ready to go mobile:
- The core logic (`split_*`, `pdf_to_*` functions) is portable
- Consider **Kivy** or **BeeWare** for an Android UI wrapper
- Or expose as a REST API and build a mobile frontend

---

## Requirements Summary
- Python 3.8+
- pypdf
- pdfplumber
- python-docx
- pdf2image + poppler (image export only)
