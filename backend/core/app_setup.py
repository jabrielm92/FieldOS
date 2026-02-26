"""Application setup helpers for FastAPI app composition."""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.config import CORS_ORIGINS


def configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
