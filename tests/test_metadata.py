"""The metadata builder, against XLS-24 — no database needed."""

from decimal import Decimal

from app.metadata import ART_V0_SCHEMA, build_metadata, category_of


def an_item(**overrides):
    """An exported item as the database hands it back."""
    row = {
        "id": 1234,
        "metadata": {},
        "item_name": "Leather Backpack",
        "item_description": "A sturdy leather pack.",
        "item_prototype_key": "leather_backpack",
        "item_taxon": 3,
    }
    row.update(overrides)
    return row


def test_the_standard_fields_are_xls24_art_v0():
    result = build_metadata(an_item())
    assert result["schema"] == ART_V0_SCHEMA
    assert result["nftType"] == "art.v0"
    assert result["name"] == "Leather Backpack"
    assert result["description"] == "A sturdy leather pack."
    assert result["image"].endswith("leather_backpack.png")


def test_the_item_id_rides_along():
    assert build_metadata(an_item())["item_id"] == 1234


def test_the_items_own_metadata_overrides_name_and_description():
    result = build_metadata(an_item(metadata={"name": "Old Faithful", "description": "Patched."}))
    assert (result["name"], result["description"]) == ("Old Faithful", "Patched.")


def test_an_item_with_no_prototype_still_has_an_image():
    # art.v0 requires one.
    assert build_metadata(an_item(item_prototype_key=None))["image"]


def test_category_and_family_come_from_the_taxon():
    result = build_metadata(an_item(item_taxon=1))
    traits = {t["trait_type"]: t["value"] for t in result["attributes"]}
    assert traits["Category"] == "Weapon"
    assert result["collection"] == {"name": "FullCircleMUD", "family": "Weapons"}


def test_an_unknown_taxon_is_general():
    assert category_of(99) == category_of(12)


def test_scalar_metadata_becomes_traits():
    result = build_metadata(an_item(metadata={"durability": 85, "enchanted": True,
                                              "runes": ["a", "b"], "name": "x"}))
    traits = {t["trait_type"]: t["value"] for t in result["attributes"]}
    assert traits["Durability"] == 85
    assert traits["Enchanted"] == "True"
    assert "Runes" not in traits
    assert "Name" not in traits


def test_a_container_lists_everything_inside_at_any_depth():
    items = [
        {"id": 1235, "contained_in_id": 1234, "item_name": "Pouch", "metadata": {}},
        {"id": 1236, "contained_in_id": 1235, "item_name": "Iron Dagger",
         "metadata": {"durability": 40}},
    ]
    balances = [
        {"contained_in_id": 1234, "currency_name": "Gold", "balance": Decimal("50.000000")},
        {"contained_in_id": 1235, "currency_name": "Wheat", "balance": Decimal("4.5")},
    ]
    contents = build_metadata(an_item(), items, balances)["contents"]
    assert contents["balances"] == [{"currency": "Gold", "amount": "50"}]
    (pouch,) = contents["items"]
    assert (pouch["item_id"], pouch["name"]) == (1235, "Pouch")
    assert pouch["contents"]["balances"] == [{"currency": "Wheat", "amount": "4.5"}]
    (dagger,) = pouch["contents"]["items"]
    assert (dagger["item_id"], dagger["name"], dagger["metadata"]) == (
        1236, "Iron Dagger", {"durability": 40})
    assert dagger["contents"] is None


def test_a_container_carries_a_contents_summary_trait():
    items = [
        {"id": 1235, "contained_in_id": 1234, "item_name": "Pouch", "metadata": {}},
        {"id": 1236, "contained_in_id": 1235, "item_name": "Iron Dagger", "metadata": {}},
    ]
    balances = [
        {"contained_in_id": 1234, "currency_name": "Gold", "balance": Decimal("30")},
        {"contained_in_id": 1235, "currency_name": "Gold", "balance": Decimal("20")},
    ]
    result = build_metadata(an_item(), items, balances)
    traits = {t["trait_type"]: t["value"] for t in result["attributes"]}
    assert traits["Contents"] == "2 items, 50 Gold"


def test_an_item_holding_nothing_has_no_contents():
    result = build_metadata(an_item())
    assert "contents" not in result
    assert "Contents" not in {t["trait_type"] for t in result["attributes"]}
