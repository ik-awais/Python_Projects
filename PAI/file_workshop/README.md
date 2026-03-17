# File Workshop AI
### Multimodal Intelligence Layer for File Management

A professional desktop application that combines a full-featured file conversion
and manipulation toolkit with a built-in Gemini AI assistant.

---

## Architecture

```
ai_workshop/
├── main.py              ← Entry point
├── config.py            ← Settings, colours, fonts
├── requirements.txt
│
├── ai/
│   ├── gemini.py        ← Gemini API client (all AI features)
│   └── extractor.py     ← Extract text from any file type for AI
│
├── core/
│   └── processor.py     ← All file operations (convert/split/merge/etc.)
│
└── ui/
    └── app.py           ← Full GUI application
```

---

## Features

### 🔄 File Operations (no AI needed)
| Tool      | What it does |
|-----------|-------------|
| Convert   | PDF·DOCX·XLSX·PPTX·CSV·TXT·HTML·Images·Audio·Video → each other |
| Split     | PDF pages or PPTX slides → individual files |
| Merge     | Multiple PDFs/images/PPTXs → one file |
| Organise  | Resequence · Delete · Rotate · Reverse PDF pages |
| Stamp     | Text watermark or PDF overlay |
| Protect   | Encrypt / decrypt PDF with password |
| Compress  | Reduce PDF file size |
| Metadata  | View and edit PDF document properties |

### 🤖 AI Features (Gemini required)
| Feature          | Description |
|-----------------|-------------|
| 💬 Chat          | Natural language — ask anything about your files |
| 📄 Doc Q&A       | Ask questions answered from the document content |
| 📋 Summarise     | Intelligent summary with key points and conclusions |
| 🗂 Batch Plan    | Describe a goal → AI plans the step-by-step operations |
| 🖼 Image Analyse | Describe image content, objects, text (Gemini Vision) |
| 🎯 Format Suggest| AI recommends the best output format for your goal |
| 🏷 Metadata AI   | Analyse and suggest improvements to PDF metadata |
| 🧠 Intent Parse  | Type "convert my report to Word" → tool auto-configures |

---

## Setup

### Step 1 — Install Python 3.8+
https://python.org

### Step 2 — Install Python packages
```bash
pip install -r requirements.txt
```

### Step 3 — System packages (Ubuntu/Debian)
```bash
sudo apt install python3-tk libreoffice poppler-utils ffmpeg
```

### Step 4 — Get Gemini API Key (FREE)

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click **"Create API key"**
4. Copy the key (starts with `AIza...`)
5. Open the app → click **⚙ Settings** → paste the key → **Save**

> The free tier of Gemini API is generous — plenty for daily use.

### Step 5 — Run
```bash
python3 main.py
```

---

## How to use the AI

### Natural Language Commands
Type in the AI chat panel:
- *"Convert all my PDFs to Word format"*
- *"Split the presentation into individual slides"*
- *"What is the main topic of this document?"*
- *"Compress and protect my report with a password"*

The AI will understand your intent and auto-configure the correct tool tab.

### Document Q&A
1. Add a PDF/DOCX/XLSX/PPTX to the queue
2. Select **📄 Doc Q&A** mode in the AI panel
3. Double-click the file in the Queue to set it as active
4. Ask any question — the AI answers from the document content

### Image Analysis
1. Add any image (PNG/JPG/etc.) to the queue
2. Click **🖼 Analyse Image** in the AI panel
3. Gemini Vision describes the image in detail

### Batch Planning
1. Add multiple files of different types
2. Select **🗂 Batch Plan** mode
3. Describe your goal: *"I need to send these as a single PDF report"*
4. The AI plans and explains each step

---

## Gemini Models

| Model | Best for |
|-------|----------|
| `gemini-1.5-flash` | Fast, efficient — recommended for most tasks |
| `gemini-1.5-pro`   | More capable — complex analysis and long documents |
| `gemini-2.0-flash` | Latest, fastest — cutting edge performance |

Switch models in ⚙ Settings at any time.

---

## Conversion Reference

| Input       | Output options |
|-------------|----------------|
| PDF         | DOCX · TXT · HTML · PNG · JPG · XLSX · PPTX · CSV |
| Excel/XLSX  | PDF · CSV · TXT · HTML · DOCX |
| CSV/TSV     | XLSX · PDF · HTML · TXT · DOCX |
| PPTX        | PDF · TXT · HTML · DOCX · PNG · JPG |
| Word/DOCX   | PDF · TXT · HTML |
| TXT         | PDF · DOCX · HTML |
| HTML        | PDF · TXT |
| Images      | PNG · JPG · WEBP · BMP · GIF · TIFF · ICO · PDF |
| Video       | MP4 · AVI · MOV · MKV · WEBM · GIF · MP3 · WAV |
| Audio       | MP3 · WAV · OGG · FLAC · AAC · M4A |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'google.generativeai'` | `pip install google-generativeai` |
| `No module named 'pypdf'` | `pip install pypdf` |
| `No module named 'docx'` | `pip install python-docx` |
| `No module named 'pdfplumber'` | `pip install pdfplumber` |
| `No module named 'openpyxl'` | `pip install openpyxl` |
| `No module named 'pptx'` | `pip install python-pptx` |
| `No module named 'tkinter'` | `sudo apt install python3-tk` |
| PDF→image fails | `pip install pdf2image` + `sudo apt install poppler-utils` |
| DOCX/XLSX/PPTX→PDF fails | `sudo apt install libreoffice` |
| Audio/video fails | `sudo apt install ffmpeg` |
| AI: "invalid API key" | Check key at aistudio.google.com, re-paste in Settings |
| AI: quota exceeded | Free tier has limits; wait or upgrade at ai.google.dev |

---

## Privacy Note
- Your API key is stored locally at `~/.ai_workshop_config.json`
- Files are processed **locally** on your machine
- Only text content is sent to Gemini API when you use AI features
- Images are sent to Gemini Vision only when you click "Analyse Image"
- No file data is ever uploaded automatically

---

## Future Roadmap
- [ ] Drag & drop file loading
- [ ] AI-powered OCR on scanned PDFs
- [ ] Auto-batch from natural language plan
- [ ] Dark/light theme toggle
- [ ] Android/mobile port (Kivy)
- [ ] Plugin system for custom operations
