from flask import Blueprint, jsonify, request, g

bp = Blueprint("soccorsi", __name__)


@bp.get("/")
def get_soccorsi():
    """Lista richieste di soccorso."""
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

    return jsonify({"count": len(data), "data": data}), 200


@bp.get("/<int:soccorso_id>")
def get_soccorso(soccorso_id):
    """Dettaglio singola richiesta di soccorso."""
    g.db.execute("SELECT * FROM Richiesta_Soccorso WHERE id = %s", (soccorso_id,))
    row = g.db.fetchone()
    if not row:
        return jsonify({"error": "NOT_FOUND", "message": "Richiesta non trovata"}), 404

    r = dict(row)
    if r.get("data_richiesta"):
        r["data_richiesta"] = r["data_richiesta"].isoformat()
    if r.get("orario_arrivo"):
        r["orario_arrivo"] = r["orario_arrivo"].isoformat()

    return jsonify(r), 200
