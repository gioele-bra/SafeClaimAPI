from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import generate_password_hash

from ..services.keycloak_service import (
    KeycloakEmailConflictError,
    KeycloakError,
    kc_assign_realm_roles,
    kc_create_user,
    kc_delete_user,
)

# Blueprint canonico per `/api/v1/utenti`.
bp = Blueprint("utenti", __name__)

# Blueprint alias per le 3 prefissi legacy (registrati separatamente in __init__).
legacy_gestione_bp = Blueprint("utenti_legacy_gestione", __name__)
legacy_creazione_bp = Blueprint("utenti_legacy_creazione", __name__)
legacy_home_admin_bp = Blueprint("utenti_legacy_home_admin", __name__)


VALID_ROLES = {"admin", "automobilista", "perito", "officina",
                "assicuratore", "soccorso", "azienda"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_roles(value):
    if value is None:
        return []
    if isinstance(value, (set, list, tuple)):
        return [str(r).strip() for r in value if r]
    if isinstance(value, str):
        return [r.strip() for r in value.split(",") if r.strip()]
    return []


def _format_user(row):
    user = dict(row)
    user.pop("password_hash", None)
    user["ruolo"] = _normalize_roles(user.get("ruolo"))
    if user.get("data_registrazione"):
        user["data_registrazione"] = user["data_registrazione"].isoformat()
    return user


def _bad_request(msg):
    return jsonify({"error": "BAD_REQUEST", "message": msg}), 400


def _not_found():
    return jsonify({"error": "NOT_FOUND", "message": "Utente non trovato"}), 404


# ---------------------------------------------------------------------------
# Handlers (canonici)
# ---------------------------------------------------------------------------


def list_utenti():
    """GET /api/v1/utenti — lista utenti con search/paginazione opzionali."""
    search = (request.args.get("search") or "").strip()
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 50)), 1), 200)
    except ValueError:
        return _bad_request("page e per_page devono essere interi")

    where_clause = ""
    params = []
    if search:
        where_clause = " WHERE nome LIKE %s OR cognome LIKE %s OR email LIKE %s"
        like = f"%{search}%"
        params = [like, like, like]

    g.db.execute(f"SELECT COUNT(*) AS total FROM Utente{where_clause}", tuple(params))
    total = (g.db.fetchone() or {}).get("total", 0)

    g.db.execute(
        f"SELECT * FROM Utente{where_clause} ORDER BY id LIMIT %s OFFSET %s",
        tuple(params + [per_page, (page - 1) * per_page]),
    )
    rows = g.db.fetchall() or []

    return jsonify({
        "utenti": [_format_user(r) for r in rows],
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page else 0,
        },
    }), 200


def count_utenti():
    g.db.execute("SELECT COUNT(*) AS totale FROM Utente")
    totale = (g.db.fetchone() or {}).get("totale", 0)
    return jsonify({"totale_utenti": totale}), 200


def get_utente(user_id):
    g.db.execute("SELECT * FROM Utente WHERE id = %s", (user_id,))
    row = g.db.fetchone()
    if not row:
        return _not_found()
    return jsonify(_format_user(row)), 200


def update_utente(user_id):
    data = request.get_json(silent=True) or {}

    g.db.execute("SELECT id FROM Utente WHERE id = %s", (user_id,))
    if not g.db.fetchone():
        return _not_found()

    fields = []
    values = []
    for col in ("nome", "cognome", "email", "telefono"):
        if col in data:
            fields.append(f"{col} = %s")
            values.append(data[col])

    if not fields:
        return _bad_request("Nessun campo da aggiornare")

    values.append(user_id)
    g.db.execute(f"UPDATE Utente SET {', '.join(fields)} WHERE id = %s", tuple(values))

    g.db.execute("SELECT * FROM Utente WHERE id = %s", (user_id,))
    return jsonify({
        "message": "Utente aggiornato",
        "utente": _format_user(g.db.fetchone()),
    }), 200


def delete_utente(user_id):
    """DELETE /api/v1/utenti/<user_id> — elimina utente da Keycloak e MySQL."""
    g.db.execute("SELECT keycloak_id FROM Utente WHERE id = %s", (user_id,))
    row = g.db.fetchone()
    if not row:
        return _not_found()

    kc_id = row.get("keycloak_id")

    # 1) Eliminazione coordinata su Keycloak
    if kc_id:
        try:
            kc_delete_user(kc_id)
        except KeycloakError as e:
            current_app.logger.error("Keycloak: eliminazione utente fallita per %s: %s", kc_id, e)
            return jsonify({
                "error": "KEYCLOAK_ERROR",
                "message": "Impossibile rimuovere l'utente dal provider di identità. Operazione interrotta."
            }), 502

    # 2) Eliminazione da MySQL
    g.db.execute("DELETE FROM Utente WHERE id = %s", (user_id,))
    
    return jsonify({
        "status": "success",
        "message": f"Utente {user_id} rimosso correttamente da database e Keycloak"
    }), 200


def update_ruoli(user_id):
    """Aggiorna i ruoli di un utente."""
    data = request.get_json(silent=True) or {}

    g.db.execute("SELECT id FROM Utente WHERE id = %s", (user_id,))
    if not g.db.fetchone():
        return _not_found()

    roles_raw = data.get("ruoli", [])
    if isinstance(roles_raw, str):
        roles_input = [r.strip().lower() for r in roles_raw.split(",") if r.strip()]
    elif isinstance(roles_raw, list):
        roles_input = [str(r).strip().lower() for r in roles_raw if r]
    else:
        roles_input = []

    invalid = [r for r in roles_input if r not in VALID_ROLES]
    if invalid:
        return _bad_request(
            f"Ruoli non riconosciuti: {', '.join(invalid)}. "
            f"Ruoli ammessi: {', '.join(sorted(VALID_ROLES))}"
        )
    if not roles_input:
        return _bad_request("Almeno un ruolo valido è obbligatorio")

    g.db.execute(
        "UPDATE Utente SET ruolo = %s WHERE id = %s",
        (",",join(roles_input), user_id),
    )
    g.db.execute("SELECT * FROM Utente WHERE id = %s", (user_id,))
    return jsonify({
        "message": "Ruoli aggiornati con successo",
        "utente": _format_user(g.db.fetchone()),
    }), 200


def stats_ruoli():
    """Conteggio utenti per ruolo (era `/api/home-admin/stats-ruoli`)."""
    g.db.execute("SELECT ruolo FROM Utente")
    rows = g.db.fetchall() or []

    stats = {}
    for row in rows:
        for r in _normalize_roles(row.get("ruolo")):
            key = r.strip().capitalize()
            if key:
                stats[key] = stats.get(key, 0) + 1
    return jsonify({"status": "success", "data": stats}), 200


def create_utente():
    """POST /api/v1/utenti — crea utente su Keycloak + MySQL con rollback."""
    data = request.get_json(silent=True) or {}

    nome = (data.get("nome") or "").strip()
    cognome = (data.get("cognome") or "").strip()
    email = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    roles_raw = data.get("ruolo", "")

    missing = [
        f for f, v in [("nome", nome), ("cognome", cognome),
                        ("email", email), ("password", password)] if not v
    ]
    if missing:
        return _bad_request(f"Campi obbligatori mancanti: {', '.join(missing)}")

    if "@" not in email or "." not in email.split("@")[-1]:
        return _bad_request("Formato email non valido")

    if isinstance(roles_raw, list):
        roles_input = [str(r).strip().lower() for r in roles_raw]
    else:
        roles_input = [r.strip().lower()
                        for r in str(roles_raw).split(",") if r.strip()]

    invalid = [r for r in roles_input if r not in VALID_ROLES]
    if invalid:
        return _bad_request(
            f"Ruoli non riconosciuti: {', '.join(invalid)}. "
            f"Ruoli ammessi: {', '.join(sorted(VALID_ROLES))}"
        )

    final_roles = roles_input if roles_input else ["automobilista"]
    ruolo_set = ",".join(final_roles)

    # 1) Keycloak create
    try:
        kc_id = kc_create_user(
            email=email, nome=nome, cognome=cognome,
            password=password, telefono=telefono or None,
        )
    except KeycloakEmailConflictError:
        return _bad_request("Email già registrata")
    except KeycloakError as e:
        current_app.logger.error("Keycloak: creazione utente fallita: %s", e)
        return jsonify({
            "error": "KEYCLOAK_UNAVAILABLE",
            "message": "Servizio identità non disponibile, riprova più tardi",
        }), 502

    # 2) Keycloak assign roles
    try:
        kc_assign_realm_roles(kc_id, final_roles)
    except KeycloakError as e:
        current_app.logger.error(
            "Keycloak: assegnazione ruoli fallita per %s: %s", kc_id, e
        )
        if not kc_delete_user(kc_id):
            return jsonify({
                "error": "INCONSISTENT_STATE",
                "message": "Stato inconsistente nel servizio identità, contattare l'amministratore",
            }), 500
        return jsonify({
            "error": "KEYCLOAK_UNAVAILABLE",
            "message": "Servizio identità non disponibile, riprova più tardi",
        }), 502

    # 3) MySQL insert (compensativo su KC se fallisce)
    pwd_hash = generate_password_hash(password)
    try:
        g.db.execute(
            "INSERT INTO Utente (nome, cognome, email, telefono, password_hash, ruolo, keycloak_id) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (nome, cognome, email, telefono or None, pwd_hash, ruolo_set, kc_id),
        )
        new_id = g.db.lastrowid
    except Exception as e:
        current_app.logger.error(
            "MySQL: insert utente fallita, rollback Keycloak %s: %s", kc_id, e
        )
        rollback_ok = kc_delete_user(kc_id)
        if not rollback_ok:
            return jsonify({
                "error": "INCONSISTENT_STATE",
                "message": "Stato inconsistente nel servizio identità, contattare l'amministratore",
            }), 500
        if "Duplicate entry" in str(e):
            return _bad_request("Email già registrata")
        raise

    return jsonify({
        "message": "Utente creato con successo",
        "user": {
            "id": new_id, "nome": nome, "cognome": cognome,
            "email": email, "ruolo": final_roles,
        },
    }), 201


# ---------------------------------------------------------------------------
# Registrazione route — canonical (Italian, kebab-case) su `bp`
# ---------------------------------------------------------------------------

bp.add_url_rule("",          "list_utenti",   list_utenti,   methods=["GET"])
bp.add_url_rule("/",         "list_utenti_s", list_utenti,   methods=["GET"])
bp.add_url_rule("",          "create_utente", create_utente, methods=["POST"])
bp.add_url_rule("/",         "create_utente_s", create_utente, methods=["POST"])
bp.add_url_rule("/count",    "count_utenti",  count_utenti,  methods=["GET"])
bp.add_url_rule("/stats-ruoli", "stats_ruoli", stats_ruoli,  methods=["GET"])
bp.add_url_rule("/<int:user_id>",       "get_utente",    get_utente,    methods=["GET"])
bp.add_url_rule("/<int:user_id>",       "update_utente", update_utente, methods=["PUT"])
bp.add_url_rule("/<int:user_id>",       "delete_utente", delete_utente, methods=["DELETE"])
bp.add_url_rule("/<int:user_id>/ruoli", "update_ruoli",  update_ruoli,  methods=["POST"])


# ---------------------------------------------------------------------------
# Alias legacy — mantenuti per compat client pre-v1
# ---------------------------------------------------------------------------

legacy_gestione_bp.add_url_rule("/utenti",        "list_legacy",   list_utenti,   methods=["GET"])
legacy_gestione_bp.add_url_rule("/utenti/",       "list_legacy_s", list_utenti,   methods=["GET"])
legacy_gestione_bp.add_url_rule("/utenti/count",  "count_legacy",  count_utenti,  methods=["GET"])
legacy_gestione_bp.add_url_rule("/utenti/<int:user_id>",       "get_legacy",    get_utente,    methods=["GET"])
legacy_gestione_bp.add_url_rule("/utenti/<int:user_id>",       "update_legacy", update_utente, methods=["PUT"])
legacy_gestione_bp.add_url_rule("/utenti/<int:user_id>",       "delete_legacy", delete_utente, methods=["DELETE"])
legacy_gestione_bp.add_url_rule("/utenti/<int:user_id>/ruoli", "ruoli_legacy",  update_ruoli,  methods=["POST"])


def _legacy_search():
    """Adatta `?q=` (legacy) a `?search=` (canonical) per /utenti/cerca."""
    q = (request.args.get("q") or "").strip()
    if not q:
        return _bad_request("parametro 'q' obbligatorio")
    like = f"%{q}%"
    g.db.execute(
        "SELECT * FROM Utente WHERE nome LIKE %s OR cognome LIKE %s OR email LIKE %s",
        (like, like, like),
    )
    rows = g.db.fetchall() or []
    return jsonify({"utenti_trovati": [_format_user(r) for r in rows]}), 200


legacy_gestione_bp.add_url_rule("/utenti/cerca", "cerca_legacy", _legacy_search, methods=["GET"])
legacy_creazione_bp.add_url_rule("/users", "create_legacy", create_utente, methods=["POST"])
legacy_home_admin_bp.add_url_rule("/stats-ruoli", "stats_ruoli_legacy", stats_ruoli, methods=["GET"])