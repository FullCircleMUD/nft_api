"""The endpoint — the database reads patched."""

from unittest import mock

from fastapi.testclient import TestClient

from app import main
from app.main import NOT_ON_LEDGER, app

client = TestClient(app)

ITEM = {
    "id": 1234,
    "metadata": {},
    "item_name": "Iron Dagger",
    "item_description": "A short iron blade.",
    "item_prototype_key": "iron_dagger",
    "item_taxon": 1,
}


def test_an_item_on_the_ledger_is_served():
    with mock.patch.object(main, "fetch_item", return_value=ITEM), \
         mock.patch.object(main, "fetch_contents", return_value=([], [])):
        response = client.get("/1234", headers={"host": "api.fcmud.world"})
    assert response.status_code == 200
    assert response.json()["name"] == "Iron Dagger"


def test_anything_not_on_the_ledger_is_not_found():
    with mock.patch.object(main, "fetch_item", return_value=None):
        response = client.get("/1234", headers={"host": "api.fcmud.world"})
    assert response.status_code == 404
    assert response.json()["detail"] == NOT_ON_LEDGER
    assert NOT_ON_LEDGER == "This item does not exist on the ledger."


def test_an_unconfigured_database_is_unavailable():
    with mock.patch.object(main, "fetch_item", side_effect=ConnectionError("dev database not configured")):
        response = client.get("/1234", headers={"host": "api.dev.fcmud.world"})
    assert response.status_code == 503
