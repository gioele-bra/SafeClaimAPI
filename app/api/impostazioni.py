from flask import Blueprint, jsonify, request, g

bp = Blueprint("impostazioni", __name__)


def _get_officina_id():
    officina_id = request.args.get("officina_id", type=int)

    if not officina_id:
        return None, (
            jsonify({
                "error": "BAD_REQUEST",
                "message": "Parametro officina_id mancante o non valido"
            }),
            400
        )

    return officina_id, None


def _get_officina(officina_id):
    g.db.execute("""
        SELECT id, ragione_sociale, email, telefono, indirizzo
        FROM Officina
        WHERE id = %s
    """, (officina_id,))
    return g.db.fetchone()


@bp.get("/")
def get_impostazioni():
    try:
        officina_id, error_response = _get_officina_id()
        if error_response:
            return error_response

        row = _get_officina(officina_id)

        if not row:
            return jsonify({
                "error": "NOT_FOUND",
                "message": f"Officina con ID {officina_id} non trovata"
            }), 404

        officina = dict(row)

        return jsonify({
            "status": "success",
            "data": {
                "profilo": {
                    "nome": officina.get("ragione_sociale"),
                    "email_contatto": officina.get("email"),
                    "telefono_contatto": officina.get("telefono"),
                    "avatar_url": None
                },
                "officina": {
                    "id": officina.get("id"),
                    "email": officina.get("email"),
                    "telefono": officina.get("telefono"),
                    "indirizzo": officina.get("indirizzo")
                },
                "notifiche": {
                    "push": None,
                    "email": None,
                    "sms": None
                },
                "parametri_operativi": {
                    "orario_inizio": None,
                    "orario_fine": None,
                    "max_coda": None,
                    "accettazione_automatica": None
                }
            }
        }), 200

    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero delle impostazioni: {str(e)}"
        }), 500


@bp.patch("/profilo")
def update_profilo():
    try:
        officina_id, error_response = _get_officina_id()
        if error_response:
            return error_response

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Payload mancante"
            }), 400

        row = _get_officina(officina_id)
        if not row:
            return jsonify({
                "error": "NOT_FOUND",
                "message": f"Officina con ID {officina_id} non trovata"
            }), 404

        if "avatar_url" in data:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Il campo avatar_url non è supportato dal DB attuale"
            }), 400

        updates = []
        values = []

        if "nome" in data:
            updates.append("ragione_sociale = %s")
            values.append(data["nome"])

        if "email_contatto" in data:
            updates.append("email = %s")
            values.append(data["email_contatto"])

        if "telefono_contatto" in data:
            updates.append("telefono = %s")
            values.append(data["telefono_contatto"])

        if not updates:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Nessun campo valido da aggiornare"
            }), 400

        query = f"""
            UPDATE Officina
            SET {', '.join(updates)}
            WHERE id = %s
        """
        values.append(officina_id)
        g.db.execute(query, tuple(values))
        g.db.connection.commit()

        row = _get_officina(officina_id)
        officina = dict(row)

        return jsonify({
            "message": "Profilo aggiornato con successo",
            "data": {
                "id": officina.get("id"),
                "nome": officina.get("ragione_sociale"),
                "email_contatto": officina.get("email"),
                "telefono_contatto": officina.get("telefono"),
                "avatar_url": None
            }
        }), 200

    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore durante l'aggiornamento del profilo: {str(e)}"
        }), 500