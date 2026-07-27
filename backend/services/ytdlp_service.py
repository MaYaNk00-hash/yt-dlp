import asyncio
import os
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import yt_dlp
from yt_dlp.utils import DownloadError

from backend.models import VideoAnalysisResponse, FormatItem, DownloadRequest
from backend.config import DOWNLOADS_DIR, is_ffmpeg_installed

def validate_url(url: str) -> bool:
    """Validate basic structure of video URL."""
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

def format_duration(seconds: Optional[int]) -> str:
    """Convert raw seconds into a readable MM:SS or HH:MM:SS format."""
    if seconds is None or seconds < 0:
        return "Live / Unknown"
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def format_bytes(size_bytes: Optional[int]) -> str:
    """Convert raw byte sizes into human-readable string (KB, MB, GB)."""
    if not size_bytes or size_bytes <= 0:
        return "N/A"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.1f} {units[i]}"

def parse_format_item(fmt: Dict[str, Any], duration_seconds: Optional[int], target_url: str = "") -> Optional[FormatItem]:
    """Parse raw yt-dlp format dictionary into structured FormatItem with CLI command."""
    format_id = fmt.get("format_id") or "best"


    vcodec = str(fmt.get("vcodec", "none")).strip()
    acodec = str(fmt.get("acodec", "none")).strip()
    
    # Clean codec display names
    v_display = "None" if vcodec in ("none", "null", "") else vcodec.split(".")[0]
    a_display = "None" if acodec in ("none", "null", "") else acodec.split(".")[0]

    has_video = v_display != "None"
    has_audio = a_display != "None"

    if not has_video and not has_audio:
        # Skip empty streams / storyboard manifests
        return None

    if has_video and has_audio:
        format_type = "Video + Audio"
    elif has_video and not has_audio:
        format_type = "Video Only"
    else:
        format_type = "Audio Only"

    # Resolution naming
    height = fmt.get("height")
    if format_type == "Audio Only":
        resolution = "Audio Only"
    elif height:
        if height >= 2160:
            resolution = f"{height}p (4K)"
        elif height >= 1440:
            resolution = f"{height}p (2K)"
        elif height == 1080:
            resolution = "1080p (Full HD)"
        elif height == 720:
            resolution = "720p (HD)"
        else:
            resolution = f"{height}p"
    else:
        resolution = str(fmt.get("resolution") or fmt.get("format_note") or "Standard").strip()

    ext = str(fmt.get("ext", "unknown")).lower()
    
    # Robust multi-tier file size estimation to guarantee every format shows an exact size
    filesize = fmt.get("filesize") or fmt.get("filesize_approx")
    if not filesize and duration_seconds:
        tbr = fmt.get("tbr")
        if not tbr:
            vbr = float(fmt.get("vbr") or 0)
            abr = float(fmt.get("abr") or 0)
            if vbr + abr > 0:
                tbr = vbr + abr
        if tbr and float(tbr) > 0:
            filesize = int((float(tbr) * 1024 / 8.0) * duration_seconds)
    
    filesize_str = format_bytes(int(filesize)) if filesize and filesize > 0 else "N/A"
    fps = fmt.get("fps")

    note = fmt.get("format_note") or ""
    if fmt.get("tbr") and not note:
        note = f"{int(fmt['tbr'])}kbps"

    # Construct exact CLI command equivalent
    if format_type == "Video Only":
        command = f'yt-dlp -f "{format_id}+bestaudio/best" --merge-output-format mp4 "{target_url}"'
    else:
        command = f'yt-dlp -f "{format_id}" "{target_url}"'

    return FormatItem(
        format_id=str(format_id),
        resolution=resolution,
        ext=ext,
        filesize_str=filesize_str,
        filesize_bytes=int(filesize) if filesize else None,
        fps=float(fps) if fps else None,
        vcodec=v_display,
        acodec=a_display,
        format_type=format_type,
        note=str(note) if note else None,
        command=command
    )

async def analyze_url(url: str) -> VideoAnalysisResponse:
    """Extract metadata, calculate Top 5 Combined qualities, and all raw download tracks."""
    if not validate_url(url):
        raise ValueError("Invalid URL format. Please provide a valid HTTP or HTTPS link.")

    ydl_opts = {
        "extract_flat": False,
        "dump_single_json": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
    }

    loop = asyncio.get_running_loop()
    try:
        info = await loop.run_in_executor(None, lambda: _extract_info_sync(ydl_opts, url))
    except DownloadError as e:
        err_msg = str(e)
        if "Unsupported URL" in err_msg or "not supported" in err_msg:
            raise ValueError("This URL or video platform is not supported by yt-dlp.")
        elif "Private video" in err_msg:
            raise ValueError("This video is private or password protected.")
        elif "Video unavailable" in err_msg:
            raise ValueError("Video is unavailable or has been deleted.")
        elif "Sign in to confirm" in err_msg or "bot" in err_msg.lower():
            raise ValueError("YouTube bot detection blocked this server IP. (Note: Cloud datacenter IPs like Vercel/AWS often require OAuth cookies for protected YouTube videos; standard sites and residential hosts work directly).")
        else:
            clean_err = re.sub(r'ERROR:\s*\[[^\]]+\]\s*[^:]+:\s*', '', err_msg.split(';')[0]).strip()
            raise ValueError(f"Analysis failed: {clean_err or err_msg}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred during URL analysis: {str(e)}")

    title = info.get("title", "Untitled Video")
    
    # Thumbnail resolution logic (pick highest quality available)
    thumbnail = info.get("thumbnail")
    if not thumbnail and info.get("thumbnails"):
        thumbnails = sorted(info.get("thumbnails", []), key=lambda t: t.get("width") or 0, reverse=True)
        if thumbnails:
            thumbnail = thumbnails[0].get("url")

    duration_seconds = info.get("duration")
    duration_formatted = format_duration(duration_seconds)
    uploader = info.get("uploader") or info.get("channel") or info.get("uploader_id") or "Unknown Creator"
    webpage_url = info.get("webpage_url", url)

    raw_formats = info.get("formats")
    if not raw_formats or not isinstance(raw_formats, list):
        # For single-stream websites (Instagram, TikTok, Twitter/X, Reddit clips, SoundCloud, Vimeo)
        raw_formats = [info]
    parsed_formats: List[FormatItem] = []
    seen_ids = set()

    for fmt in raw_formats:
        fid = str(fmt.get("format_id"))
        if fid in seen_ids:
            continue
        item = parse_format_item(fmt, duration_seconds, webpage_url)
        if item:
            parsed_formats.append(item)
            seen_ids.add(fid)

    # Helper to determine resolution height for sorting
    def get_res_height(x: FormatItem) -> int:
        if x.format_type == "Audio Only":
            return 0
        match = re.search(r"(\d+)p", x.resolution)
        return int(match.group(1)) if match else 0

    # Sort raw formats cleanly: by type, then resolution height descending, then FPS, then bitrate
    parsed_formats.sort(key=lambda x: (
        0 if x.format_type == "Video + Audio" else (1 if x.format_type == "Video Only" else 2),
        -get_res_height(x),
        -(x.fps or 0),
        -(x.filesize_bytes or 0)
    ))

    # Construct Top 5 High Quality Combined Video + Audio options
    top_combined: List[FormatItem] = []
    audio_only = [f for f in parsed_formats if f.format_type == "Audio Only"]
    best_audio = sorted(audio_only, key=lambda a: (a.filesize_bytes or 0), reverse=True)[0] if audio_only else None
    best_audio_id = best_audio.format_id if best_audio else "bestaudio/best"
    best_acodec = best_audio.acodec if best_audio else "bestaudio"
    audio_size_bytes = (best_audio.filesize_bytes or 0) if best_audio else 0

    # Collect all video streams and sort STRICTLY by resolution height and FPS (so 4K/1080p always beat 360p pre-merged)
    video_streams = [f for f in parsed_formats if f.format_type in ("Video Only", "Video + Audio")]
    video_streams.sort(key=lambda x: (-get_res_height(x), -(x.fps or 0), -(x.filesize_bytes or 0)))

    # Calculate exact max combined size of #1 best video + #1 best studio audio
    best_video = video_streams[0] if video_streams else None
    max_size_bytes = 0
    if best_video and best_video.filesize_bytes:
        max_size_bytes += best_video.filesize_bytes
        if best_video.format_type == "Video Only" and audio_size_bytes > 0:
            max_size_bytes += audio_size_bytes
    max_size_str = format_bytes(max_size_bytes) if max_size_bytes > 0 else "N/A"

    # 1. ALWAYS inject #1 Master Option: Maximum Available (Best Video + Best Audio)
    max_cmd = f'yt-dlp -f "bestvideo+bestaudio/best" --merge-output-format mp4 "{webpage_url}"'
    top_combined.append(FormatItem(
        format_id="bestvideo+bestaudio/best",
        resolution="Maximum Quality (Best Video + Best Audio)",
        ext="mp4",
        filesize_str=max_size_str,
        filesize_bytes=max_size_bytes if max_size_bytes > 0 else None,
        fps=best_video.fps if best_video else None,
        vcodec=best_video.vcodec if best_video else "bestvideo",
        acodec=best_acodec,
        format_type="Top 5 Combined",
        note="Master Quality: Merges #1 highest video stream with #1 studio audio",
        command=max_cmd
    ))

    seen_res = set()
    for v in video_streams:
        if len(top_combined) >= 5:
            break
        # Group by resolution + codec so users get distinct high definition tiers (e.g., 2160p, 1080p, 720p)
        res_key = f"{v.resolution}_{v.vcodec}"
        if res_key in seen_res:
            continue
        seen_res.add(res_key)

        if v.format_type == "Video Only":
            comb_id = f"{v.format_id}+{best_audio_id}"
            comb_size_bytes = (v.filesize_bytes or 0) + audio_size_bytes
            comb_size_str = format_bytes(comb_size_bytes) if comb_size_bytes > 0 else "N/A"
            comb_cmd = f'yt-dlp -f "{comb_id}" --merge-output-format mp4 "{webpage_url}"'
            audio_note = f" ({best_audio.note})" if best_audio and best_audio.note else ""
            top_combined.append(FormatItem(
                format_id=comb_id,
                resolution=v.resolution,
                ext="mp4",
                filesize_str=comb_size_str,
                filesize_bytes=comb_size_bytes if comb_size_bytes > 0 else None,
                fps=v.fps,
                vcodec=v.vcodec,
                acodec=best_acodec,
                format_type="Top 5 Combined",
                note=f"Merged with Best Audio{audio_note} • Track {v.format_id}+{best_audio_id}",
                command=comb_cmd
            ))
        else:
            comb_cmd = f'yt-dlp -f "{v.format_id}" "{webpage_url}"'
            top_combined.append(FormatItem(
                format_id=v.format_id,
                resolution=v.resolution,
                ext=v.ext,
                filesize_str=v.filesize_str,
                filesize_bytes=v.filesize_bytes,
                fps=v.fps,
                vcodec=v.vcodec,
                acodec=v.acodec,
                format_type="Top 5 Combined",
                note="Pre-merged High Quality Stream",
                command=comb_cmd
            ))

    all_formats = top_combined + parsed_formats

    return VideoAnalysisResponse(
        title=title,
        thumbnail=thumbnail,
        duration_formatted=duration_formatted,
        duration_seconds=int(duration_seconds) if duration_seconds else None,
        uploader=uploader,
        webpage_url=webpage_url,
        formats=all_formats,
        ffmpeg_available=is_ffmpeg_installed(),
    )

def _extract_info_sync(opts: Dict[str, Any], target_url: str) -> Dict[str, Any]:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(target_url, download=False)

def build_ytdlp_download_opts(task_id: str, request: DownloadRequest, progress_callback: Any) -> Dict[str, Any]:
    """Generate precise yt-dlp configurations for format extraction and FFmpeg automatic merging."""
    safe_title = re.sub(r'[\\/*?:"<>|]', "", request.title or "video")[:80]
    output_template = str(DOWNLOADS_DIR / f"{task_id}_{safe_title}.%(ext)s")

    opts = {
        "outtmpl": output_template,
        "progress_hooks": [progress_callback],
        "quiet": True,
        "no_warnings": True,
        "nopagereaders": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
    }

    if request.format_type == "Video Only":
        opts["format"] = f"{request.format_id}+bestaudio/best"
        opts["merge_output_format"] = "mp4"
    elif request.format_type == "Top 5 Combined" or "+" in str(request.format_id):
        opts["format"] = str(request.format_id)
        if "+" in str(request.format_id) or "mp4" in request.format_type.lower():
            opts["merge_output_format"] = "mp4"
    else:
        opts["format"] = str(request.format_id)

    return opts
