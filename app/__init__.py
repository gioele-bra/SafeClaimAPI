from flask import Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import Config
from .extensions import cors, init_mysql
from .errors import register_error_handlers
from .api import register_blueprints
from .auth_middleware import register_auth_middleware

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # L'app gira dietro Nginx Proxy Manager. Senza ProxyFix, Flask non si
    # fida degli header X-Forwarded-* e genera URL assoluti (es. il
    # redirect_uri OIDC della doc) usando scheme/host interni invece di
    # `https://safeclaim.giobra.com`. ProxyFix legge X-Forwarded-Proto/
    # X-Forwarded-Host dal primo hop e li applica al request.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_for=1)

    # Session cookie hardening (usata da /documentation/ con OIDC).
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = True  # solo HTTPS in produzione
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Configurazione CORS aggiornata ed espansa per evitare i blocchi
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Origin"]
        }
    })

    init_mysql(app)

    register_error_handlers(app)
    register_auth_middleware(app)
    register_blueprints(app)

    import atexit
    from .services.mysql_service import MySQLService

    @atexit.register
    def close_db_connection():
        """Chiude la connessione a MySQL quando il processo dell'app termina."""
        MySQLService().close()

    @app.get("/")
    def index():
        return jsonify({"name": "SafeClaim API", "status": "ok"})

    return app