import os
import shutil
from pathlib import Path

# Resilient repository root discovery for serverless cloud containers (Vercel / AWS Lambda site-packages wheels)
if (Path(os.getcwd()) / "frontend").exists():
    BASE_DIR = Path(os.getcwd()).resolve()
elif (Path("/var/task") / "frontend").exists():
    BASE_DIR = Path("/var/task").resolve()
else:
    BASE_DIR = Path(__file__).parent.parent.resolve()

# In Vercel / serverless deployments or read-only filesystems, safely route downloads to ephemeral /tmp
if os.environ.get("VERCEL") == "1" or os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or not os.access(BASE_DIR, os.W_OK):
    DOWNLOADS_DIR = Path("/tmp/downloads")
else:
    DOWNLOADS_DIR = BASE_DIR / "downloads"

FRONTEND_DIR = BASE_DIR / "frontend"

# Ensure downloads directory exists safely without throwing permission exceptions
try:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"Notice: Could not automatically create downloads directory: {e}")

# Application Settings
APP_TITLE = "yt-dlp Frontend Server"
APP_DESCRIPTION = "Modern, high-performance web dashboard for video and audio extraction using yt-dlp and FFmpeg."
APP_VERSION = "1.0.0"

# Cleanup threshold in seconds (default: 1 hour)
FILE_CLEANUP_THRESHOLD = 3600

def is_ffmpeg_installed() -> bool:
    """Check if ffmpeg executable is present in system PATH."""
    return shutil.which("ffmpeg") is not None
