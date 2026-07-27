import uvicorn
import sys
import socket
from pathlib import Path

# Add project root to system path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from backend.config import is_ffmpeg_installed

def get_local_ip() -> str:
    """Detect LAN / Wi-Fi IP address of this computer for seamless mobile device access."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def main():
    print("=" * 66)
    print("      🎥  yt-dlp Studio — High-Performance Frontend Server  🎥")
    print("=" * 66)
    
    if is_ffmpeg_installed():
        print("  [✓] FFmpeg detected in system PATH. Audio/Video merging enabled.")
    else:
        print("  [!] WARNING: FFmpeg not found in system PATH!")
        print("      Video Only streams cannot automatically merge with audio.")
    
    lan_ip = get_local_ip()
    print("\n  🚀 Access your Web Studio at:")
    print(f"  💻 PC (Localhost):    http://localhost:8000")
    print(f"  📱 Mobile (Same Wi-Fi): http://{lan_ip}:8000")
    print("=" * 66 + "\n")
    
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()

