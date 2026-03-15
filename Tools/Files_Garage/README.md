# File Workshop — Universal Local Converter

A desktop GUI tool for converting, splitting, and transforming files.
Runs fully offline. No internet required.

---

## Supported Conversions

| Input       | Output options                                        |
|-------------|-------------------------------------------------------|
| PDF         | TXT, DOCX, PNG, JPG, HTML                             |
| Images      | PNG, JPG, WEBP, BMP, GIF, TIFF, ICO, PDF             |
| Word (.docx)| PDF, TXT, HTML                                        |
| Text (.txt) | PDF, DOCX, HTML                                       |
| HTML        | PDF, TXT                                              |
| Video       | MP4, AVI, MOV, MKV, WEBM, GIF, MP3, WAV              |
| Audio       | MP3, WAV, OGG, FLAC, AAC, M4A                        |

---

## Quick Setup

### 1. Python
Requires Python 3.8+. Get it from https://python.org

### 2. Install Python packages
```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install pypdf pdfplumber python-docx reportlab Pillow pdf2image weasyprint
```

### 3. System packages (for full feature support)

**ffmpeg** (audio/video conversions):
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html and add to PATH
```

**poppler** (PDF → PNG/JPG images):
```bash
# Ubuntu/Debian
sudo apt install poppler-utils

# macOS
brew install poppler

# Windows
# Download from https://github.com/oschwartz10612/poppler-windows
# Extract and add the /bin folder to your system PATH
```

**LibreOffice** (DOCX → PDF, the best option):
```bash
# Ubuntu/Debian
sudo apt install libreoffice

# macOS / Windows
# Download from https://libreoffice.org
```

### 4. Run the tool
```bash
python3 file_workshop.py
```

Windows: double-click `run.bat`
Mac/Linux: `./run.sh` or `python3 file_workshop.py`

---

## How to Use

1. Click **+ Add Files** to load one or more files into the queue
2. Set your **Output Folder** in the left sidebar (auto-fills from first file)
3. Switch between tabs:
   - **Convert tab** — pick a format, set options, click ▶ RUN
   - **PDF Split tab** — choose split mode, click ▶ RUN
   - **File Queue tab** — view and manage queued files
   - **Help tab** — built-in reference

### Batch conversion
Add multiple files of different types. They will all be converted to the same
output format you selected. Incompatible combinations are reported in the log
without stopping the rest.

### PDF Split — Custom Groups
Use the `|` separator to define groups, commas for page lists, `-` for ranges:
```
1,10 | 3,5 | 2-4,7
```
Creates 3 output PDFs:
- pages 1 and 10
- pages 3 and 5
- pages 2, 3, 4, and 7

### Page filter (Convert tab)
Applies when converting PDFs. Examples:
- `1,3,5-8` → pages 1, 3, 5, 6, 7, 8
- `2-10` → pages 2 through 10
- (blank) → all pages

---

## Dependency Status

The top-right of the app shows `deps: N/6 ✓`. Hover over it to see exactly which
packages are installed and what to run to install the missing ones.

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| `No module named 'pypdf'` | `pip install pypdf` |
| `No module named 'docx'` | `pip install python-docx` |
| `No module named 'pdfplumber'` | `pip install pdfplumber` |
| PDF→image fails | `pip install pdf2image` + install poppler |
| DOCX→PDF fails | Install LibreOffice or `pip install docx2pdf` |
| Audio/video fails | `sudo apt install ffmpeg` |
| `tkinter` not found (Linux) | `sudo apt install python3-tk` |
| HTML→PDF fails | `pip install weasyprint` |

---

## Roadmap / Future
- [ ] Drag & drop file loading
- [ ] Per-file format selection in queue
- [ ] Progress bar per file
- [ ] Android/mobile port using Kivy or BeeWare
