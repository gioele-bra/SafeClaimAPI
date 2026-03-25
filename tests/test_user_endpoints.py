import os
import sys
import pytest
from types import SimpleNamespace

# ensure project root on path so "app" package is importable during tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app


@pytest.fixture
def client(monkeypatch):
    app = create_app()
    app.testing = True
    return app.test_client()


def _patch_user_service(monkeypatch):
    # crea alcuni "utenti" fittizi con differenti stati
    users = [
        SimpleNamespace(id=1, username="u1", email="u1@x", nome="U1", cognome="Uno", attivo=True, ruolo="r1"),
        SimpleNamespace(id=2, username="u2", email="u2@x", nome="U2", cognome="Due", attivo=False, ruolo="r2"),
        SimpleNamespace(id=3, username="u3", email="u3@x", nome="U3", cognome="Tre", attivo=True, ruolo="r3"),
    ]

    def fake_get_user_list(active_only=False, user_id=None):
        result = users
        if active_only:
            result = [u for u in result if u.attivo]
        if user_id is not None:
            result = [u for u in result if u.id == user_id]
        return result

    def fake_get_user_count(active_only=False):
        if active_only:
            return len([u for u in users if u.attivo])
        return len(users)

    monkeypatch.setattr('app.api.gestioneUtenti.get_user_list', fake_get_user_list)
    monkeypatch.setattr('app.api.gestioneUtenti.get_user_count', fake_get_user_count)


def test_list_active_users_and_counts(client, monkeypatch):
    _patch_user_service(monkeypatch)

    # lista utenti attivi
    resp = client.get('/api/gestioneUtenti/utenti/attivi')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert 'utenti' in data
    assert len(data['utenti']) == 2
    assert all(u['attivo'] for u in data['utenti'])

    # conteggio totale
    resp = client.get('/api/gestioneUtenti/utenti/count')
    assert resp.status_code == 200
    assert resp.get_json().get('totale_utenti') == 3

    # conteggio utenti attivi tramite query param
    resp = client.get('/api/gestioneUtenti/utenti/count?attivo=true')
    assert resp.status_code == 200
    assert resp.get_json().get('totale_utenti_attivi') == 2


def test_list_all_users_returns_everyone(client, monkeypatch):
    _patch_user_service(monkeypatch)

    resp = client.get('/api/gestioneUtenti/utenti')
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data['utenti']) == 3


def test_count_active_false_by_default(client, monkeypatch):
    _patch_user_service(monkeypatch)
    resp = client.get('/api/gestioneUtenti/utenti/count?attivo=false')
    # should still return totale_utenti, not totale_utenti_attivi
    assert resp.status_code == 200
    assert 'totale_utenti' in resp.get_json()
