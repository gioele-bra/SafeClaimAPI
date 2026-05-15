from flask import Blueprint, current_app, g, jsonify, request

from ..services.keycloak_service import (
    KeycloakError,
    kc_set_password,
    kc_update_user,
    kc_verify_password,
)

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

    ruoli = list(user["ruolo"]) if user["ruolo"] else []

    response = jsonify({
        "message": "Login OK (mock)",
        "user": {
            "id": user["id"],
            "nome": user["nome"],
            "cognome": user["cognome"],
            "email": user["email"],
            "ruolo": ruoli,
        }
    })
    # Endpoint legacy: i client devono autenticarsi direttamente contro Keycloak.
    response.headers["X-Deprecated"] = "true"
    return response, 200


@bp.get("/status")
def auth_status():
    return jsonify({
        "message": "Autenticazione gestita da Keycloak (mock attivo)",
        "provider": "mock"
    }), 200


# ---------------------------------------------------------------------------
# /me — profilo dell'utente loggato
# ---------------------------------------------------------------------------


def _normalize_roles(value):
    if value is None:
        return []
    if isinstance(value, (set, list, tuple)):
        return [str(r) for r in value if r]
    if isinstance(value, str):
        return [r.strip() for r in value.split(",") if r.strip()]
    return []


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _lookup_user_row(kc_id: str | None, email: str | None):
    g.db.execute(
        "SELECT id, nome, cognome, email, telefono, ruolo, keycloak_id "
        "FROM Utente WHERE keycloak_id = %s OR email = %s LIMIT 1",
        (kc_id, email),
    )
    return g.db.fetchone()


def _build_me_payload(row, fallback_claims) -> dict:
    payload = {
        "id": (row or {}).get("id"),
        "nome": (row or {}).get("nome") or (fallback_claims or {}).get("given_name"),
        "email": (row or {}).get("email") or (fallback_claims or {}).get("email")
                  or (fallback_claims or {}).get("preferred_username"),
        "telefono": (row or {}).get("telefono"),
        "ruolo": _normalize_roles((row or {}).get("ruolo"))
                  or (fallback_claims or {}).get("roles") or [],
    }
    cognome = (row or {}).get("cognome")
    # Cognome blank → completamente omesso dalla response.
    if not _is_blank(cognome):
        payload["cognome"] = cognome
    return payload


@bp.get("/me")
def get_me():
    current = getattr(g, "current_user", None) or {}
    kc_id = current.get("sub")
    email = current.get("email") or current.get("preferred_username")

    row = _lookup_user_row(kc_id, email)
    return jsonify({"status": "success", "data": _build_me_payload(row, current)}), 200


@bp.patch("/me")
def patch_me():
    current = getattr(g, "current_user", None) or {}
    kc_id = current.get("sub")
    if not kc_id:
        return jsonify({"error": "UNAUTHORIZED", "message": "Sessione non valida"}), 401

    data = request.get_json(silent=True) or {}
    allowed = {"nome", "telefono"}  # cognome non self-modificabile
    fields = {}
    for k, v in data.items():
        if k not in allowed:
            continue
        if v is None:
            continue
        if isinstance(v, str):
            v = v.strip()
        fields[k] = v

    # Esplicito: rifiuta cognome se passato.
    if "cognome" in data:
        return jsonify({
            "error": "FORBIDDEN_FIELD",
            "message": "Il campo cognome non è modificabile dalle proprie impostazioni",
        }), 400

    if not fields:
        return jsonify({"error": "BAD_REQUEST", "message": "Nessun campo modificabile"}), 400

    row = _lookup_user_row(kc_id, current.get("email") or current.get("preferred_username"))
    if not row:
        return jsonify({"error": "NOT_FOUND", "message": "Utente non presente nel DB"}), 404

    set_clause = ", ".join(f"{k} = %s" for k in fields)
    g.db.execute(
        f"UPDATE Utente SET {set_clause} WHERE id = %s",
        (*fields.values(), row["id"]),
    )

    # Sync best-effort su Keycloak (firstName / attribute telefono).
    kc_payload = {}
    if "nome" in fields:
        kc_payload["firstName"] = fields["nome"]
    if "telefono" in fields:
        kc_payload["attributes"] = {"telefono": [fields["telefono"]]}

    sync_warning = None
    if kc_payload:
        try:
            kc_update_user(kc_id, kc_payload)
        except KeycloakError as e:
            current_app.logger.error("Sync Keycloak fallito per %s: %s", kc_id, e)
            sync_warning = "Aggiornato localmente, sync identity provider fallito"

    row = _lookup_user_row(kc_id, current.get("email") or current.get("preferred_username"))
    body = {"status": "success", "data": _build_me_payload(row, current)}
    if sync_warning:
        body["warning"] = sync_warning
    return jsonify(body), 200


@bp.post("/me/password")
def change_password():
    current = getattr(g, "current_user", None) or {}
    kc_id = current.get("sub")
    username = current.get("preferred_username") or current.get("email")
    if not kc_id or not username:
        return jsonify({"error": "UNAUTHORIZED", "message": "Sessione non valida"}), 401

    data = request.get_json(silent=True) or {}
    old_password = (data.get("old_password") or "").strip()
    new_password = (data.get("new_password") or "").strip()

    if not old_password or not new_password:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "old_password e new_password sono obbligatori",
        }), 400
    if len(new_password) < 8:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "La nuova password deve avere almeno 8 caratteri",
        }), 400
    if new_password == old_password:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "La nuova password deve essere diversa da quella attuale",
        }), 400

    try:
        if not kc_verify_password(username, old_password):
            return jsonify({
                "error": "INVALID_OLD_PASSWORD",
                "message": "Password attuale errata",
            }), 401
        kc_set_password(kc_id, new_password)
    except KeycloakError as e:
        current_app.logger.error("Cambio password fallito per %s: %s", kc_id, e)
        return jsonify({
            "error": "KEYCLOAK_UNAVAILABLE",
            "message": "Servizio identità non disponibile",
        }), 502

    return jsonify({"status": "success", "message": "Password aggiornata correttamente"}), 200
