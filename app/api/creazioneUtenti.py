from flask import Blueprint, jsonify, request, g, current_app
from werkzeug.security import generate_password_hash

from ..services.keycloak_service import (
    KeycloakEmailConflictError,
    KeycloakError,
    kc_assign_realm_roles,
    kc_create_user,
    kc_delete_user,
)

bp = Blueprint("creazioneUtenti", __name__)

VALID_ROLES = {"admin", "automobilista", "perito", "officina", "assicuratore", "soccorso", "azienda"}


def _inconsistent_state_response():
    return jsonify({
        "error": "INCONSISTENT_STATE",
        "message": "Stato inconsistente nel servizio identità, contattare l'amministratore"
    }), 500


def _keycloak_unavailable_response():
    return jsonify({
        "error": "KEYCLOAK_UNAVAILABLE",
        "message": "Servizio identità non disponibile, riprova più tardi"
    }), 502


@bp.post("/users")
def create_user_endpoint():
    """
    Crea un nuovo utente.

    Body JSON:
    {
        "nome": "Mario",
        "cognome": "Rossi",
        "email": "mario@example.com",
        "password": "SecretPass123",
        "telefono": "3331234567",
        "ruolo": "automobilista,perito"
    }

    Ordine delle operazioni:
      1) Validazione input
      2) Creazione utente su Keycloak (source of truth dell'identità)
      3) Assegnazione realm roles su Keycloak
      4) Insert su MySQL con keycloak_id
      5) In caso di errore nei passi 3/4 → rollback compensativo (delete su KC)
    """
    data = request.get_json(silent=True) or {}

    nome = (data.get("nome") or "").strip()
    cognome = (data.get("cognome") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    roles_raw = data.get("ruolo", "")

    missing = [f for f, v in [("nome", nome), ("cognome", cognome),
                               ("email", email), ("password", password)] if not v]
    if missing:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": f"Campi obbligatori mancanti: {', '.join(missing)}"
        }), 400

    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"error": "BAD_REQUEST", "message": "Formato email non valido"}), 400

    if isinstance(roles_raw, list):
        roles_input = [str(r).strip().lower() for r in roles_raw]
    else:
        roles_input = [r.strip().lower() for r in str(roles_raw).split(",") if r.strip()]

    invalid = [r for r in roles_input if r not in VALID_ROLES]
    if invalid:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": f"Ruoli non riconosciuti: {', '.join(invalid)}. "
                       f"Ruoli ammessi: {', '.join(sorted(VALID_ROLES))}"
        }), 400

    final_roles = roles_input if roles_input else ["automobilista"]
    ruolo_set = ",".join(final_roles)

    try:
        kc_id = kc_create_user(
            email=email,
            nome=nome,
            cognome=cognome,
            password=password,
            telefono=telefono or None,
        )
    except KeycloakEmailConflictError:
        return jsonify({"error": "BAD_REQUEST", "message": "Email già registrata"}), 400
    except KeycloakError as e:
        current_app.logger.error("Keycloak: creazione utente fallita: %s", e)
        return _keycloak_unavailable_response()

    try:
        kc_assign_realm_roles(kc_id, final_roles)
    except KeycloakError as e:
        current_app.logger.error(
            "Keycloak: assegnazione ruoli fallita per %s: %s", kc_id, e
        )
        if not kc_delete_user(kc_id):
            return _inconsistent_state_response()
        return _keycloak_unavailable_response()

    pwd_hash = generate_password_hash(password)
    try:
        g.db.execute(
            "INSERT INTO Utente (nome, cognome, email, telefono, password_hash, ruolo, keycloak_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (nome, cognome, email, telefono or None, pwd_hash, ruolo_set, kc_id)
        )
        new_id = g.db.lastrowid
    except Exception as e:
        current_app.logger.error(
            "MySQL: insert utente fallita, rollback Keycloak %s: %s", kc_id, e
        )
        rollback_ok = kc_delete_user(kc_id)
        if not rollback_ok:
            return _inconsistent_state_response()
        if "Duplicate entry" in str(e):
            return jsonify({"error": "BAD_REQUEST", "message": "Email già registrata"}), 400
        raise

    return jsonify({
        "message": "Utente creato con successo",
        "user": {
            "id": new_id,
            "nome": nome,
            "cognome": cognome,
            "email": email,
            "ruolo": final_roles,
        }
    }), 201
