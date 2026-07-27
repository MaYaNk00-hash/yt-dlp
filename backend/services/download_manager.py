import asyncio
import os
import re
import uuid
import time
from typing import Dict, Set
import yt_dlp

from backend.models import DownloadRequest, DownloadProgress
from backend.services.ytdlp_service import build_ytdlp_download_opts, format_bytes
from backend.config import DOWNLOADS_DIR

class DownloadManager:
    """Manages active downloads, background lifecycle, and WebSocket status broadcasts."""
    def __init__(self):
        self.active_tasks: Dict[str, DownloadProgress] = {}
        self.websockets: Dict[str, Set[Any]] = {}

    def get_task_status(self, task_id: str) -> DownloadProgress:
        return self.active_tasks.get(task_id)

    async def start_download(self, request: DownloadRequest) -> str:
        task_id = str(uuid.uuid4())[:12]
        self.active_tasks[task_id] = DownloadProgress(
            task_id=task_id,
            status="queued",
            progress_percent=0.0,
            speed_str="0 B/s",
            eta_str="Calculating..."
        )
        self.websockets[task_id] = set()

        # Launch background download task
        loop = asyncio.get_running_loop()
        loop.create_task(self._execute_download(task_id, request, loop))
        return task_id

    async def register_websocket(self, task_id: str, websocket: Any):
        if task_id not in self.websockets:
            self.websockets[task_id] = set()
        self.websockets[task_id].add(websocket)
        # Send initial status right upon connection
        if task_id in self.active_tasks:
            await websocket.send_text(self.active_tasks[task_id].model_dump_json())

    def unregister_websocket(self, task_id: str, websocket: Any):
        if task_id in self.websockets:
            self.websockets[task_id].discard(websocket)

    async def _broadcast_status(self, task_id: str):
        """Send current task progress JSON to all subscribed websocket clients."""
        if task_id not in self.websockets or not self.websockets[task_id]:
            return
        status_data = self.active_tasks[task_id].model_dump_json()
        broken_ws = set()
        for ws in self.websockets[task_id]:
            try:
                await ws.send_text(status_data)
            except Exception:
                broken_ws.add(ws)
        for ws in broken_ws:
            self.websockets[task_id].discard(ws)

    async def _execute_download(self, task_id: str, request: DownloadRequest, loop: asyncio.AbstractEventLoop):
        """Run yt-dlp download in thread pool executor and handle completion status."""
        self.active_tasks[task_id].status = "downloading"
        await self._broadcast_status(task_id)

        def progress_callback(d: dict):
            # Because this hook runs inside a thread pool, schedule broadcasts via event loop
            loop.call_soon_threadsafe(self._handle_ytdlp_progress, task_id, d, loop)

        opts = build_ytdlp_download_opts(task_id, request, progress_callback)

        try:
            await loop.run_in_executor(None, lambda: self._run_ydl_sync(opts, request.url))
            
            # Locate completed output file
            final_file = self._find_downloaded_file(task_id)
            if not final_file:
                raise FileNotFoundError("Download completed but generated output file could not be located.")
            
            self.active_tasks[task_id].status = "complete"
            self.active_tasks[task_id].progress_percent = 100.0
            self.active_tasks[task_id].speed_str = "Done"
            self.active_tasks[task_id].eta_str = "00:00"
            self.active_tasks[task_id].filename = os.path.basename(final_file)
            self.active_tasks[task_id].download_url = f"/api/file/{task_id}/{os.path.basename(final_file)}"
            
        except Exception as e:
            self.active_tasks[task_id].status = "error"
            self.active_tasks[task_id].error_message = f"Download failed: {str(e)}"
            
        finally:
            await self._broadcast_status(task_id)

    def _run_ydl_sync(self, opts: dict, target_url: str):
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([target_url])

    def _handle_ytdlp_progress(self, task_id: str, d: dict, loop: asyncio.AbstractEventLoop):
        """Thread-safe handler invoked during download and merging phases."""
        task = self.active_tasks.get(task_id)
        if not task:
            return

        status = d.get("status")
        if status == "downloading":
            task.status = "downloading"
            
            # Percentage calculation
            total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            if total_bytes > 0:
                task.progress_percent = round((downloaded / float(total_bytes)) * 100.0, 1)
            
            # Speed formatting
            speed = d.get("speed")
            if speed:
                task.speed_str = f"{format_bytes(int(speed))}/s"
            elif d.get("_speed_str"):
                task.speed_str = re.sub(r'\x1b\[[0-9;]*m', '', d["_speed_str"]).strip()

            # ETA formatting
            eta = d.get("eta")
            if eta is not None:
                mins, secs = divmod(int(eta), 60)
                task.eta_str = f"{mins:02d}:{secs:02d}"
            elif d.get("_eta_str"):
                task.eta_str = re.sub(r'\x1b\[[0-9;]*m', '', d["_eta_str"]).strip()

        elif status == "finished":
            # During Video Only + Audio downloads, finished is invoked after each track before FFmpeg merge
            task.status = "merging"
            task.speed_str = "Processing"
            task.eta_str = "Merging streams..."
            task.progress_percent = 99.0

        asyncio.run_coroutine_threadsafe(self._broadcast_status(task_id), loop)

    def _find_downloaded_file(self, task_id: str) -> str:
        """Scan downloads directory for the completed artifact matching task prefix."""
        prefix = f"{task_id}_"
        candidates = []
        for entry in os.listdir(DOWNLOADS_DIR):
            if entry.startswith(prefix) and not entry.endswith((".part", ".ytdl", ".temp", ".f000", ".f001")):
                full_path = os.path.join(DOWNLOADS_DIR, entry)
                if os.path.isfile(full_path):
                    candidates.append((full_path, os.path.getmtime(full_path)))
        if not candidates:
            return None
        # Return most recently modified candidate (e.g. post-merge MP4)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

# Global singleton download manager instance
manager = DownloadManager()
