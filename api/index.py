import sys
import os
from pathlib import Path

# Guarantee root repository workspace directory is in system path for clean library resolution
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.main import app

# Export FastAPI server application for Vercel Serverless Function engine
__all__ = ["app"]
