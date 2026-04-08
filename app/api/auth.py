from flask import Blueprint, jsonify, request, g
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)

# TODO: Sostituire con Keycloak.
# Mock temporaneo: accetta qualsiasi email presente in Utente con password "admin123".

MOCK_PASSWORD = "admin123"


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"error": "BAD_REQUEST", "message": "email e password obbligatori"}), 400

    if password != MOCK_PASSWORD:
        return jsonify({"error": "UNAUTHORIZED", "message": "Credenziali non valide"}), 401

    g.db.execute("SELECT id, nome, cognome, email, ruolo FROM Utente WHERE email = %s", (email,))
    user = g.db.fetchone()

    if not user:
        return jsonify({"error": "UNAUTHORIZED", "message": "Credenziali non valide"}), 401

    ruoli = user["ruolo"].split(",") if user["ruolo"] else []

    return jsonify({
        "message": "Login OK (mock)",
        "user": {
            "id": user["id"],
            "nome": user["nome"],
            "cognome": user["cognome"],
            "email": user["email"],
            "ruolo": ruoli,
        }
    }), 200


@bp.get("/status")
def auth_status():
    return jsonify({
        "message": "Autenticazione gestita da Keycloak (mock attivo)",
        "provider": "mock"
    }), 200
