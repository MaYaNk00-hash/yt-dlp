import uvicorn
import sys
from pathlib import Path

# Add project root to system path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from backend.config import is_ffmpeg_installed

def main():
    print("=" * 60)
    print("  yt-dlp Frontend Web Server Launcher")
    print("=" * 60)
    
    if is_ffmpeg_installed():
        print("[+] FFmpeg detected in system PATH. Video/Audio merging is fully enabled.")
    else:
        print("[-] WARNING: FFmpeg was not found in system PATH!")
        print("    Video Only streams will not be able to automatically merge with best audio.")
    
    print("[+] Launching Uvicorn server at http://127.0.0.1:8000 ...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
