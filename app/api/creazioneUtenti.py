from flask import Blueprint, jsonify, request, g
from werkzeug.security import generate_password_hash

bp = Blueprint("creazioneUtenti", __name__)

VALID_ROLES = {"admin", "automobilista", "perito", "officina", "assicuratore", "azienda"}


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

    # Validazione ruoli
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

    ruolo_set = ",".join(roles_input) if roles_input else "automobilista"

    pwd_hash = generate_password_hash(password)

    try:
        g.db.execute(
            "INSERT INTO Utente (nome, cognome, email, telefono, password_hash, ruolo) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (nome, cognome, email, telefono or None, pwd_hash, ruolo_set)
        )
        new_id = g.db.lastrowid
    except Exception as e:
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
            "ruolo": roles_input or ["automobilista"],
        }
    }), 201
