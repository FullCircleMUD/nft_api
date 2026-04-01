"""
FullCircleMUD NFT Metadata API

Standalone FastAPI service that serves XLS-24d compliant NFT metadata
from the game's PostgreSQL database. Runs independently of the game
server so metadata is always available for XRPL marketplace resolution.

Endpoints:
    GET /nft/{uri_id}   -> XLS-24d JSON metadata
    GET /health         -> health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import fetch_nft
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
def health():
    """Health check for Railway deployment."""
    return {"status": "ok"}


@app.get("/nft/{uri_id}")
def nft_metadata(uri_id: int):
    """Serve XLS-24d NFT metadata for the given uri_id."""
    row = fetch_nft(uri_id)
    if not row:
        raise HTTPException(status_code=404, detail="NFT not found")

    # Unassigned tokens (no item_type) are not publicly resolvable
    if not row.get("item_name"):
        raise HTTPException(status_code=404, detail="NFT not found")

    return build_metadata(row)
