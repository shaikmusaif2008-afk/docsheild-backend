import os
import sys
from pathlib import Path

# Add project root to sys.path so backend modules import cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Top-level ASGI FastAPI app exposed for Vercel Serverless Function
from backend.main import app
