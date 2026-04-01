# FullCircleMUD NFT Metadata API

Standalone API service that serves XLS-24d compliant NFT metadata from the game's PostgreSQL database. Runs independently of the game server so XRPL marketplace metadata resolution is always available.

## Endpoint

```
GET /nft/{uri_id}  ->  XLS-24d JSON metadata
GET /health        ->  { "status": "ok" }
```

The URI baked into each minted NFToken points here:
```
https://api.fcmud.world/nft/42
```

## Architecture

- **FastAPI** + **uvicorn** — lightweight, async-capable
- **psycopg2** — read-only connection to the game's Postgres
- **No Django/Evennia dependency** — pure Python, zero game engine overhead
- Reads from `xrpl_nftgamestate` and `xrpl_nftitemtype` tables only

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your DATABASE_URL
uvicorn app.main:app --reload
```

## Railway Deployment

Set these environment variables in Railway:
- `DATABASE_URL` — Railway Postgres connection string (same DB as game server)
- `NFT_IMAGE_BASE_URL` — Supabase image bucket URL (optional, has default)

The `Procfile` handles the rest.

## Response Format (XLS-24d)

```json
{
  "type": "game_item",
  "name": "Bronze Longsword",
  "description": "A broad bronze blade...",
  "collection": {
    "name": "FullCircleMUD",
    "family": "Game Items"
  },
  "properties": {
    "primary_display": {
      "type": "image/png",
      "description": "Bronze Longsword",
      "primary_uri": "https://...supabase.co/.../bronze_longsword.png"
    },
    "attributes": [
      { "attribute_name": "Category", "value_type": "string", "value": "Weapon" },
      { "attribute_name": "Prototype", "value_type": "string", "value": "bronze_longsword" }
    ]
  }
}
```
