"""ASGI entrypoint for FieldOS.

This thin module keeps deployment command compatibility (`uvicorn server:app`)
while the application implementation lives in `app.py`.
"""

from app import app

__all__ = ["app"]
