from flask import Flask, jsonify
from .config import Config
from .extensions import cors, init_mysql
from .errors import register_error_handlers
from .api import register_blueprints


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    init_mysql(app)

    register_error_handlers(app)
    register_blueprints(app)

    @app.get("/")
    def index():
        return jsonify({"name": "SafeClaim API", "status": "ok"})

    return app
