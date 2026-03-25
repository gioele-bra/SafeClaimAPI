from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash
from ..services.token_service import issue_token, revoke_token

bp = Blueprint("auth", __name__)

# Explicitly use PBKDF2 because this Python build does not provide hashlib.scrypt.
PASSWORD_HASH_METHOD = "pbkdf2:sha256"

# --- DIZIONARIO AMMINISTRATORI ---
# Chiave: Email dell'admin
# Valore: Password criptata in modo sicuro (hash) della stringa "admin123"
ADMIN_USERS = {
    "admin@safeclaim.it": generate_password_hash("admin123", method=PASSWORD_HASH_METHOD)
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


# --- LOGOUT ---
@bp.post("/logout")
def logout():
    # 1. Estrae il token dall'header Authorization (es: "Bearer demo-token-xxx")
    auth_header = request.headers.get("Authorization")
    
    if auth_header and auth_header.startswith("Bearer "):
        # Prende solo la parte del token, scartando la parola "Bearer"
        token = auth_header.split(" ")[1]
        
        # 2. Invalida il token tramite il service
        revoke_token(token)

    # 3. Risponde al client. 
    # N.B. Il frontend dovrà occuparsi di cancellare il token dal localStorage/sessionStorage.
    return jsonify({
        "message": "Logout completato con successo"
    }), 200
