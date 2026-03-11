from flask import Blueprint, jsonify, request
from ..services import create_user, UserAlreadyExistsError

bp = Blueprint("creazioneUtenti", __name__)

VALID_ROLES = {"admin", "soccorso", "officina", "perito"}


def _validate_roles(roles: list) -> tuple[list, list]:
    """Restituisce (ruoli_validi, ruoli_non_validi)."""
    valid = [r for r in roles if r in VALID_ROLES]
    invalid = [r for r in roles if r not in VALID_ROLES]
    return valid, invalid


@bp.post("/users")
def create_user_endpoint():
    """
    Crea un nuovo utente.

    Body JSON:
    {
        "username": "mario",
        "email": "mario@example.com",
        "password": "SecretPass123",
        "roles": ["admin", "perito"]   // lista di ruoli attivi nel DB
    }
    """
    data = request.get_json(silent=True) or {}

    # --- Campi obbligatori ---
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    roles_raw = data.get("roles", [])

    # --- Validazione campi base ---
    missing = [f for f, v in [("username", username), ("email", email), ("password", password)] if not v]
    if missing:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": f"Campi obbligatori mancanti: {', '.join(missing)}"
        }), 400

    # --- Validazione formato email (semplice) ---
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Formato email non valido"
        }), 400

    # --- Validazione ruoli ---
    if not isinstance(roles_raw, list):
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Il campo 'roles' deve essere una lista di stringhe"
        }), 400

    # Normalizza in lowercase e rimuovi duplicati
    roles_input = list({str(r).strip().lower() for r in roles_raw})

    valid_roles, invalid_roles = _validate_roles(roles_input)

    if invalid_roles:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": f"Ruoli non riconosciuti: {', '.join(invalid_roles)}. "
                       f"Ruoli ammessi: {', '.join(sorted(VALID_ROLES))}"
        }), 400

    # --- Creazione utente tramite service ---
    try:
        user = create_user(
            username=username,
            email=email,
            password=password,
            roles=valid_roles,
        )
    except UserAlreadyExistsError as e:
        return jsonify({
            "error": "CONFLICT",
            "message": str(e)
        }), 409
    except Exception:
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "Errore interno durante la creazione dell'utente"
        }), 500

    return jsonify({
        "message": "Utente creato con successo",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles,
        }
    }), 201