from .soccorsi import bp as soccorsi_bp
from .auth import bp as auth_bp
from .admin import bp as admin_bp
from .common import bp as common_bp
from .gestioneUtenti import bp as gestioneUtenti_bp
from .creazioneUtenti import bp as creazioneUtenti_bp
from .richieste import bp as richieste_bp
from .analytics import bp as analytics_bp
from .dashboard import bp as dashboard_bp
from .dettaglio_intervento import bp as dettaglio_intervento_bp

def register_blueprints(app):
    app.register_blueprint(common_bp, url_prefix="/api/common")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(soccorsi_bp, url_prefix="/api/soccorsi")
    app.register_blueprint(gestioneUtenti_bp, url_prefix="/api/gestioneUtenti")
    app.register_blueprint(creazioneUtenti_bp, url_prefix="/api/creazioneUtenti")
    app.register_blueprint(richieste_bp, url_prefix="/api/richieste")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(dettaglio_intervento_bp, url_prefix="/api/dettaglioIntervento")
