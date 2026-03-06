from flask import Blueprint, jsonify
from ..services.mongo_service import MongoDBService

bp = Blueprint("mongo_users", __name__)

@bp.get("/active")
def list_active_users():
    """Restituisce tutti gli utenti attivi memorizzati in MongoDB."""
    try:
        service = MongoDBService()
        users = service.get_active_users()
        return jsonify(users)
    except Exception as e:
        # in caso di errore durante la query restituisci un 500 generico
        return jsonify({"error": "INTERNAL_SERVER_ERROR", "message": str(e)}), 500


@bp.get("/active/category/<string:category>")
def list_active_users_by_category(category: str):
    """Restituisce gli utenti attivi appartenenti a una categoria specifica."""
    try:
        service = MongoDBService()
        users = service.get_users_by_category(category)
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": "INTERNAL_SERVER_ERROR", "message": str(e)}), 500
