"""Configurazione globale per pytest.

Bypassa il middleware JWT (`auth_middleware._enforce_auth`) sostituendo
la sua dipendenza interna con un'implementazione no-op. Il bypass è
attivo solo dentro la suite di test.
"""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app as _create_app  # noqa: E402
from app import auth_middleware  # noqa: E402


@pytest.fixture(autouse=True)
def _bypass_auth_for_tests(monkeypatch):
    """Disabilita il check di autenticazione per qualsiasi test."""
    monkeypatch.setattr(
        auth_middleware,
        "_is_whitelisted",
        lambda method, path: True,
    )


@pytest.fixture
def app():
    """Fixture pronta all'uso per nuovi test."""
    app = _create_app()
    app.config["AUTH_BYPASS_FOR_TESTS"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
