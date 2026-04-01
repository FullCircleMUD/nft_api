# FullCircleMUD NFT Metadata API

Standalone API service that serves XLS-24d compliant NFT metadata from the game's PostgreSQL database. Runs independently of the game server so XRPL marketplace metadata resolution is always available.

## Endpoints

```
GET /nft/{uri_id}  ->  XLS-24d JSON metadata
GET /health        ->  { "status": "ok", "environment": "dev|prod", "db_configured": true }
```

## Multi-Environment Routing

A single API instance serves both staging and production by routing on the request hostname:

| Domain | Database | XRPL Network |
|--------|----------|--------------|
| `api.dev.fcmud.world` | Staging PostgreSQL | Testnet |
| `api.fcmud.world` | Production PostgreSQL | Mainnet |

Both domains point to the same Railway service. The `Host` header determines which database connection pool is used. Each connection is **read-only**.

If the database for a given environment isn't configured yet (e.g. production before beta launch), requests to that domain return `503 Service Unavailable`.

## Architecture

- **FastAPI** + **uvicorn** — lightweight, async-capable
- **psycopg2** with connection pooling — two read-only pools, one per environment
- **No Django/Evennia dependency** — pure Python, zero game engine overhead
- Reads from `xrpl_nftgamestate` and `xrpl_nftitemtype` tables only

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database URLs
uvicorn app.main:app --reload
```

## Railway Deployment

Set these environment variables in Railway:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL_DEV` | Yes (from alpha) | Staging PostgreSQL connection string |
| `DATABASE_URL_PROD` | Yes (from beta) | Production PostgreSQL connection string |
| `NFT_IMAGE_BASE_URL` | No (has default) | Supabase image bucket URL |

Add both `api.fcmud.world` and `api.dev.fcmud.world` as custom domains on the Railway service.

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
