import copy
import re
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from pymongo import MongoClient

bp = Blueprint("impostazioni", __name__)

SETTINGS_COLLECTION = "Proto_Impostazioni_Soccorso_SC"
SETTINGS_KEY = "soccorso"
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

DEFAULT_SETTINGS = {
    "profilo": {
        "nome": "Soccorso SafeClaim",
        "email_contatto": None,
        "telefono_contatto": None,
        "avatar_url": None
    },
    "notifiche": {
        "push": None,
        "email": None,
        "sms": None
    },
    "parametri_operativi": {
        "operativo_online": None,
        "orario_inizio": None,
        "orario_fine": None,
        "max_coda": None,
        "accettazione_automatica": None
    }
}


def _get_settings_collection():
    mongo_uri = current_app.config.get("MONGODB_URI")
    mongo_db = current_app.config.get("MONGODB_DB")

    if not mongo_uri or not mongo_db:
        raise RuntimeError("MongoDB non configurato")

    client = MongoClient(mongo_uri)
    return client[mongo_db][SETTINGS_COLLECTION]


def _get_settings_document():
    return _get_settings_collection().find_one({"chiave": SETTINGS_KEY}) or {}


def _merge_settings(document):
    settings = copy.deepcopy(DEFAULT_SETTINGS)

    for section in settings:
        section_data = document.get(section)
        if isinstance(section_data, dict):
            for key in settings[section]:
                if key in section_data:
                    settings[section][key] = section_data.get(key)

    return settings


def _updated_at():
    return datetime.utcnow().isoformat()


def _upsert_settings(set_values):
    set_values["updated_at"] = _updated_at()
    _get_settings_collection().update_one(
        {"chiave": SETTINGS_KEY},
        {
            "$set": set_values,
            "$setOnInsert": {
                "chiave": SETTINGS_KEY,
                "ambito": "soccorso"
            }
        },
        upsert=True
    )


def _bad_request(message):
    return jsonify({
        "error": "BAD_REQUEST",
        "message": message
    }), 400


def _get_json_payload():
    data = request.get_json(silent=True)

    if not data:
        return None, _bad_request("Payload mancante")

    if not isinstance(data, dict):
        return None, _bad_request("Payload non valido")

    return data, None


def _validate_boolean_payload(data, allowed_fields):
    updates = {}

    for key, value in data.items():
        if key not in allowed_fields:
            continue

        if type(value) is not bool:
            return None, f"Il campo {key} deve essere booleano"

        updates[key] = value

    return updates, None


def _validate_profilo_payload(data):
    allowed_fields = {
        "nome",
        "email_contatto",
        "telefono_contatto",
        "avatar_url"
    }
    updates = {}

    for key, value in data.items():
        if key not in allowed_fields:
            continue

        if value is not None and not isinstance(value, str):
            return None, f"Il campo {key} deve essere una stringa o null"

        updates[key] = value

    return updates, None


def _validate_parametri_payload(data):
    allowed_fields = {
        "operativo_online",
        "orario_inizio",
        "orario_fine",
        "max_coda",
        "accettazione_automatica"
    }
    updates = {}

    for key, value in data.items():
        if key not in allowed_fields:
            continue

        if key in {"operativo_online", "accettazione_automatica"}:
            if type(value) is not bool:
                return None, f"Il campo {key} deve essere booleano"

        if key in {"orario_inizio", "orario_fine"}:
            if not isinstance(value, str) or not TIME_PATTERN.match(value):
                return None, f"Il campo {key} deve essere nel formato HH:MM"

        if key == "max_coda":
            if type(value) is not int or value < 0:
                return None, "max_coda deve essere un intero maggiore o uguale a 0"

        updates[key] = value

    return updates, None


@bp.get("/")
def get_impostazioni():
    try:
        settings = _merge_settings(_get_settings_document())

        return jsonify({
            "status": "success",
            "data": settings
        }), 200

    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero delle impostazioni soccorso: {str(e)}"
        }), 500


@bp.patch("/profilo")
def update_profilo():
    try:
        data, error_response = _get_json_payload()
        if error_response:
            return error_response

        updates, validation_error = _validate_profilo_payload(data)
        if validation_error:
            return _bad_request(validation_error)

        if not updates:
            return _bad_request("Nessun campo valido da aggiornare")

        _upsert_settings({f"profilo.{key}": value for key, value in updates.items()})
        settings = _merge_settings(_get_settings_document())

        return jsonify({
            "message": "Profilo soccorso aggiornato con successo",
            "data": settings["profilo"]
        }), 200

    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore durante l'aggiornamento del profilo soccorso: {str(e)}"
        }), 500


@bp.patch("/notifiche")
def update_notifiche():
    try:
        data, error_response = _get_json_payload()
        if error_response:
            return error_response

        updates, validation_error = _validate_boolean_payload(data, {"push", "email", "sms"})
        if validation_error:
            return _bad_request(validation_error)

        if not updates:
            return _bad_request("Nessun campo valido da aggiornare")

        _upsert_settings({f"notifiche.{key}": value for key, value in updates.items()})
        settings = _merge_settings(_get_settings_document())

        return jsonify({
            "message": "Preferenze notifiche soccorso salvate",
            "data": settings["notifiche"]
        }), 200

    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore durante l'aggiornamento delle notifiche soccorso: {str(e)}"
        }), 500


@bp.patch("/parametri-operativi")
def update_parametri_operativi():
    try:
        data, error_response = _get_json_payload()
        if error_response:
            return error_response

        updates, validation_error = _validate_parametri_payload(data)
        if validation_error:
            return _bad_request(validation_error)

        if not updates:
            return _bad_request("Nessun campo valido da aggiornare")

        _upsert_settings({
            f"parametri_operativi.{key}": value
            for key, value in updates.items()
        })
        settings = _merge_settings(_get_settings_document())

        return jsonify({
            "message": "Parametri operativi soccorso aggiornati",
            "data": settings["parametri_operativi"]
        }), 200

    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore durante l'aggiornamento dei parametri operativi soccorso: {str(e)}"
        }), 500
