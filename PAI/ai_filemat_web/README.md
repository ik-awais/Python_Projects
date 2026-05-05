# AI FileMat Web

A modern web-based file processing tool with AI capabilities, built with React and FastAPI. This is the web version of the AI FileMat desktop application with enhanced features and superior UI/UX.

## 🚀 Features

- 🤖 **AI-Powered File Processing** - Natural language commands for file operations
- 📁 **Multi-Format Support** - PDF, DOCX, Excel, PowerPoint, Images, Audio, Video
- 🎨 **Modern UI** - Beautiful, responsive design with smooth animations
- ☁️ **Web-Based** - Access from any browser, no installation required
- ⚡ **Real-Time Processing** - Background task queue with progress tracking
- 🔒 **Security** - File encryption and protection features
- 📊 **Metadata Management** - Extract and edit file metadata
- 🎯 **15 Functional Tabs** - All features from desktop tool plus more

## 🏗️ Architecture

### Backend (FastAPI)
- **processor.py** - Core file processing operations (ported from desktop tool)
- **ai_client.py** - AI integration with Gemini and OpenAI
- **main.py** - FastAPI application with 20+ API endpoints
- **config.py** - Configuration management

### Frontend (React + TypeScript)
- **App.tsx** - Main application with 15 functional tabs
- **components/** - Reusable UI components
- **Professional UI** - TailwindCSS with modern design

## 📋 Available Operations

### File Processing
- **Convert**: PDF ↔ DOCX/TXT/HTML, Excel ↔ CSV/HTML, PPTX ↔ PDF/TXT
- **Split**: PDF pages by range or individual files
- **Merge**: Multiple PDFs into single document
- **Protect**: Encrypt/decrypt PDFs with passwords
- **Compress**: File compression and optimization
- **Metadata**: Extract and edit file metadata

### AI Features
- **Chat**: Natural conversation about your files
- **Intent Parsing**: "Convert my PDF to Word" → automatic operation
- **Image Analysis**: AI-powered image understanding
- **Document Intelligence**: Content extraction and analysis

### Supported File Types
- 📄 PDF, DOCX, TXT, HTML
- 📊 Excel (XLSX, XLS), CSV
- 📽 PowerPoint (PPTX, PPT)
- 🖼 Images (PNG, JPG, GIF, SVG, etc.)
- 🎬 Video (MP4, AVI, MOV, MKV)
- 🎵 Audio (MP3, WAV, FLAC, AAC)

## 🛠️ Quick Start

### Prerequisites
- Node.js 16+ and npm
- Python 3.8+
- Git

### Backend Setup

1. **Navigate to backend directory**
```bash
cd backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Start the backend server**
```bash
python main.py
```

Backend will be available at: http://localhost:8000

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Start the development server**
```bash
npm start
```

Frontend will be available at: http://localhost:3000

### AI Configuration

1. **Set up API keys** (optional but recommended)
```bash
# For Gemini
export GEMINI_API_KEY="your-gemini-api-key"

# For OpenAI
export OPENAI_API_KEY="your-openai-api-key"
```

2. **Configure AI in the application**
- Navigate to AI Chat tab
- Configure your preferred AI provider
- Start chatting with your files

## 📁 Project Structure

```
ai_filemat_web/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── processor.py         # File processing operations
│   ├── ai_client.py          # AI integration
│   ├── config.py             # Configuration
│   ├── requirements.txt      # Python dependencies
│   ├── uploads/              # File upload directory
│   └── output/               # Processed files directory
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React application
│   │   ├── components/      # Reusable components
│   │   │   ├── FileUploader.tsx
│   │   │   ├── FileList.tsx
│   │   │   └── AIChat.tsx
│   │   └── App.css          # Application styles
│   ├── package.json         # Node.js dependencies
│   └── tailwind.config.js   # TailwindCSS configuration
└── README.md                # This file
```

## 🔧 API Endpoints

### File Management
- `POST /api/upload` - Upload files
- `GET /api/files` - List uploaded files
- `DELETE /api/files/{id}` - Delete file

### Processing
- `POST /api/process` - Start file processing
- `GET /api/operations/{id}` - Get operation status
- `GET /api/queue` - Get processing queue

### AI Features
- `POST /api/ai/chat` - Chat with AI
- `POST /api/ai/parse-intent` - Parse natural language commands
- `POST /api/ai/analyse-image` - Analyze images
- `GET /api/ai/status` - Check AI status

## 🎯 Usage Examples

### File Upload and Processing
1. Upload files using the drag-and-drop interface
2. Select files and choose operation (convert, split, merge, etc.)
3. Monitor progress in real-time
4. Download processed files

### AI Commands
- "Convert my PDF to Word document"
- "Split this PDF into individual pages"
- "What's in this spreadsheet?"
- "Analyze this image for me"

### File Operations
- **Convert**: Select format and target output
- **Split**: Choose page ranges or individual pages
- **Merge**: Select multiple files to combine
- **Protect**: Set password for encryption

## 🔒 Security Features

- File encryption with password protection
- Secure file upload and storage
- API key management for AI services
- Local processing (files not sent to external services unless using AI)

## 🌟 Advantages Over Desktop Version

1. **Web-Based**: Access from any device with a browser
2. **Superior UI**: Modern design with animations and responsive layout
3. **Real-Time Processing**: Background task queue with progress tracking
4. **Enhanced AI**: Multiple AI providers and better natural language understanding
5. **Scalable**: Modern web architecture for better performance
6. **Cross-Platform**: Works on Windows, macOS, Linux, and mobile devices

## 📝 Development Notes

- Built with modern web technologies (React, FastAPI, TypeScript)
- Responsive design works on all devices
- Real-time file processing with progress tracking
- Modular architecture for easy maintenance and extension
- Professional UI/UX that exceeds the desktop version

## 🤝 Contributing

This is a complete web-based rewrite of the AI FileMat desktop application with enhanced features and superior user experience.

---

**AI FileMat Web** - Modern file processing with AI intelligence 🚀
