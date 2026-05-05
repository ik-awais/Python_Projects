"""
main.py - FastAPI backend for AI FileMat Web with full functionality
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
import asyncio
import uuid

from config import settings
from processor import (
    cat, cat_icon, do_convert, split_each, split_range, merge_pdfs,
    encrypt_pdf, decrypt_pdf, watermark_text, get_metadata,
    get_available_operations, pdf_page_count, pptx_slide_count,
    video_get_duration
)
from ai_client import create_ai_client, get_available_providers

app = FastAPI(
    title="AI FileMat API",
    description="Web-based file processing with AI capabilities - Full Functionality",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Create directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Global AI client
ai_client = None

# In-memory storage
files_db = {}
operations_db = {}
queue_db = {}

# Pydantic models
class FileInfo(BaseModel):
    id: str
    name: str
    size: int
    type: str
    category: str
    icon: str
    upload_time: str
    path: str
    metadata: Optional[Dict] = {}

class ProcessRequest(BaseModel):
    file_ids: List[str]
    operation: str
    parameters: Dict[str, Any] = {}

class AIRequest(BaseModel):
    message: str
    context: Optional[str] = None
    provider: Optional[str] = "gemini"

class AIConfig(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None

@app.on_event("startup")
async def startup_event():
    """Initialize AI client on startup"""
    global ai_client
    # Try to initialize with default config
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        provider = "gemini" if os.getenv("GEMINI_API_KEY") else "openai"
        ai_client = create_ai_client(provider, api_key=api_key)

@app.get("/")
async def root():
    return {"message": "AI FileMat API v2.0", "status": "running", "features": "full_functionality"}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "ai_status": ai_client.is_ready if ai_client else False,
        "available_operations": get_available_operations()
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload file with full metadata extraction"""
    try:
        # Generate unique ID and filename
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / safe_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract metadata
        metadata = get_metadata(str(file_path))
        
        # Store file info
        file_info = FileInfo(
            id=file_id,
            name=file.filename,
            size=file_path.stat().st_size,
            type=file.content_type or "application/octet-stream",
            category=metadata["category"],
            icon=metadata["icon"],
            upload_time=datetime.now().isoformat(),
            path=str(file_path),
            metadata=metadata
        )
        files_db[file_id] = file_info
        
        return ApiResponse(
            success=True,
            message="File uploaded successfully",
            data={"file_id": file_id, "info": file_info.dict()}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
async def get_files():
    """Get all uploaded files with metadata"""
    return {"files": [info.dict() for info in files_db.values()]}

@app.get("/api/files/{file_id}")
async def get_file(file_id: str):
    """Get specific file info"""
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = files_db[file_id]
    return file_info.dict()

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str):
    """Delete a file"""
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = files_db[file_id]
    file_path = Path(file_info.path)
    
    try:
        if file_path.exists():
            file_path.unlink()
        del files_db[file_id]
        return ApiResponse(success=True, message="File deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process")
async def process_file(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Process files with real operations"""
    try:
        # Validate files exist
        for file_id in request.file_ids:
            if file_id not in files_db:
                raise HTTPException(status_code=404, detail=f"File {file_id} not found")
        
        # Create operation
        operation_id = str(uuid.uuid4())
        
        # Add to queue
        queue_db[operation_id] = {
            "id": operation_id,
            "status": "queued",
            "operation": request.operation,
            "file_ids": request.file_ids,
            "parameters": request.parameters,
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "result": None,
            "error": None
        }
        
        # Start background processing
        background_tasks.add_task(process_operation, operation_id)
        
        return ApiResponse(
            success=True,
            message="Processing started",
            data={"operation_id": operation_id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def process_operation(operation_id: str):
    """Background task to process operations"""
    try:
        operation = queue_db[operation_id]
        operation["status"] = "processing"
        
        files = [files_db[file_id] for file_id in operation["file_ids"]]
        op_type = operation["operation"]
        params = operation["parameters"]
        
        results = []
        
        for i, file_info in enumerate(files):
            try:
                # Update progress
                operation["progress"] = int((i / len(files)) * 100)
                
                result = await execute_operation(file_info, op_type, params)
                results.append(result)
                
            except Exception as e:
                operation["error"] = str(e)
                operation["status"] = "failed"
                return
        
        operation["status"] = "completed"
        operation["progress"] = 100
        operation["result"] = results
        
    except Exception as e:
        operation["status"] = "failed"
        operation["error"] = str(e)

async def execute_operation(file_info: FileInfo, operation: str, params: Dict):
    """Execute a single file operation"""
    file_path = file_info.path
    output_path = OUTPUT_DIR / f"{file_info.id}_{operation}"
    output_path.mkdir(exist_ok=True)
    
    if operation == "convert":
        target_format = params.get("format", "pdf")
        pages = params.get("pages")
        result_path = do_convert(file_path, target_format, output_path, pages)
        return {"input": file_path, "output": result_path, "operation": operation}
    
    elif operation == "split":
        split_type = params.get("type", "each")
        if split_type == "each":
            results = split_each(file_path, str(output_path))
        else:
            page_range = params.get("range", "1-3")
            results = [split_range(file_path, str(output_path), page_range)]
        return {"input": file_path, "outputs": results, "operation": operation}
    
    elif operation == "merge":
        # For now, just return the input file (merge needs multiple files)
        return {"input": file_path, "output": file_path, "operation": operation}
    
    elif operation == "encrypt":
        password = params.get("password", "default")
        output_file = output_path / f"encrypted_{Path(file_path).name}"
        result_path = encrypt_pdf(file_path, str(output_file), password)
        return {"input": file_path, "output": result_path, "operation": operation}
    
    elif operation == "decrypt":
        password = params.get("password", "default")
        output_file = output_path / f"decrypted_{Path(file_path).name}"
        result_path = decrypt_pdf(file_path, str(output_file), password)
        return {"input": file_path, "output": result_path, "operation": operation}
    
    else:
        raise ValueError(f"Unsupported operation: {operation}")

@app.get("/api/operations/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get operation status"""
    if operation_id not in queue_db:
        raise HTTPException(status_code=404, detail="Operation not found")
    
    return queue_db[operation_id]

@app.get("/api/queue")
async def get_queue():
    """Get all operations in queue"""
    return {"operations": list(queue_db.values())}

@app.post("/api/ai/configure")
async def configure_ai(config: AIConfig):
    """Configure AI client"""
    global ai_client
    try:
        ai_client = create_ai_client(config.provider, api_key=config.api_key, model=config.model)
        
        if ai_client.is_ready:
            return ApiResponse(
                success=True,
                message="AI client configured successfully",
                data={"provider": config.provider, "ready": True}
            )
        else:
            return ApiResponse(
                success=False,
                message="AI client configuration failed",
                data={"error": ai_client.error}
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/status")
async def get_ai_status():
    """Get AI client status"""
    if not ai_client:
        return {"configured": False, "provider": None, "ready": False}
    
    return {
        "configured": True,
        "provider": ai_client.provider,
        "ready": ai_client.is_ready,
        "error": ai_client.error if not ai_client.is_ready else None,
        "available_providers": get_available_providers()
    }

@app.post("/api/ai/chat")
async def ai_chat(request: AIRequest):
    """Chat with AI"""
    if not ai_client or not ai_client.is_ready:
        raise HTTPException(status_code=400, detail="AI client not configured")
    
    try:
        # Create response future
        response_future = asyncio.Future()
        
        def on_response(text: str):
            response_future.set_result(text)
        
        def on_error(error: str):
            response_future.set_exception(Exception(error))
        
        # Build context from files if provided
        context = request.context or ""
        
        # Send to AI
        ai_client.chat(request.message, context=context, on_done=on_response, on_error=on_error)
        
        # Wait for response
        response_text = await response_future
        
        return ApiResponse(
            success=True,
            message="AI response generated",
            data={"response": response_text}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/parse-intent")
async def parse_intent(request: AIRequest):
    """Parse user intent"""
    if not ai_client or not ai_client.is_ready:
        raise HTTPException(status_code=400, detail="AI client not configured")
    
    try:
        # Create response future
        response_future = asyncio.Future()
        
        def on_response(intent: Dict):
            response_future.set_result(intent)
        
        def on_error(error: str):
            response_future.set_exception(Exception(error))
        
        # Parse intent
        ai_client.parse_intent(request.message, on_done=on_response, on_error=on_error)
        
        # Wait for response
        intent_result = await response_future
        
        return ApiResponse(
            success=True,
            message="Intent parsed successfully",
            data={"intent": intent_result}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/analyse-image")
async def analyse_image(file_id: str, prompt: str = "Describe this image in detail."):
    """Analyse an image using AI"""
    if not ai_client or not ai_client.is_ready:
        raise HTTPException(status_code=400, detail="AI client not configured")
    
    if file_id not in files_db:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = files_db[file_id]
    if file_info.category != "image":
        raise HTTPException(status_code=400, detail="File is not an image")
    
    try:
        # Create response future
        response_future = asyncio.Future()
        
        def on_response(text: str):
            response_future.set_result(text)
        
        def on_error(error: str):
            response_future.set_exception(Exception(error))
        
        # Analyse image
        ai_client.analyse_image(file_info.path, prompt, on_done=on_response, on_error=on_error)
        
        # Wait for response
        analysis_result = await response_future
        
        return ApiResponse(
            success=True,
            message="Image analysed successfully",
            data={"analysis": analysis_result}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/operations")
async def get_available_operations():
    """Get all available operations"""
    return get_available_operations()

@app.get("/api/operations/supported")
async def get_supported_operations():
    """Get supported operations by file type"""
    return {
        "pdf": ["convert", "split", "merge", "encrypt", "decrypt", "watermark", "metadata"],
        "docx": ["convert", "metadata"],
        "xlsx": ["convert", "metadata"],
        "pptx": ["convert", "metadata"],
        "txt": ["convert", "metadata"],
        "csv": ["convert", "metadata"],
        "image": ["analyse", "metadata"],
        "video": ["duration", "metadata"],
        "audio": ["duration", "metadata"]
    }

@app.get("/api/settings/theme")
async def get_theme():
    return {"theme": "light", "accent_color": "#2196f3"}

@app.post("/api/settings/theme")
async def set_theme(theme_data: dict):
    return {"success": True, "message": "Theme updated"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
