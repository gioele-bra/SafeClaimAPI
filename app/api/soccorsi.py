"""Lista richieste di soccorso (MySQL `Richiesta_Soccorso`).

Letto dal client Soccorso (pagina Richieste) tramite `RichiesteApiService`.
La rotta singola `/api/soccorsi/<id>` è stata rimossa perché nessun
client la chiamava.
"""

from flask import Blueprint, g, jsonify

bp = Blueprint("soccorsi", __name__)


def list_soccorsi():
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


bp.add_url_rule("",  "list_soccorsi_no_slash", list_soccorsi, methods=["GET"])
bp.add_url_rule("/", "list_soccorsi",          list_soccorsi, methods=["GET"])
