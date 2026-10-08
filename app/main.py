"""
FullCircleMUD NFT Metadata API

Standalone FastAPI service that serves XLS-24 (`art.v0`) metadata for the
game's exported items, from the game's PostgreSQL database. Runs independently of the game
server so metadata is always available for XRPL marketplace resolution.

Routes to the correct database based on the request hostname:
    api.fcmud.world     -> production database
    api.dev.fcmud.world -> staging/dev database

Endpoints:
    GET /{item_id}      -> XLS-24 JSON metadata, for an item on the ledger
    GET /health         -> health check
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.db import DATABASE_URL_DEV, DATABASE_URL_PROD, fetch_contents, fetch_item
from app.metadata import build_metadata

#: The answer for any id with no item on the ledger: one in the game, one
#: destroyed in play, or one that never existed alike.
NOT_ON_LEDGER = "This item does not exist on the ledger."

app = FastAPI(
    title="FullCircleMUD NFT API",
    description="XLS-24 NFT metadata for XRPL marketplace resolution",
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


@app.get("/{item_id}")
def nft_metadata(item_id: int, request: Request):
    """Serve XLS-24 metadata for the item a token carries."""
    host = request.headers.get("host", "")

    try:
        row = fetch_item(host, item_id)
        if not row:
            raise HTTPException(status_code=404, detail=NOT_ON_LEDGER)
        items, balances = fetch_contents(host, item_id)
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    return build_metadata(row, items, balances)
