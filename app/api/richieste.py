from flask import Blueprint, jsonify, request, g

bp = Blueprint("richieste", __name__)

VALID_STATUSES = {"in_attesa", "assegnata", "in_corso", "completata", "annullata"}


@bp.get("/")
def get_requests():
    status_filter = request.args.get("status")

    if status_filter and status_filter != "tutte":
        if status_filter not in VALID_STATUSES:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": f"Stato '{status_filter}' non valido. "
                           f"Valori ammessi: {', '.join(sorted(VALID_STATUSES))}"
            }), 400

        g.db.execute(
            "SELECT * FROM Richiesta_Soccorso WHERE stato = %s ORDER BY data_richiesta DESC",
            (status_filter,)
        )
    else:
        g.db.execute("SELECT * FROM Richiesta_Soccorso ORDER BY data_richiesta DESC")

    rows = g.db.fetchall()

    data = []
    for row in rows:
        r = dict(row)
        if r.get("data_richiesta"):
            r["data_richiesta"] = r["data_richiesta"].isoformat()
        if r.get("orario_arrivo"):
            r["orario_arrivo"] = r["orario_arrivo"].isoformat()
        data.append(r)

    return jsonify({"success": True, "count": len(data), "data": data}), 200


@bp.get("/<int:richiesta_id>")
def get_single_request(richiesta_id):
    g.db.execute("SELECT * FROM Richiesta_Soccorso WHERE id = %s", (richiesta_id,))
    row = g.db.fetchone()
    if not row:
        return jsonify({"error": "NOT_FOUND", "message": "Richiesta non trovata"}), 404

    r = dict(row)
    if r.get("data_richiesta"):
        r["data_richiesta"] = r["data_richiesta"].isoformat()
    if r.get("orario_arrivo"):
        r["orario_arrivo"] = r["orario_arrivo"].isoformat()

    return jsonify(r), 200
