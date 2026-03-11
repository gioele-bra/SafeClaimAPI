from flask import Blueprint, jsonify, request
from ..services.token_service import issue_token, get_current_user
from ..services.user_service import (
    get_user_list, get_user_count, get_active_roles, 
    activate_user, delete_user, search_users
)

bp = Blueprint("gestioneUtenti", __name__)

# Endpoint originale per login/token
@bp.post("/")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()

    if not username:
        return jsonify({"error": "BAD_REQUEST", "message": "username obbligatorio"}), 400

    token = issue_token(username)
    return jsonify({"access_token": token, "token_type": "bearer"}), 200

# RICHIESTA UTENTI (lista completa con email, nome, cognome)
@bp.get("/utenti")
def get_utenti():
    """Restituisce lista utenti con email, nome, cognome"""
    try:
        users = get_user_list()
        return jsonify({
            "utenti": [{
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nome": user.nome,
                "cognome": user.cognome,
                "attivo": user.attivo,
                "ruolo": user.ruolo
            } for user in users]
        }), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# NUMERO UTENTI DISPONIBILI
@bp.get("/utenti/count")
def get_numero_utenti():
    """Restituisce numero totale utenti disponibili"""
    try:
        count = get_user_count()
        return jsonify({"totale_utenti": count}), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# RUOLI ATTIVI
@bp.get("/utenti/ruoli")
def get_ruoli_attivi():
    """Restituisce lista ruoli attivi"""
    try:
        ruoli = get_active_roles()
        return jsonify({"ruoli_attivi": ruoli}), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# ATTIVAZIONE UTENTE
@bp.patch("/utenti/<int:user_id>/attiva")
@get_current_user  # Decoratore per verificare token e autorizzazione
def attiva_utente(user_id):
    """Attiva un utente specifico"""
    try:
        result = activate_user(user_id)
        if result:
            return jsonify({"message": f"Utente {user_id} attivato con successo"}), 200
        else:
            return jsonify({"error": "UTENTE_NON_TROVATO", "message": "Utente non trovato"}), 404
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# ELIMINA UTENTE
@bp.delete("/utenti/<int:user_id>")
@get_current_user
def elimina_utente(user_id):
    """Elimina un utente specifico"""
    try:
        result = delete_user(user_id)
        if result:
            return jsonify({"message": f"Utente {user_id} eliminato con successo"}), 200
        else:
            return jsonify({"error": "UTENTE_NON_TROVATO", "message": "Utente non trovato"}), 404
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# CERCA UTENTI
@bp.get("/utenti/cerca")
def cerca_utenti():
    """Cerca utenti per nome, cognome, email o username"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "BAD_REQUEST", "message": "parametro 'q' obbligatorio"}), 400
    
    try:
        users = search_users(query)
        return jsonify({
            "utenti_trovati": [{
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "nome": user.nome,
                "cognome": user.cognome,
                "attivo": user.attivo
            } for user in users]
        }), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500

# Esempio di GET singolo utente per completezza
@bp.get("/utenti/<int:user_id>")
def get_singolo_utente(user_id):
    """Ottiene dettagli singolo utente"""
    try:
        user = get_user_list(user_id=user_id).first()  # Implementazione nel service
        if not user:
            return jsonify({"error": "UTENTE_NON_TROVATO"}), 404
        
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "nome": user.nome,
            "cognome": user.cognome,
            "attivo": user.attivo,
            "ruolo": user.ruolo
        }), 200
    except Exception as e:
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500


#"Metodo","Endpoint","Descrizione"
#"POST","/","Login (token) [ESISTENTE]"
#"GET","/utenti","Lista utenti completa"
#"GET","/utenti/count","Numero utenti totali"
#"GET","/utenti/ruoli","Ruoli attivi"
#"PATCH","/utenti/:id/attiva","Attiva utente"
#"DELETE","/utenti/:id","Elimina utente"
#"GET","/utenti/cerca?q=","Cerca utenti (query param)"
