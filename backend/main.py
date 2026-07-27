import os
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import APP_TITLE, APP_DESCRIPTION, APP_VERSION, FRONTEND_DIR, DOWNLOADS_DIR
from backend.models import (
    AnalyzeRequest,
    VideoAnalysisResponse,
    DownloadRequest,
    DownloadResponse,
)
from backend.services.ytdlp_service import analyze_url
from backend.services.download_manager import manager

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze", response_model=VideoAnalysisResponse)
async def analyze_video_endpoint(request: AnalyzeRequest):
    """Analyze video URL and return metadata + available formats."""
    try:
        data = await analyze_url(request.url)
        return data
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error during analysis: {str(e)}")

@app.post("/api/download", response_model=DownloadResponse)
async def start_download_endpoint(request: DownloadRequest):
    """Queue video/audio stream for download and merging."""
    try:
        task_id = await manager.start_download(request)
        return DownloadResponse(
            task_id=task_id,
            message="Download initiated successfully.",
            ws_url=f"/api/ws/progress/{task_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate download: {str(e)}")

@app.websocket("/api/ws/progress/{task_id}")
async def websocket_progress_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket connection for live download lifecycle updates."""
    await websocket.accept()
    await manager.register_websocket(task_id, websocket)
    try:
        while True:
            # Keep open and handle client-side ping messages
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        manager.unregister_websocket(task_id, websocket)

@app.get("/api/file/{task_id}/{filename}")
async def fetch_downloaded_file(task_id: str, filename: str):
    """Serve completed download file directly to client browser."""
    file_path = DOWNLOADS_DIR / filename
    if not file_path.is_file() or not filename.startswith(f"{task_id}_"):
        raise HTTPException(status_code=404, detail="Requested file was not found or has been removed.")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

# Ensure downloads folder exists on server startup without throwing errors in read-only containers
try:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"Notice: Unable to initialize downloads directory during container startup: {e}")

# Safely mount static interface files without throwing RuntimeError crashes if directories shift in cloud bundles
if FRONTEND_DIR.exists():
    css_dir = FRONTEND_DIR / "css"
    js_dir = FRONTEND_DIR / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    print(f"Notice: Static frontend directory not found at {FRONTEND_DIR}. Running in pure API mode.")
