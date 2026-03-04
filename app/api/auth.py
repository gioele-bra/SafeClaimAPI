from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from ..services.token_service import issue_token

bp = Blueprint("auth", __name__)

# --- DIZIONARIO AMMINISTRATORI ---
# Chiave: Email dell'admin
# Valore: Password criptata in modo sicuro (hash) della stringa "admin123"
ADMIN_USERS = {
    "admin@safeclaim.it": generate_password_hash("admin123")
}

# --- LOGIN UTENTE NORMALE ---
@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify({"error": "BAD_REQUEST", "message": "username obbligatorio"}), 400

    token = issue_token(username)
    return jsonify({"access_token": token, "token_type": "bearer"})


# --- LOGIN ADMIN ---
@bp.post("/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()

    # 1. Verifica che i campi non siano vuoti
    if not email or not password:
        return jsonify({"error": "BAD_REQUEST", "message": "email e password obbligatori"}), 400

    # 2. Cerca la password criptata nel dizionario usando l'email
    admin_password_hash = ADMIN_USERS.get(email)

    # 3. Verifica: se l'email non c'è (None) OPPURE la password è sbagliata, restituisci errore
    if not admin_password_hash or not check_password_hash(admin_password_hash, password):
        return jsonify({"error": "UNAUTHORIZED", "message": "Credenziali non valide"}), 401

    # 4. Genera il token includendo il ruolo di amministratore
    token = issue_token(email, role="admin")
    
    return jsonify({
        "access_token": token, 
        "token_type": "bearer",
        "role": "admin",
        "email": email
    }), 200
