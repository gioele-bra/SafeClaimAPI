import os
import sys
import pytest

# ensure project root on path so "app" package is importable during tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app.services.mongo_service import MongoDBService


@pytest.fixture
def client(monkeypatch):
    # create flask test client with patched service methods
    app = create_app()
    app.testing = True

    # patch service so it doesn't try to connect to real db
    class DummyService:
        def get_active_users(self):
            return [{"_id": "1", "username": "user1"}]

        def get_users_by_category(self, category):
            return [{"_id": "2", "username": "user2", "category": category}]

    monkeypatch.setattr('app.api.mongo_users.MongoDBService', lambda: DummyService())
    return app.test_client()


def test_list_active_users(client):
    resp = client.get('/api/mongo/active')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data[0]['username'] == 'user1'


def test_list_active_users_by_category(client):
    resp = client.get('/api/mongo/active/category/testcat')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data[0]['category'] == 'testcat'
