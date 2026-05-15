from flask import Blueprint, jsonify, request, g

bp = Blueprint("gestioneUtenti", __name__)

VALID_ROLES = {"admin", "automobilista", "perito", "officina", "soccorso", "assicuratore", "azienda"}


def _format_user(row):
    user = dict(row)
    user.pop("password_hash", None)
    ruolo = user.get("ruolo")
    if isinstance(ruolo, set):
        user["ruolo"] = list(ruolo)
    elif isinstance(ruolo, str):
        user["ruolo"] = ruolo.split(",") if ruolo else []
    else:
        user["ruolo"] = []
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
            # Gestione sicura se è stringa o set
            val = row["ruolo"]
            if isinstance(val, str):
                for r in val.split(","):
                    ruoli.add(r.strip().lower())
            elif isinstance(val, (set, list)):
                for r in val:
                    ruoli.add(str(r).strip().lower())

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


@bp.post("/utenti/<int:user_id>/ruoli")
def update_user_roles(user_id):
    """Aggiorna i ruoli di un utente."""
    data = request.get_json(silent=True) or {}
    
    # Verifica che l'utente esista
    g.db.execute("SELECT id FROM Utente WHERE id = %s", (user_id,))
    if not g.db.fetchone():
        return jsonify({"error": "UTENTE_NON_TROVATO", "message": "Utente non trovato"}), 404
    
    # Estrai i ruoli dal body
    roles_raw = data.get("ruoli", [])
    
    # Normalizza i ruoli (può essere lista o stringa)
    if isinstance(roles_raw, str):
        roles_input = [r.strip().lower() for r in roles_raw.split(",") if r.strip()]
    elif isinstance(roles_raw, list):
        roles_input = [str(r).strip().lower() for r in roles_raw if r]
    else:
        roles_input = []
    
    # Valida i ruoli
    invalid = [r for r in roles_input if r not in VALID_ROLES]
    if invalid:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": f"Ruoli non riconosciuti: {', '.join(invalid)}. Ruoli ammessi: {', '.join(sorted(VALID_ROLES))}"
        }), 400
    
    # Se non ci sono ruoli validi, ritorna errore
    if not roles_input:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Almeno un ruolo valido è obbligatorio"
        }), 400
    
    # Salva i ruoli come stringa separata da virgola
    ruoli_str = ",".join(roles_input)
    
    # Aggiorna il database
    g.db.execute("UPDATE Utente SET ruolo = %s WHERE id = %s", (ruoli_str, user_id))
    
    # Ritorna l'utente aggiornato
    g.db.execute("SELECT * FROM Utente WHERE id = %s", (user_id,))
    user = g.db.fetchone()
    
    return jsonify({
        "message": "Ruoli aggiornati con successo",
        "utente": _format_user(user)
    }), 200


@bp.delete("/utenti/<int:user_id>")
def elimina_utente(user_id):
    """Elimina un utente."""
    g.db.execute("DELETE FROM Utente WHERE id = %s", (user_id,))
    if g.db.rowcount == 0:
        return jsonify({"error": "UTENTE_NON_TROVATO", "message": "Utente non trovato"}), 404
    return jsonify({"message": f"Utente {user_id} eliminato con successo"}), 200