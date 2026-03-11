from flask import Blueprint, jsonify, request
import uuid # Ci serve per generare ID finti quando crei un utente

bp = Blueprint("users_admin", __name__)

# ==========================================
# MOCK DATABASE (stessa struttura)
# ==========================================
MOCK_USERS = [
    {"id": "0", "username": "Giovanni", "email": "giovanni@email.com", "nome": "Giovanni", "cognome": "Rossi", "attivo": "True", "telefono": "123456", "ruolo": ["automobilista", "officina"]},
    {"id": "1", "username": "Mario", "email": "mario@email.com", "nome": "Mario", "cognome": "Verdi", "attivo": "True", "telefono": "123456", "ruolo": ["automobilista"]},
    {"id": "2", "username": "Luigi", "email": "luigi@email.com", "nome": "Luigi", "cognome": "Neri", "attivo": "False", "telefono": "123456", "ruolo": ["officina"]},
    {"id": "3", "username": "Anna", "email": "anna@email.com", "nome": "Anna", "cognome": "Bianchi", "attivo": "True", "telefono": "123456", "ruolo": ["automobilista"]},
    {"id": "4", "username": "Paola", "email": "paola@email.com", "nome": "Paola", "cognome": "Gialli", "attivo": "True", "telefono": "123456", "ruolo": ["admin"]}
]

# =========================
# GET tutti utenti
# =========================
@bp.get("/")
def list_users():
    return jsonify(MOCK_USERS), 200

# =========================
# GET conteggio utenti (Totali e Attivi)
# =========================
@bp.get("/count")
def count_all_users():
    try:
        totale = len(MOCK_USERS)
        attivi = sum(1 for user in MOCK_USERS if user.get("attivo") == "True")

        return jsonify({
            "total_users": totale,
            "active_users": attivi
        }), 200

    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR", 
            "message": f"Errore durante il conteggio: {str(e)}"
        }), 500

# =========================
# GET singolo utente
# =========================
@bp.get("/<user_id>")
def get_user(user_id):
    for user in MOCK_USERS:
        if user["id"] == str(user_id):
            return jsonify(user), 200
            
    return jsonify({"error": "NOT_FOUND", "message": "Utente non trovato"}), 404


# =========================
# CREA utente (ruoli solo alla creazione)
# =========================
@bp.post("/")
def create_user():
    data = request.get_json(silent=True) or {}

    nome = (data.get("nome") or "").strip()
    cognome = (data.get("cognome") or "").strip()
    email = (data.get("email") or "").strip()
    telefono = (data.get("telefono") or "").strip()

    if not nome or not cognome or not email or not telefono:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "nome, cognome, email e telefono sono obbligatori"
        }), 400

    # Controllo finto per email duplicata
    if any(u["email"] == email for u in MOCK_USERS):
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Email già registrata"
        }), 400

    nuovo_utente = {
        "id": str(uuid.uuid4())[:8], # Genera un ID finto e corto
        "username": nome,
        "nome": nome,
        "cognome": cognome,
        "email": email,
        "telefono": telefono,
        "attivo": "True",
        "ruolo": data.get("roles", [])
    }

    MOCK_USERS.append(nuovo_utente)

    return jsonify(nuovo_utente), 201


# =========================
# MODIFICA utente (NO RUOLI)
# =========================
@bp.put("/<user_id>")
def update_user(user_id):
    data = request.get_json(silent=True) or {}

    for user in MOCK_USERS:
        if user["id"] == str(user_id):
            user["nome"] = data.get("nome", user["nome"])
            user["cognome"] = data.get("cognome", user["cognome"])
            user["email"] = data.get("email", user["email"])
            user["telefono"] = data.get("telefono", user.get("telefono", ""))
            
            # ⚠ I RUOLI NON SI POSSONO MODIFICARE
            
            return jsonify(user), 200

    return jsonify({"error": "NOT_FOUND", "message": "Utente non trovato"}), 404