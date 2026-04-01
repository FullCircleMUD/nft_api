"""Tests for metadata builder — no database needed."""

from app.metadata import build_metadata, _derive_category


def test_derive_category_weapon():
    assert _derive_category("typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem") == "Weapon"


def test_derive_category_wearable():
    assert _derive_category("typeclasses.items.wearables.wearable_nft_item.WearableNFTItem") == "Wearable"


def test_derive_category_none():
    assert _derive_category(None) == "Item"


def test_derive_category_unknown():
    assert _derive_category("typeclasses.items.something_new.FooItem") == "Item"


def test_build_metadata_basic():
    row = {
        "nftoken_id": "abc123",
        "uri_id": 42,
        "metadata": {},
        "item_name": "Bronze Longsword",
        "item_description": "A broad bronze blade.",
        "item_typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
        "item_prototype_key": "bronze_longsword",
    }
    result = build_metadata(row)
    assert result["type"] == "game_item"
    assert result["name"] == "Bronze Longsword"
    assert result["description"] == "A broad bronze blade."
    assert result["collection"]["name"] == "FullCircleMUD"
    assert "primary_display" in result["properties"]
    assert result["properties"]["primary_display"]["primary_uri"].endswith("bronze_longsword.png")

    attrs = result["properties"]["attributes"]
    categories = [a for a in attrs if a["attribute_name"] == "Category"]
    assert len(categories) == 1
    assert categories[0]["value"] == "Weapon"


def test_build_metadata_with_instance_metadata():
    row = {
        "nftoken_id": "abc123",
        "uri_id": 42,
        "metadata": {"durability": 85, "custom_name": "Excalibur"},
        "item_name": "Bronze Longsword",
        "item_description": "A broad bronze blade.",
        "item_typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
        "item_prototype_key": "bronze_longsword",
    }
    result = build_metadata(row)
    attrs = {a["attribute_name"]: a for a in result["properties"]["attributes"]}
    assert "Durability" in attrs
    assert attrs["Durability"]["value"] == 85
    assert attrs["Durability"]["value_type"] == "int"
    assert "Custom Name" in attrs
    assert attrs["Custom Name"]["value"] == "Excalibur"


def test_build_metadata_name_override():
    row = {
        "nftoken_id": "abc123",
        "uri_id": 42,
        "metadata": {"name": "The Blade of Kings"},
        "item_name": "Bronze Longsword",
        "item_description": "A broad bronze blade.",
        "item_typeclass": "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
        "item_prototype_key": "bronze_longsword",
    }
    result = build_metadata(row)
    assert result["name"] == "The Blade of Kings"


def test_build_metadata_no_prototype():
    row = {
        "nftoken_id": "abc123",
        "uri_id": 42,
        "metadata": {},
        "item_name": "Mystery Item",
        "item_description": "",
        "item_typeclass": "typeclasses.items.base_nft_item.BaseNFTItem",
        "item_prototype_key": None,
    }
    result = build_metadata(row)
    assert "primary_display" not in result["properties"]
    assert result["description"] == "A Mystery Item from FullCircleMUD."
