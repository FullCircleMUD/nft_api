# FullCircleMUD NFT Metadata API

Standalone API service that serves XLS-24 (`art.v0`) metadata for the game's exported items, from the game's PostgreSQL database. Runs independently of the game server so XRPL marketplace metadata resolution is always available.

A token is minted when an item leaves the game, with the item's id at the end of its URI, and burnt when it comes back. So the API answers only for items on the ledger. Any other id — an item in the game, one destroyed in play, one that never existed — gets `404` with `"This item does not exist on the ledger."`

## Endpoints

```
GET /{item_id}  ->  XLS-24 JSON metadata
GET /health     ->  { "status": "ok", "environment": "dev|prod", "db_configured": true }
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
- Reads `xrpl_nftgamestate`, `xrpl_nftitemtype`, `xrpl_fungiblegamestate` and `xrpl_currencytype`

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
| `NFT_DEFAULT_IMAGE` | No (has default) | The image for an item type with no prototype — `art.v0` requires one |

Add both `api.fcmud.world` and `api.dev.fcmud.world` as custom domains on the Railway service.

The `Procfile` handles the rest.

## Response Format (XLS-24, `art.v0`)

The fields the standard defines, then our own beside them, as it encourages: `item_id`, and for an item holding anything, `contents` — everything inside it at any depth, and every balance. Marketplaces show `attributes`, so a `Contents` trait summarises what is inside.

`Category` and the collection's `family` come from the item type's taxon — the group number the token is minted with. The twelve names are kept in `app/metadata.py`, in step with the game's seed.

```json
{
  "schema": "ipfs://QmNpi8rcXEkohca8iXu7zysKKSJYqCvBJn3xJwga8jXqWU",
  "nftType": "art.v0",
  "name": "Leather Backpack",
  "description": "A sturdy leather pack.",
  "image": "https://...supabase.co/.../leather_backpack.png",
  "collection": { "name": "FullCircleMUD", "family": "Containers" },
  "attributes": [
    { "trait_type": "Category", "value": "Container" },
    { "trait_type": "Contents", "value": "1 item, 50 Gold" }
  ],
  "item_id": 1234,
  "contents": {
    "items": [
      { "item_id": 1235, "name": "Iron Dagger", "metadata": { "durability": 40 }, "contents": null }
    ],
    "balances": [ { "currency": "Gold", "amount": "50" } ]
  }
}
```
