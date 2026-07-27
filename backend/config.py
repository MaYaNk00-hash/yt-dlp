import os
import shutil
from pathlib import Path

# Project directory paths
BASE_DIR = Path(__file__).parent.parent.resolve()

# In Vercel / serverless deployments (read-only root filesystem), safely route downloads to ephemeral /tmp
if os.environ.get("VERCEL") == "1" or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    DOWNLOADS_DIR = Path("/tmp/downloads")
else:
    DOWNLOADS_DIR = BASE_DIR / "downloads"

FRONTEND_DIR = BASE_DIR / "frontend"

# Ensure downloads directory exists
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Application Settings
APP_TITLE = "yt-dlp Frontend Server"
APP_DESCRIPTION = "Modern, high-performance web dashboard for video and audio extraction using yt-dlp and FFmpeg."
APP_VERSION = "1.0.0"

# Cleanup threshold in seconds (default: 1 hour)
FILE_CLEANUP_THRESHOLD = 3600

def is_ffmpeg_installed() -> bool:
    """Check if ffmpeg executable is present in system PATH."""
    return shutil.which("ffmpeg") is not None
