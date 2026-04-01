"""
Read-only database connection to the game's PostgreSQL database.

Connects via DATABASE_URL environment variable (same Postgres instance
as the game server). Only reads from xrpl_nftgamestate and
xrpl_nftitemtype tables.
"""

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def get_connection():
    """Yield a read-only database connection."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.set_session(readonly=True, autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


def fetch_nft(uri_id: int) -> dict | None:
    """Fetch NFT game state + item type by uri_id.

    Returns a dict with all fields needed for metadata, or None.
    """
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
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (uri_id,))
            row = cur.fetchone()
    return dict(row) if row else None
