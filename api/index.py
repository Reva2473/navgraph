"""
Vercel Serverless Function Entry Point for NavGraph DSA FastAPI Backend.
"""

import os
import sys

# Add project root directory to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import app

# Vercel's Python runtime automatically looks for the WSGI/ASGI 'app' attribute
__all__ = ["app"]
