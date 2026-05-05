# AI FileMat - Web Version

A modern web-based file processing tool with AI capabilities, built with React and FastAPI.

## Features

- 🤖 **AI-Powered File Processing** - Natural language commands for file operations
- 📁 **Multi-Format Support** - PDF, DOCX, Excel, PowerPoint, Images, Audio, Video
- 🎨 **Modern UI** - Beautiful, responsive design with smooth animations
- ☁️ **Cloud-Ready** - Scalable web architecture
- 🔒 **Secure** - File encryption and secure processing
- 🌙 **Theme System** - Light/Dark themes with smooth transitions
- 📱 **Mobile-Friendly** - Responsive design for all devices

## Architecture

```
ai_filemat_web/
├── backend/          # FastAPI Python backend
├── frontend/         # React TypeScript frontend
├── docs/            # Documentation
└── README.md
```

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Tech Stack

- **Backend**: FastAPI, Python, SQLAlchemy
- **Frontend**: React, TypeScript, Tailwind CSS
- **AI**: OpenAI, Gemini APIs
- **Database**: PostgreSQL (development: SQLite)
- **File Storage**: Local/Cloud storage options
