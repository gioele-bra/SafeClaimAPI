"""Registrazione dei blueprint sotto `/api/v1/...` (canonical) e
sotto i vecchi prefissi (legacy alias). Vedi `handoff.md` §13 per il
mapping completo.
"""

from .auth import bp as auth_bp
from .common import bp as common_bp
from .utenti import (
    bp as utenti_bp,
    legacy_gestione_bp,
    legacy_creazione_bp,
    legacy_home_admin_bp,
)
from .sinistri import bp as sinistri_bp, legacy_bp as sinistri_legacy_bp
from .dashboard import bp as dashboard_bp, legacy_bp as dashboard_legacy_bp
from .analytics import bp as analytics_bp, legacy_bp as analytics_legacy_bp
from .veicoli import bp as veicoli_bp, legacy_bp as veicoli_legacy_bp
from .soccorsi import bp as soccorsi_bp
from .impostazioni import bp as impostazioni_bp
from .documentation import bp as documentation_bp


def register_blueprints(app):
    # --- Canonical /api/v1/* ---------------------------------------------
    app.register_blueprint(common_bp,       url_prefix="/api/v1")
    app.register_blueprint(auth_bp,         url_prefix="/api/v1/auth")
    app.register_blueprint(utenti_bp,       url_prefix="/api/v1/utenti")
    app.register_blueprint(sinistri_bp,     url_prefix="/api/v1/sinistri")
    app.register_blueprint(dashboard_bp,    url_prefix="/api/v1/dashboard")
    app.register_blueprint(analytics_bp,    url_prefix="/api/v1/analytics")
    app.register_blueprint(veicoli_bp,      url_prefix="/api/v1/veicoli")
    app.register_blueprint(soccorsi_bp,     url_prefix="/api/v1/soccorsi")
    app.register_blueprint(impostazioni_bp, url_prefix="/api/v1/impostazioni")

    # --- Legacy alias (mantenuti per compat client pre-v1) ---------------
    app.register_blueprint(common_bp,
                            url_prefix="/api/common", name="common_legacy")
    app.register_blueprint(auth_bp,
                            url_prefix="/api/auth", name="auth_legacy")
    app.register_blueprint(legacy_gestione_bp,
                            url_prefix="/api/gestioneUtenti")
    app.register_blueprint(legacy_creazione_bp,
                            url_prefix="/api/creazioneUtenti")
    app.register_blueprint(legacy_home_admin_bp,
                            url_prefix="/api/home-admin")
    app.register_blueprint(sinistri_legacy_bp,
                            url_prefix="/api/dettaglioIntervento")
    app.register_blueprint(dashboard_legacy_bp,
                            url_prefix="/api/dashboard")
    app.register_blueprint(analytics_legacy_bp,
                            url_prefix="/api/analytics")
    app.register_blueprint(veicoli_legacy_bp,
                            url_prefix="/api/flotta")
    app.register_blueprint(soccorsi_bp,
                            url_prefix="/api/soccorsi", name="soccorsi_legacy")
    app.register_blueprint(impostazioni_bp,
                            url_prefix="/api/impostazioni", name="impostazioni_legacy")

    # Documentazione (path invariato, vedi auth interna in documentation.py).
    app.register_blueprint(documentation_bp, url_prefix="/documentation")
