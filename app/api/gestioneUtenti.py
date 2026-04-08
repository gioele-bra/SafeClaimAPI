from flask import Blueprint, jsonify, request, g

bp = Blueprint("gestioneUtenti", __name__)

VALID_ROLES = {"admin", "automobilista", "perito", "officina", "assicuratore", "azienda"}


def _format_user(row):
    """Formatta una riga Utente per la risposta JSON."""
    user = dict(row)
    user.pop("password_hash", None)
    if isinstance(user.get("ruolo"), str):
        user["ruolo"] = user["ruolo"].split(",") if user["ruolo"] else []
    if user.get("data_registrazione"):
        user["data_registrazione"] = user["data_registrazione"].isoformat()
    return user


@bp.get("/utenti")
def get_utenti():
    """Restituisce lista utenti."""
    g.db.execute("SELECT * FROM Utente")
    rows = g.db.fetchall()
    return jsonify({"utenti": [_format_user(r) for r in rows]}), 200


@bp.get("/utenti/count")
def get_numero_utenti():
    """Restituisce numero totale utenti."""
    g.db.execute("SELECT COUNT(*) AS totale FROM Utente")
    totale = g.db.fetchone()["totale"]
    return jsonify({"totale_utenti": totale}), 200


@bp.get("/utenti/ruoli")
def get_ruoli_attivi():
    """Restituisce i ruoli effettivamente in uso nel sistema."""
    g.db.execute("SELECT ruolo FROM Utente")
    rows = g.db.fetchall()

    ruoli = set()
    for row in rows:
        if row["ruolo"]:
            for r in row["ruolo"].split(","):
                ruoli.add(r.strip().lower())

    return jsonify({"ruoli_attivi": sorted(ruoli)}), 200


@bp.get("/utenti/cerca")
def cerca_utenti():
    """Cerca utenti per nome, cognome o email."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "BAD_REQUEST", "message": "parametro 'q' obbligatorio"}), 400

    like = f"%{query}%"
    g.db.execute(
        "SELECT * FROM Utente WHERE nome LIKE %s OR cognome LIKE %s OR email LIKE %s",
        (like, like, like)
    )
    rows = g.db.fetchall()
    return jsonify({"utenti_trovati": [_format_user(r) for r in rows]}), 200


@bp.get("/utenti/<int:user_id>")
def get_singolo_utente(user_id):
    """Ottiene dettagli singolo utente."""
    g.db.execute("SELECT * FROM Utente WHERE id = %s", (user_id,))
    row = g.db.fetchone()
    if not row:
        return jsonify({"error": "UTENTE_NON_TROVATO"}), 404
    return jsonify(_format_user(row)), 200


@bp.put("/utenti/<int:user_id>")
def modifica_utente(user_id):
    """Modifica dati utente (nome, cognome, email, telefono)."""
    data = request.get_json(silent=True) or {}

    g.db.execute("SELECT id FROM Utente WHERE id = %s", (user_id,))
    if not g.db.fetchone():
        return jsonify({"error": "UTENTE_NON_TROVATO", "message": "Utente non trovato"}), 404

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
    return jsonify({"message": "Utente aggiornato", "utente": _format_user(g.db.fetchone())}), 200


@bp.delete("/utenti/<int:user_id>")
def elimina_utente(user_id):
    """Elimina un utente."""
    g.db.execute("DELETE FROM Utente WHERE id = %s", (user_id,))
    if g.db.rowcount == 0:
        return jsonify({"error": "UTENTE_NON_TROVATO", "message": "Utente non trovato"}), 404
    return jsonify({"message": f"Utente {user_id} eliminato con successo"}), 200
