"""
Read-only database connections to the game's PostgreSQL databases.

Maintains two connection pools — one for production (api.fcmud.world)
and one for staging/dev (api.dev.fcmud.world). The correct pool is
selected at request time based on the Host header.

Both connections are read-only. Only reads from xrpl_nftgamestate and
xrpl_nftitemtype tables.
"""

import os

import psycopg2
import psycopg2.pool
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL_PROD = os.environ.get("DATABASE_URL_PROD", "")
DATABASE_URL_DEV = os.environ.get("DATABASE_URL_DEV", "")

# Connection pools — initialised lazily on first use
_pool_prod = None
_pool_dev = None


def _get_pool(db_url):
    """Create a read-only connection pool for the given database URL."""
    pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=db_url,
    )
    return pool


def _ensure_pools():
    """Lazily initialise connection pools."""
    global _pool_prod, _pool_dev
    if _pool_prod is None and DATABASE_URL_PROD:
        _pool_prod = _get_pool(DATABASE_URL_PROD)
    if _pool_dev is None and DATABASE_URL_DEV:
        _pool_dev = _get_pool(DATABASE_URL_DEV)


def get_pool_for_host(host: str):
    """Return the correct connection pool based on the request host.

    Returns None if the database for that environment isn't configured.
    """
    _ensure_pools()
    if "dev" in host:
        return _pool_dev
    return _pool_prod


def fetch_nft(host: str, uri_id: int) -> dict | None:
    """Fetch NFT game state + item type by uri_id.

    Routes to the correct database based on the request host.
    Returns a dict with all fields needed for metadata, or None.
    Raises ConnectionError if the database for this environment
    isn't configured.
    """
    pool = get_pool_for_host(host)
    if pool is None:
        env = "staging" if "dev" in host else "production"
        raise ConnectionError(f"{env} database not configured")

    query = """
        SELECT
            gs.nftoken_id,
            gs.uri_id,
            gs.metadata,
            it.name         AS item_name,
            it.description  AS item_description,
            it.typeclass    AS item_typeclass,
            it.prototype_key AS item_prototype_key
        FROM xrpl_nftgamestate gs
        LEFT JOIN xrpl_nftitemtype it ON gs.item_type_id = it.id
        WHERE gs.uri_id = %s
    """
    conn = pool.getconn()
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (uri_id,))
            row = cur.fetchone()
        return dict(row) if row else None
    finally:
        pool.putconn(conn)
