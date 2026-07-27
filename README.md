# yt-dlp Studio 🎬

> **Lightning-fast, visually stunning web studio and dashboard for stream inspection, codec extraction, and automated FFmpeg video merging powered by yt-dlp and FastAPI.**

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-00a396?logo=fastapi&logoColor=white)
![FFmpeg Ready](https://img.shields.io/badge/FFmpeg-Ready-8A5CF6?logo=ffmpeg&logoColor=white)
![WebSockets](https://img.shields.io/badge/WebSockets-Realtime-10b981)
![License MIT](https://img.shields.io/badge/License-MIT-amber)

---

## 🌟 Key Features

* **🏆 Top 5 Combined High-Quality Curation**: Automatically calculates the highest bitrate audio stream and merges it with up to 5 top HD video qualities (4K AV1, 1440p VP9, 1080p60 H.264) into clean, ready-to-download MP4 options.
* **📋 Interactive CLI Terminal Commands**: Inspects exact `yt-dlp` parameter flags for every format profile with a one-click copy button to paste straight into your terminal or automation scripts.
* **⚡ Automated FFmpeg Stream Merging**: Video-only stream formats automatically trigger high-definition audio demuxing/muxing via FFmpeg—no manual instructions required.
* **📈 Real-Time WebSocket Tracking**: Watch live download progress bars, bitrates, transfer speeds, and ETA times broadcasted directly from the backend to your browser.
* **🎨 Ultra-Premium Dark Mode UI**: Designed with Google Fonts (*Outfit*), vibrant HSL gradients, smooth glassmorphism effects, dynamic filter tabs, and a non-intrusive Toast Notification Engine.

---

## 🚀 Quick Start (Local Development)

### 1. Requirements
* **Python**: v3.10 or higher
* **FFmpeg**: Must be installed and accessible in your system `PATH` for video/audio merging.

### 2. Installation & Run

```powershell
# Clone the repository
git clone https://github.com/MaYaNk00-hash/yt-dlp.git
cd yt-dlp

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # On macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch web studio server
python run.py
```

Open your web browser and navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## ☁️ Production & Cloud Deployment Guide

### Why NOT Vercel?
While Vercel is fantastic for frontend applications, hosting this full-stack application completely on Vercel is **not recommended** due to serverless architecture limitations:
1. **WebSockets**: Serverless functions do not support long-lived bidirectional WebSockets required for real-time progress streaming.
2. **FFmpeg & Storage**: Vercel environments lack full FFmpeg installations and have ephemeral disk quotas (max 500MB `/tmp`), preventing large 4K video downloads and transcoding.
3. **Timeout Restrictors**: Serverless execution timeouts (10s on Free tiers) will interrupt long video download tasks.

### ✅ Recommended Cloud Deployment: Docker / Container Platforms (Render, Railway, Fly.io)

We have provided a production-ready **`Dockerfile`** that preloads Python 3.11 and **FFmpeg** into a high-performance Linux container!

#### One-Click Deploy on Render.com (Free Tier Supported):
1. Create a free account on **[Render.com](https://render.com)**.
2. Click **New +** -> **Web Service** and connect this GitHub repository (`MaYaNk00-hash/yt-dlp`).
3. Set **Runtime** to **Docker** (Render will automatically detect the provided `Dockerfile`).
4. Click **Deploy Web Service**—that's it! Your application will deploy with full FFmpeg capabilities, zero timeout interruptions, and native WebSocket progress tracking!

---

## 🧪 Testing Suite

Run the comprehensive automated unit and API test suite:
```powershell
pytest test_backend.py test_api.py -v
```

## 📝 License
This project is licensed under the **MIT License**.
