from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    url: str = Field(..., description="The URL of the target video to analyze")

class FormatItem(BaseModel):
    format_id: str
    resolution: str
    ext: str
    filesize_str: str
    filesize_bytes: Optional[int] = None
    fps: Optional[float] = None
    vcodec: str
    acodec: str
    format_type: str = Field(..., description="'Top 5 Combined', 'Video + Audio', 'Video Only', or 'Audio Only'")
    note: Optional[str] = None
    command: Optional[str] = None

class VideoAnalysisResponse(BaseModel):
    title: str
    thumbnail: Optional[str] = None
    duration_formatted: str
    duration_seconds: Optional[int] = None
    uploader: str
    webpage_url: str
    formats: List[FormatItem]
    ffmpeg_available: bool

class DownloadRequest(BaseModel):
    url: str
    format_id: str
    format_type: str
    title: Optional[str] = "video"

class DownloadResponse(BaseModel):
    task_id: str
    message: str
    ws_url: str

class DownloadProgress(BaseModel):
    task_id: str
    status: str = Field(..., description="'queued', 'downloading', 'merging', 'complete', 'error'")
    progress_percent: float = 0.0
    speed_str: str = "-"
    eta_str: str = "-"
    filename: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
