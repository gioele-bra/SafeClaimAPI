from copy import deepcopy
from flask import Blueprint, jsonify, request

# --- MOCK DATA STORE ---
# Inizializzato con i dati del tuo JSON
_settings_data = {
    "profilo": {
        "nome": "Officina Centrale",
        "email_contatto": "officina@example.com",
        "telefono_contatto": "02 1234567",
        "avatar_url": "https://..."
    },
    "officina": {
        "email": "officina@example.com",
        "telefono": "+39 02 1234567",
        "indirizzo": "Via Roma 123, Milano"
    },
    "notifiche": {
        "push": True,
        "email": True,
        "sms": False
    },
    "parametri_operativi": {
        "orario_inizio": "08:00",
        "orario_fine": "20:00",
        "max_coda": 10,
        "accettazione_automatica": False
    }
}

def get_settings():
    """Ritorna una copia profonda delle impostazioni correnti."""
    return deepcopy(_settings_data)

def update_settings(new_data):
    """Esegue un merge/update semplice delle chiavi di primo livello."""
    global _settings_data
    for key, value in new_data.items():
        if key in _settings_data and isinstance(_settings_data[key], dict):
            _settings_data[key].update(value)
        else:
            _settings_data[key] = value
    return get_settings()

# --- BLUEPRINT DEFINITION ---

bp = Blueprint("impostazioni", __name__)

@bp.get("/")
def get_all_settings():
    """Endpoint per recuperare tutte le impostazioni."""
    data = get_settings()
    return jsonify({
        "status": "success",
        "data": data
    }), 200

@bp.patch("/profilo")
def patch_profilo():
    """Aggiorna solo i dati del profilo."""
    payload = request.get_json(silent=True) or {}
    if not payload:
        return jsonify({"error": "BAD_REQUEST", "message": "Payload mancante"}), 400
    
    updated_data = update_settings({"profilo": payload})
    return jsonify({
        "message": "Profilo aggiornato con successo",
        "data": updated_data["profilo"]
    }), 200

@bp.patch("/notifiche")
def patch_notifiche():
    """Aggiorna le preferenze di notifica."""
    payload = request.get_json(silent=True) or {}
    # Validazione base per booleani
    for key in payload:
        if not isinstance(payload[key], bool):
            return jsonify({
                "error": "INVALID_FORMAT",
                "message": f"Il campo {key} deve essere booleano"
            }), 400
            
    updated_data = update_settings({"notifiche": payload})
    return jsonify({
        "message": "Preferenze notifiche salvate",
        "data": updated_data["notifiche"]
    }), 200

@bp.patch("/parametri-operativi")
def patch_parametri():
    """Aggiorna i parametri operativi dell'officina."""
    payload = request.get_json(silent=True) or {}
    
    # Esempio di validazione specifica
    if "max_coda" in payload and not isinstance(payload["max_coda"], int):
        return jsonify({"error": "BAD_REQUEST", "message": "max_coda deve essere un intero"}), 400

    updated_data = update_settings({"parametri_operativi": payload})
    return jsonify({
        "message": "Parametri operativi aggiornati",
        "data": updated_data["parametri_operativi"]
    }), 200