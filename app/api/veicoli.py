"""Blueprint veicoli — sostituisce il vecchio `flotta`.

Lettura/azioni sulla tabella MySQL `Veicoli`.
"""

import uuid

from flask import Blueprint, current_app, g, jsonify, request

# Blueprint canonico per `/api/v1/veicoli`.
bp = Blueprint("veicoli", __name__)
# Alias legacy per `/api/flotta`.
legacy_bp = Blueprint("veicoli_legacy", __name__)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def list_veicoli():
    try:
        g.db.execute("SELECT * FROM Veicoli ORDER BY name ASC")
        rows = g.db.fetchall() or []
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        current_app.logger.error("Errore lettura veicoli: %s", e)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": f"Errore nel recupero dei veicoli: {e}",
        }), 500


def get_veicolo(vehicle_id):
    try:
        g.db.execute("SELECT * FROM Veicoli WHERE id = %s", (vehicle_id,))
        row = g.db.fetchone()
        if not row:
            return jsonify({
                "error": "NOT_FOUND",
                "message": f"Veicolo con ID {vehicle_id} non trovato",
            }), 404
        return jsonify(dict(row)), 200
    except Exception as e:
        current_app.logger.error("Errore lettura veicolo %s: %s", vehicle_id, e)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "Errore durante la ricerca del veicolo",
        }), 500


def contact_driver():
    """POST /api/v1/veicoli/contatto-autista — mock di chiamata autista."""
    try:
        data = request.get_json(silent=True) or {}
        if "driver" not in data:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Dati mancanti: specificare il nome dell'autista",
            }), 400

        driver_name = data["driver"]
        return jsonify({
            "status": "success",
            "message": f"Chiamata a {driver_name} inoltrata correttamente",
            "timestamp": uuid.uuid4().hex,
        }), 200
    except Exception as e:
        current_app.logger.error("Errore contact_driver: %s", e)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "Errore durante l'invio della chiamata",
        }), 500


# ---------------------------------------------------------------------------
# Route canoniche su `bp` → /api/v1/veicoli
# ---------------------------------------------------------------------------

bp.add_url_rule("",                "list_veicoli_no_slash", list_veicoli,   methods=["GET"])
bp.add_url_rule("/",               "list_veicoli",          list_veicoli,   methods=["GET"])
bp.add_url_rule("/<int:vehicle_id>", "get_veicolo",         get_veicolo,    methods=["GET"])
bp.add_url_rule("/contatto-autista", "contact_driver",      contact_driver, methods=["POST"])


# ---------------------------------------------------------------------------
# Alias legacy su `legacy_bp` → /api/flotta
# ---------------------------------------------------------------------------

legacy_bp.add_url_rule("",                  "list_legacy_no_slash", list_veicoli,   methods=["GET"])
legacy_bp.add_url_rule("/",                 "list_legacy",          list_veicoli,   methods=["GET"])
legacy_bp.add_url_rule("/<int:vehicle_id>", "get_legacy",           get_veicolo,    methods=["GET"])
legacy_bp.add_url_rule("/contact",          "contact_legacy",       contact_driver, methods=["POST"])
