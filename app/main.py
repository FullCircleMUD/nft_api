"""
FullCircleMUD NFT Metadata API

Standalone FastAPI service that serves XLS-24d compliant NFT metadata
from the game's PostgreSQL database. Runs independently of the game
server so metadata is always available for XRPL marketplace resolution.

Routes to the correct database based on the request hostname:
    api.fcmud.world     -> production database
    api.dev.fcmud.world -> staging/dev database

Endpoints:
    GET /{uri_id}       -> XLS-24d JSON metadata
    GET /health         -> health check
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.db import fetch_nft, DATABASE_URL_PROD, DATABASE_URL_DEV
from app.metadata import build_metadata

app = FastAPI(
    title="FullCircleMUD NFT API",
    description="XLS-24d NFT metadata for XRPL marketplace resolution",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health(request: Request):
    """Health check for Railway deployment."""
    host = request.headers.get("host", "")
    is_dev = "dev" in host
    return {
        "status": "ok",
        "environment": "dev" if is_dev else "prod",
        "db_configured": bool(DATABASE_URL_DEV if is_dev else DATABASE_URL_PROD),
    }


@app.get("/{uri_id}")
def nft_metadata(uri_id: int, request: Request):
    """Serve XLS-24d NFT metadata for the given uri_id."""
    host = request.headers.get("host", "")

    try:
        row = fetch_nft(host, uri_id)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if not row:
        raise HTTPException(status_code=404, detail="NFT not found")

    # Unassigned tokens (no item_type) are not publicly resolvable
    if not row.get("item_name"):
        raise HTTPException(status_code=404, detail="NFT not found")

    return build_metadata(row)
