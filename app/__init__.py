from flask import Flask, jsonify
from .config import Config
from .extensions import cors, init_mysql
from .errors import register_error_handlers
from .api import register_blueprints

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

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