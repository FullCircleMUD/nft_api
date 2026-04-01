"""
XLS-24d metadata builder.

Replicates the logic from the game's nft_metadata_view but without
any Django or Evennia dependencies.
"""

import os

NFT_IMAGE_BASE_URL = os.environ.get(
    "NFT_IMAGE_BASE_URL",
    "https://njqdijnpujooixoehbms.supabase.co/storage/v1/object/public/FCMImages/",
)

# Typeclass path fragment -> human-readable category
_CATEGORY_MAP = {
    "wearable": "Wearable",
    "holdable": "Holdable",
    "weapon": "Weapon",
    "consumable": "Consumable",
    "container": "Container",
    "ship": "Ship",
    "base_nft_item": "Item",
}

# Python type -> XLS-24d value_type
_VALUE_TYPE_MAP = {
    str: "string",
    int: "int",
    float: "decimal",
    bool: "string",
}


def _derive_category(typeclass_path: str | None) -> str:
    """Map a typeclass path to a display category."""
    if not typeclass_path:
        return "Item"
    path_lower = typeclass_path.lower()
    for fragment, label in _CATEGORY_MAP.items():
        if fragment in path_lower:
            return label
    return "Item"


def build_metadata(row: dict) -> dict:
    """Build XLS-24d compliant metadata dict from a database row.

    Args:
        row: Dict from db.fetch_nft() with keys: item_name,
             item_description, item_typeclass, item_prototype_key,
             metadata.
    """
    metadata = row.get("metadata") or {}
    item_name = row.get("item_name") or "Unknown Item"
    item_description = row.get("item_description") or ""
    item_typeclass = row.get("item_typeclass")
    prototype_key = row.get("item_prototype_key")

    name = metadata.get("name", item_name)
    description = metadata.get(
        "description",
        item_description or f"A {item_name} from FullCircleMUD.",
    )

    data = {
        "type": "game_item",
        "name": name,
        "description": description,
        "collection": {
            "name": "FullCircleMUD",
            "family": "Game Items",
        },
        "properties": {},
    }

    # Image
    if prototype_key and NFT_IMAGE_BASE_URL:
        data["properties"]["primary_display"] = {
            "type": "image/png",
            "description": name,
            "primary_uri": f"{NFT_IMAGE_BASE_URL}{prototype_key}.png",
        }

    # Attributes
    attrs = []
    if item_typeclass:
        attrs.append({
            "attribute_name": "Category",
            "value_type": "string",
            "value": _derive_category(item_typeclass),
        })
    if prototype_key:
        attrs.append({
            "attribute_name": "Prototype",
            "value_type": "string",
            "value": prototype_key,
        })

    # Per-instance metadata
    for key, value in metadata.items():
        if key in ("name", "description"):
            continue
        value_type = _VALUE_TYPE_MAP.get(type(value))
        if value_type:
            attrs.append({
                "attribute_name": key.replace("_", " ").title(),
                "value_type": value_type,
                "value": str(value) if isinstance(value, bool) else value,
            })

    if attrs:
        data["properties"]["attributes"] = attrs

    return data
