import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.config import Config
from app.api import impostazioni
from app.services import mysql_service


class FakeCollection:
    def __init__(self, document=None):
        self.document = document or None
        self.last_update = None

    def find_one(self, query):
        if self.document and self.document.get("chiave") == query["chiave"]:
            return self.document
        return None

    def update_one(self, query, update, upsert=False):
        self.last_update = {
            "query": query,
            "update": update,
            "upsert": upsert
        }
        document = self.document or {
            "chiave": query["chiave"],
            "ambito": "soccorso"
        }

        for key, value in update.get("$set", {}).items():
            target = document
            parts = key.split(".")
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value

        self.document = document


@pytest.fixture
def impostazioni_client(monkeypatch):
    fake_collection = FakeCollection()

    class DummyMySQLService:
        def close(self):
            pass

    monkeypatch.setattr(Config, "MYSQL_HOST", "")
    monkeypatch.setattr(mysql_service, "MySQLService", DummyMySQLService)

    app = create_app()
    app.testing = True

    monkeypatch.setattr(
        impostazioni,
        "_get_settings_collection",
        lambda: fake_collection
    )

    return app.test_client(), fake_collection


def test_get_impostazioni_defaults_without_mongo_document(impostazioni_client):
    client, _ = impostazioni_client

    response = client.get("/api/impostazioni/")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["profilo"]["nome"] == "Soccorso SafeClaim"
    assert data["profilo"]["avatar_url"] is None
    assert data["notifiche"] == {"push": None, "email": None, "sms": None}
    assert data["parametri_operativi"]["operativo_online"] is None


def test_get_impostazioni_merges_mongo_document(impostazioni_client):
    client, fake_collection = impostazioni_client
    fake_collection.document = {
        "chiave": "soccorso",
        "ambito": "soccorso",
        "profilo": {"avatar_url": "https://cdn/avatar.png"},
        "notifiche": {"push": True, "email": False, "sms": True},
        "parametri_operativi": {"max_coda": 5}
    }

    response = client.get("/api/impostazioni/")

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["profilo"]["avatar_url"] == "https://cdn/avatar.png"
    assert data["notifiche"]["push"] is True
    assert data["parametri_operativi"]["max_coda"] == 5
    assert data["parametri_operativi"]["orario_inizio"] is None


def test_patch_profilo_updates_mongo(impostazioni_client):
    client, fake_collection = impostazioni_client

    response = client.patch(
        "/api/impostazioni/profilo",
        json={
            "nome": "Centrale Soccorso",
            "email_contatto": "soccorso@example.com",
            "telefono_contatto": "02 000000",
            "avatar_url": "https://cdn/avatar.png"
        }
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["nome"] == "Centrale Soccorso"
    assert fake_collection.document["profilo"]["email_contatto"] == "soccorso@example.com"
    assert fake_collection.document["profilo"]["avatar_url"] == "https://cdn/avatar.png"
    assert fake_collection.last_update["upsert"] is True


def test_patch_profilo_validates_string_values(impostazioni_client):
    client, _ = impostazioni_client

    response = client.patch(
        "/api/impostazioni/profilo",
        json={"nome": 123}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "BAD_REQUEST"


def test_patch_notifiche_validates_boolean_values(impostazioni_client):
    client, _ = impostazioni_client

    response = client.patch(
        "/api/impostazioni/notifiche",
        json={"push": "yes"}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "BAD_REQUEST"


def test_patch_notifiche_upserts_mongo_values(impostazioni_client):
    client, fake_collection = impostazioni_client

    response = client.patch(
        "/api/impostazioni/notifiche",
        json={"push": True, "email": False}
    )

    assert response.status_code == 200
    assert response.get_json()["data"]["push"] is True
    assert response.get_json()["data"]["email"] is False
    assert fake_collection.last_update["upsert"] is True


def test_patch_parametri_operativi_validates_time(impostazioni_client):
    client, _ = impostazioni_client

    response = client.patch(
        "/api/impostazioni/parametri-operativi",
        json={"orario_inizio": "25:99"}
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "BAD_REQUEST"


def test_patch_parametri_operativi_upserts_mongo_values(impostazioni_client):
    client, fake_collection = impostazioni_client

    response = client.patch(
        "/api/impostazioni/parametri-operativi",
        json={
            "operativo_online": True,
            "orario_inizio": "08:00",
            "orario_fine": "18:30",
            "max_coda": 12,
            "accettazione_automatica": False
        }
    )

    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["operativo_online"] is True
    assert data["orario_inizio"] == "08:00"
    assert data["orario_fine"] == "18:30"
    assert data["max_coda"] == 12
    assert data["accettazione_automatica"] is False
    assert fake_collection.last_update["upsert"] is True


def test_empty_payload_returns_400(impostazioni_client):
    client, _ = impostazioni_client

    response = client.patch("/api/impostazioni/notifiche", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "BAD_REQUEST"
