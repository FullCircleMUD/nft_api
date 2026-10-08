"""
XLS-24 metadata for an exported item.

The response follows the XRPL NFT metadata standard, `art.v0`: the fields the
standard defines, then our own beside them — the item's id, and for an item
holding anything, the full tree of what is inside it.
"""

import os
from decimal import Decimal

NFT_IMAGE_BASE_URL = os.environ.get(
    "NFT_IMAGE_BASE_URL",
    "https://njqdijnpujooixoehbms.supabase.co/storage/v1/object/public/FCMImages/",
)

#: What an item type with no prototype shows. `art.v0` requires an image.
NFT_DEFAULT_IMAGE = os.environ.get("NFT_DEFAULT_IMAGE", f"{NFT_IMAGE_BASE_URL}default.png")

#: The `art.v0` schema, which the standard asks art and collectible projects to
#: point at unchanged.
ART_V0_SCHEMA = "ipfs://QmNpi8rcXEkohca8iXu7zysKKSJYqCvBJn3xJwga8jXqWU"
ART_V0 = "art.v0"

COLLECTION_NAME = "FullCircleMUD"

#: Each taxon an item type is minted with, as (category, family). The same
#: twelve groups the game's seed sets — kept here because this service cannot
#: read the game's code. A taxon is never reassigned once minted, so a new one
#: is only ever added.
TAXONS = {
    1: ("Weapon", "Weapons"),
    2: ("Wearable", "Wearables"),
    3: ("Container", "Containers"),
    4: ("Map", "Maps"),
    5: ("Ship", "Ships"),
    6: ("Pet", "Pets"),
    7: ("Gem", "Gems"),
    8: ("Potion", "Potions"),
    9: ("Wand", "Wands"),
    10: ("Recipe", "Recipes"),
    11: ("Scroll", "Scrolls"),
    12: ("General", "General"),
}
GENERAL = TAXONS[12]

# Python type -> whether a metadata value can be a trait's value.
_TRAIT_TYPES = (str, int, float, bool)


def category_of(taxon):
    """The (category, family) a taxon names. An unknown one reads as general."""
    return TAXONS.get(taxon, GENERAL)


def _amount(balance):
    """A balance as a plain string — no trailing zeros the database pads with."""
    text = format(Decimal(balance).normalize(), "f")
    return text


def _traits(metadata):
    """The item's own metadata as traits. Lists and mappings are left to `contents`."""
    traits = []
    for key, value in metadata.items():
        if key in ("name", "description") or not isinstance(value, _TRAIT_TYPES):
            continue
        traits.append({
            "trait_type": key.replace("_", " ").title(),
            "value": str(value) if isinstance(value, bool) else value,
        })
    return traits


def _contents_of(parent_id, items, balances):
    """What one item holds, its own holdings nested under each. None if nothing."""
    held_items = [
        {
            "item_id": item["id"],
            "name": item["item_name"],
            "metadata": item.get("metadata") or {},
            "contents": _contents_of(item["id"], items, balances),
        }
        for item in items if item["contained_in_id"] == parent_id
    ]
    held_balances = [
        {"currency": balance["currency_name"], "amount": _amount(balance["balance"])}
        for balance in balances if balance["contained_in_id"] == parent_id
    ]
    if not held_items and not held_balances:
        return None
    return {"items": held_items, "balances": held_balances}


def _summary(items, balances):
    """A one-line account of everything inside, for marketplaces to show."""
    parts = []
    if items:
        parts.append(f"{len(items)} item" + ("" if len(items) == 1 else "s"))
    totals = {}
    for balance in balances:
        name = balance["currency_name"]
        totals[name] = totals.get(name, Decimal(0)) + Decimal(balance["balance"])
    parts.extend(f"{_amount(amount)} {name}" for name, amount in totals.items())
    return ", ".join(parts)


def build_metadata(row, items=(), balances=()):
    """XLS-24 metadata for an exported item.

    Args:
        row: the item, as `db.fetch_item` returns it.
        items: everything inside it, at any depth, each with `contained_in_id`.
        balances: every balance inside it or anything in it, with
            `contained_in_id`, `currency_name` and `balance`.
    """
    metadata = row.get("metadata") or {}
    item_name = row.get("item_name") or "Unknown Item"
    prototype_key = row.get("item_prototype_key")
    category, family = category_of(row.get("item_taxon"))

    data = {
        "schema": ART_V0_SCHEMA,
        "nftType": ART_V0,
        "name": metadata.get("name", item_name),
        "description": metadata.get(
            "description",
            row.get("item_description") or f"A {item_name} from FullCircleMUD.",
        ),
        "image": (
            f"{NFT_IMAGE_BASE_URL}{prototype_key}.png" if prototype_key
            else NFT_DEFAULT_IMAGE
        ),
        "collection": {"name": COLLECTION_NAME, "family": family},
        "attributes": [{"trait_type": "Category", "value": category}, *_traits(metadata)],
        "item_id": row["id"],
    }

    contents = _contents_of(row["id"], list(items), list(balances))
    if contents is not None:
        data["contents"] = contents
        data["attributes"].append(
            {"trait_type": "Contents", "value": _summary(list(items), list(balances))}
        )
    return data
