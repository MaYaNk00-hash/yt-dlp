import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Insert project root to system path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from backend.main import app

client = TestClient(app)

def test_static_frontend_mount():
    """Verify index.html interface is correctly mounted and served at root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "yt-dlp Studio" in response.text
    assert "Extract & Download Web Video" in response.text
    assert "styles.css" in response.text

def test_analyze_invalid_url_validation():
    """Verify API returns 400 Bad Request with clean descriptive error when URL is invalid."""
    response = client.post("/api/analyze", json={"url": "not-a-valid-http-url"})
    assert response.status_code == 400
    data = response.json()
    assert "Invalid URL format" in data["detail"]

def test_download_endpoint_queue_initialization():
    """Verify download initiation returns unique task ID and websocket endpoint."""
    payload = {
        "url": "https://www.youtube.com/watch?v=sample",
        "format_id": "22",
        "format_type": "Video + Audio",
        "title": "Sample Verification Video"
    }
    response = client.post("/api/download", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert "ws_url" in data
    assert data["ws_url"].startswith("/api/ws/progress/")
