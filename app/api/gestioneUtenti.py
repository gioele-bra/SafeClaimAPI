from flask import Blueprint, jsonify, request
from functools import wraps
# Se hai questo file tienilo, altrimenti commentalo
# from ..services.token_service import issue_token 

bp = Blueprint("gestioneUtenti", __name__)

# ==========================================
# ⚠ DECORATORE FITTIZIO PER EVITARE ERRORI
# ==========================================
def get_current_user(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Qui in futuro metterai il controllo del token
        return f(*args, **kwargs)
    return decorated

# ==========================================
# MOCK DATABASE
# ==========================================
MOCK_USERS = [
    {"id": "0", "username": "Giovanni", "email": "giovanni@email.com", "nome": "Giovanni", "cognome": "Rossi", "attivo": "True", "ruolo": ["automobilista", "officina"]},
    {"id": "1", "username": "Mario", "email": "mario@email.com", "nome": "Mario", "cognome": "Verdi", "attivo": "True", "ruolo": ["automobilista"]},
    {"id": "2", "username": "Luigi", "email": "luigi@email.com", "nome": "Luigi", "cognome": "Neri", "attivo": "False", "ruolo": ["officina"]},
    {"id": "3", "username": "Anna", "email": "anna@email.com", "nome": "Anna", "cognome": "Bianchi", "attivo": "True", "ruolo": ["automobilista"]},
    {"id": "4", "username": "Paola", "email": "paola@email.com", "nome": "Paola", "cognome": "Gialli", "attivo": "True", "ruolo": ["admin"]}
]

# Endpoint originale per login/token
@bp.post("/")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify({"error": "BAD_REQUEST", "message": "username obbligatorio"}), 400

    # token = issue_token(username) # Scommenta se usi token_service
    token = "token_provvisorio_123"
    return jsonify({"access_token": token, "token_type": "bearer"}), 200

# RICHIESTA UTENTI (lista completa con email, nome, cognome)
@bp.get("/utenti")
def get_utenti():
    """Restituisce lista utenti con email, nome, cognome"""
    try:
        return jsonify({"utenti": MOCK_USERS}), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# NUMERO UTENTI ATTIVI E TOTALI
@bp.get("/utenti/count")
def get_numero_utenti():
    """Restituisce numero totale utenti e numero utenti attivi"""
    try:
        totale = len(MOCK_USERS)
        # Conta solo quelli con attivo == "True"
        attivi = sum(1 for u in MOCK_USERS if u.get("attivo") == "True")
        
        return jsonify({
            "totale_utenti": totale,
            "utenti_attivi": attivi
        }), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# RUOLI ATTIVI
@bp.get("/utenti/ruoli")
def get_ruoli_attivi():
    """Restituisce lista ruoli attivi finti"""
    try:
        ruoli = ["admin", "automobilista", "officina"]
        return jsonify({"ruoli_attivi": ruoli}), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# ATTIVAZIONE UTENTE
@bp.patch("/utenti/<user_id>/attiva")
@get_current_user  # Ora funziona senza bloccare il server
def attiva_utente(user_id):
    """Attiva un utente specifico"""
    try:
        for user in MOCK_USERS:
            if user["id"] == str(user_id):
                user["attivo"] = "True"
                return jsonify({"message": f"Utente {user_id} attivato con successo", "utente": user}), 200
        
        return jsonify({"error": "UTENTE_NON_TROVATO", "message": "Utente non trovato"}), 404
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# ELIMINA UTENTE
@bp.delete("/utenti/<user_id>")
@get_current_user
def elimina_utente(user_id):
    """Elimina un utente specifico (lo toglie dalla lista provvisoria)"""
    try:
        global MOCK_USERS
        nuova_lista = [u for u in MOCK_USERS if u["id"] != str(user_id)]
        
        if len(nuova_lista) < len(MOCK_USERS):
            MOCK_USERS = nuova_lista
            return jsonify({"message": f"Utente {user_id} eliminato con successo"}), 200
        
        return jsonify({"error": "UTENTE_NON_TROVATO", "message": "Utente non trovato"}), 404
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# CERCA UTENTI
@bp.get("/utenti/cerca")
def cerca_utenti():
    """Cerca utenti per nome, cognome, email o username"""
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify({"error": "BAD_REQUEST", "message": "parametro 'q' obbligatorio"}), 400
    
    try:
        trovati = []
        for u in MOCK_USERS:
            if (query in u["nome"].lower() or 
                query in u["cognome"].lower() or 
                query in u["email"].lower() or 
                query in u["username"].lower()):
                trovati.append(u)
                
        return jsonify({"utenti_trovati": trovati}), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# GET SINGOLO UTENTE
@bp.get("/utenti/<user_id>")
def get_singolo_utente(user_id):
    """Ottiene dettagli singolo utente"""
    try:
        for user in MOCK_USERS:
            if user["id"] == str(user_id):
                return jsonify(user), 200
                
        return jsonify({"error": "UTENTE_NON_TROVATO"}), 404
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500