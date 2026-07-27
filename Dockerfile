# Production Docker runtime for yt-dlp Studio
FROM python:3.11-slim

# Install FFmpeg and core utilities required for audio/video stream merging
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Set application workspace directory
WORKDIR /app

# Install Python backend requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code and static assets
COPY . .

# Create writable downloads directory for container execution
RUN mkdir -p downloads && chmod -R 777 downloads

# Expose HTTP port
EXPOSE 8000

# Launch Uvicorn server via run.py launcher
CMD ["python", "run.py"]
