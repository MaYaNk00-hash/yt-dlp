import pytest
import os
import sys
from pathlib import Path

# Insert workspace root to system path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from backend.services.ytdlp_service import (
    validate_url,
    format_duration,
    format_bytes,
    parse_format_item,
    build_ytdlp_download_opts,
)
from backend.models import DownloadRequest

def test_validate_url():
    assert validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert validate_url("http://vimeo.com/123456") is True
    assert validate_url("invalid-url") is False
    assert validate_url("") is False

def test_format_duration():
    assert format_duration(None) == "Live / Unknown"
    assert format_duration(0) == "00:00"
    assert format_duration(255) == "04:15"
    assert format_duration(3665) == "01:01:05"

def test_format_bytes():
    assert format_bytes(None) == "N/A"
    assert format_bytes(500) == "500.0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1048576) == "1.0 MB"
    assert format_bytes(47401560) == "45.2 MB"

def test_parse_format_item_classification():
    # 1. Video + Audio Format (1080p)
    fmt_va = {
        "format_id": "22",
        "vcodec": "avc1.64001F",
        "acodec": "mp4a.40.2",
        "height": 1080,
        "fps": 60,
        "ext": "mp4",
        "filesize": 52428800 # 50 MB
    }
    item_va = parse_format_item(fmt_va, 120, "https://youtube.com/watch?v=sample")
    assert item_va is not None
    assert item_va.format_type == "Video + Audio"
    assert item_va.resolution == "1080p (Full HD)"
    assert item_va.vcodec == "avc1"
    assert item_va.acodec == "mp4a"
    assert item_va.filesize_str == "50.0 MB"
    assert item_va.command == 'yt-dlp -f "22" "https://youtube.com/watch?v=sample"'

    # 2. Video Only Format (4K)
    fmt_vo = {
        "format_id": "313",
        "vcodec": "vp9",
        "acodec": "none",
        "height": 2160,
        "fps": 30,
        "ext": "webm",
        "filesize": 157286400 # 150 MB
    }
    item_vo = parse_format_item(fmt_vo, 120, "https://youtube.com/watch?v=sample")
    assert item_vo is not None
    assert item_vo.format_type == "Video Only"
    assert item_vo.resolution == "2160p (4K)"
    assert item_vo.vcodec == "vp9"
    assert item_vo.acodec == "None"
    assert item_vo.command == 'yt-dlp -f "313+bestaudio/best" --merge-output-format mp4 "https://youtube.com/watch?v=sample"'

    # 3. Audio Only Format
    fmt_ao = {
        "format_id": "251",
        "vcodec": "none",
        "acodec": "opus",
        "ext": "webm",
        "tbr": 160 # 160 kbps
    }
    item_ao = parse_format_item(fmt_ao, 100, "https://youtube.com/watch?v=sample")
    assert item_ao is not None
    assert item_ao.format_type == "Audio Only"
    assert item_ao.resolution == "Audio Only"
    assert item_ao.vcodec == "None"
    assert item_ao.acodec == "opus"
    assert item_ao.command == 'yt-dlp -f "251" "https://youtube.com/watch?v=sample"'

def test_build_ytdlp_download_opts_merging():
    # Test Top 5 Combined merging parameters
    req_top = DownloadRequest(
        url="https://youtube.com/watch?v=test",
        format_id="313+251",
        format_type="Top 5 Combined",
        title="Top Quality Video"
    )
    opts_top = build_ytdlp_download_opts("task-789", req_top, lambda d: None)
    assert opts_top["format"] == "313+251"
    assert opts_top["merge_output_format"] == "mp4"

    # Test that Video Only streams request automatic merging with best audio via FFmpeg
    req_vo = DownloadRequest(
        url="https://youtube.com/watch?v=test",
        format_id="137",
        format_type="Video Only",
        title="Test Video"
    )
    opts_vo = build_ytdlp_download_opts("task-123", req_vo, lambda d: None)
    assert opts_vo["format"] == "137+bestaudio/best"
    assert opts_vo["merge_output_format"] == "mp4"

    # Test Audio Only streams download directly
    req_ao = DownloadRequest(
        url="https://youtube.com/watch?v=test",
        format_id="140",
        format_type="Audio Only",
        title="Test Audio"
    )
    opts_ao = build_ytdlp_download_opts("task-456", req_ao, lambda d: None)
    assert opts_ao["format"] == "140"
    assert "merge_output_format" not in opts_ao

def test_parse_format_item_single_stream_platform():
    # Verify extraction on single-stream websites (Instagram Reels, TikTok, Twitter/X, SoundCloud) where format_id is omitted
    fmt_single = {
        "vcodec": "h264",
        "acodec": "aac",
        "height": 720,
        "filesize_approx": 15728640 # 15 MB
    }
    item = parse_format_item(fmt_single, 30, "https://www.tiktok.com/@user/video/123456789")
    assert item is not None
    assert item.format_id == "best"
    assert item.format_type == "Video + Audio"
    assert item.resolution == "720p (HD)"
    assert item.filesize_str == "15.0 MB"
    assert item.command == 'yt-dlp -f "best" "https://www.tiktok.com/@user/video/123456789"'

