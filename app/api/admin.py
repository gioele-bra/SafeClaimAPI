from flask import Blueprint, jsonify, request, g

bp = Blueprint("users_admin", __name__)


def _format_user(row):
    """Formatta una riga Utente per la risposta JSON."""
    user = dict(row)
    user.pop("password_hash", None)
    if isinstance(user.get("ruolo"), str):
        user["ruolo"] = user["ruolo"].split(",") if user["ruolo"] else []
    if user.get("data_registrazione"):
        user["data_registrazione"] = user["data_registrazione"].isoformat()
    return user


@bp.get("/")
def list_users():
    g.db.execute("SELECT * FROM Utente")
    rows = g.db.fetchall()
    return jsonify([_format_user(r) for r in rows]), 200


@bp.get("/count")
def count_all_users():
    g.db.execute("SELECT COUNT(*) AS totale FROM Utente")
    totale = g.db.fetchone()["totale"]
    return jsonify({"total_users": totale}), 200


@bp.get("/roles-report")
def get_roles_report():
    """Conta quanti utenti hanno ciascun ruolo (il SET può contenere più valori)."""
    g.db.execute("SELECT ruolo FROM Utente")
    rows = g.db.fetchall()

    report = {}
    for row in rows:
        ruoli = row["ruolo"].split(",") if row["ruolo"] else []
        for r in ruoli:
            r = r.strip().lower()
            report[r] = report.get(r, 0) + 1

    return jsonify({"status": "success", "roles_count": report}), 200


@bp.get("/<int:user_id>")
def get_user(user_id):
    g.db.execute("SELECT * FROM Utente WHERE id = %s", (user_id,))
    row = g.db.fetchone()
    if not row:
        return jsonify({"error": "NOT_FOUND", "message": "Utente non trovato"}), 404
    return jsonify(_format_user(row)), 200


@bp.post("/")
def create_user():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    cognome = (data.get("cognome") or "").strip()
    email = (data.get("email") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    password = (data.get("password") or "").strip()
    ruolo = data.get("ruolo", "automobilista")

    if not nome or not cognome or not email or not password:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "nome, cognome, email e password sono obbligatori"
        }), 400

    from werkzeug.security import generate_password_hash
    pwd_hash = generate_password_hash(password)

    try:
        g.db.execute(
            "INSERT INTO Utente (nome, cognome, email, telefono, password_hash, ruolo) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (nome, cognome, email, telefono or None, pwd_hash, ruolo)
        )
        new_id = g.db.lastrowid
    except Exception as e:
        if "Duplicate entry" in str(e):
            return jsonify({"error": "BAD_REQUEST", "message": "Email già registrata"}), 400
        raise

    g.db.execute("SELECT * FROM Utente WHERE id = %s", (new_id,))
    return jsonify(_format_user(g.db.fetchone())), 201


@bp.put("/<int:user_id>")
def update_user(user_id):
    data = request.get_json(silent=True) or {}

    g.db.execute("SELECT * FROM Utente WHERE id = %s", (user_id,))
    if not g.db.fetchone():
        return jsonify({"error": "NOT_FOUND", "message": "Utente non trovato"}), 404

    fields = []
    values = []
    for col in ("nome", "cognome", "email", "telefono"):
        if col in data:
            fields.append(f"{col} = %s")
            values.append(data[col])

    if not fields:
        return jsonify({"error": "BAD_REQUEST", "message": "Nessun campo da aggiornare"}), 400

    values.append(user_id)
    g.db.execute(f"UPDATE Utente SET {', '.join(fields)} WHERE id = %s", tuple(values))

    g.db.execute("SELECT * FROM Utente WHERE id = %s", (user_id,))
    return jsonify(_format_user(g.db.fetchone())), 200


@bp.delete("/<int:user_id>")
def delete_user(user_id):
    g.db.execute("DELETE FROM Utente WHERE id = %s", (user_id,))
    if g.db.rowcount == 0:
        return jsonify({"error": "NOT_FOUND", "message": "Utente non trovato"}), 404
    return jsonify({"message": f"Utente {user_id} eliminato con successo"}), 200
