"""
Read-only database connections to the game's PostgreSQL databases.

Maintains two connection pools — one for production (api.fcmud.world)
and one for staging/dev (api.dev.fcmud.world). The correct pool is
selected at request time based on the Host header.

Both connections are read-only. Reads xrpl_nftgamestate, xrpl_nftitemtype,
xrpl_fungiblegamestate and xrpl_currencytype, and answers only for items on
the ledger.
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


def _pool_or_raise(host: str):
    """The pool for this host, or ConnectionError if it is not configured."""
    pool = get_pool_for_host(host)
    if pool is None:
        env = "staging" if "dev" in host else "production"
        raise ConnectionError(f"{env} database not configured")
    return pool


def _read(host: str, query: str, params: tuple) -> list[dict]:
    """Run one read-only query and return its rows as dicts."""
    pool = _pool_or_raise(host)
    conn = pool.getconn()
    try:
        conn.set_session(readonly=True, autocommit=True)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    finally:
        pool.putconn(conn)


def fetch_item(host: str, item_id: int) -> dict | None:
    """An exported item and its type, or None for one not on the ledger.

    The exported item is the token's one row with no container: an item
    inside it is ONCHAIN under the same token and is described with it.
    Raises ConnectionError if the database for this environment isn't
    configured.
    """
    rows = _read(host, """
        SELECT
            gs.id,
            gs.metadata,
            it.name          AS item_name,
            it.description   AS item_description,
            it.prototype_key AS item_prototype_key,
            it.taxon         AS item_taxon
        FROM xrpl_nftgamestate gs
        JOIN xrpl_nftitemtype it ON gs.item_type_id = it.id
        WHERE gs.id = %s
          AND gs.location = 'ONCHAIN'
          AND gs.contained_in_id IS NULL
    """, (item_id,))
    return rows[0] if rows else None


def fetch_contents(host: str, item_id: int) -> tuple[list[dict], list[dict]]:
    """Everything inside an exported item, at any depth, and every balance in it.

    Returns (items, balances). Each item carries `contained_in_id`, its name and
    its metadata; each balance its `contained_in_id`, currency name and amount.
    """
    items = _read(host, """
        WITH RECURSIVE inside AS (
            SELECT id, contained_in_id, item_type_id, metadata
            FROM xrpl_nftgamestate
            WHERE contained_in_id = %s AND location = 'ONCHAIN'
          UNION ALL
            SELECT child.id, child.contained_in_id, child.item_type_id, child.metadata
            FROM xrpl_nftgamestate child
            JOIN inside ON child.contained_in_id = inside.id
            WHERE child.location = 'ONCHAIN'
        )
        SELECT inside.id, inside.contained_in_id, inside.metadata,
               it.name AS item_name
        FROM inside
        JOIN xrpl_nftitemtype it ON inside.item_type_id = it.id
        ORDER BY inside.id
    """, (item_id,))
    holders = [item_id] + [item["id"] for item in items]
    balances = _read(host, """
        SELECT fs.contained_in_id,
               COALESCE(ct.name, fs.currency_code) AS currency_name,
               fs.balance
        FROM xrpl_fungiblegamestate fs
        LEFT JOIN xrpl_currencytype ct ON ct.currency_code = fs.currency_code
        WHERE fs.location = 'NFT' AND fs.contained_in_id = ANY(%s)
        ORDER BY fs.contained_in_id, currency_name
    """, (holders,))
    return items, balances
