"""Blueprint sinistri — sostituisce il vecchio `dettagliointervento`.

Sorgente: MongoDB `Proto_Sinistro_SC`. Stato canonico letto da
`stato_sinistro` con fallback su `stato`, scritto sempre su
`stato_sinistro`. Vedi `dashboard.py` per la mappatura completa.
"""

from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError

from .dashboard import (
    SINISTRI_COLLECTION,
    _canonical_state,
    _format_sinistro,
    _mongo_error_response,
)
from ..services.mongo_service import MongoDBService

# Blueprint canonico per `/api/v1/sinistri`.
bp = Blueprint("sinistri", __name__)
# Alias legacy per `/api/dettaglioIntervento`.
legacy_bp = Blueprint("sinistri_legacy", __name__)


# (stato_corrente, azione) -> (nuovo_stato, messaggio)
_TRANSITIONS = {
    ("pending", "take_in_charge"): ("accepted", "Intervento preso in carico"),
    ("pending", "reject"):         ("rejected", "Intervento rifiutato"),
    ("accepted", "complete"):      ("handled",  "Intervento completato"),
    ("accepted", "reject"):        ("rejected", "Intervento rifiutato"),
    # Riprendibilità di una richiesta rifiutata:
    ("rejected", "take_in_charge"): ("accepted", "Intervento ripreso in carico"),
}


def _collection():
    return MongoDBService().get_db()[SINISTRI_COLLECTION]


def _find_by_request_id(col, request_id: str):
    """Cerca il sinistro per `numero_sinistro` e in fallback per `_id`."""
    doc = col.find_one({"numero_sinistro": request_id})
    if doc:
        return doc
    try:
        return col.find_one({"_id": ObjectId(request_id)})
    except (InvalidId, TypeError):
        return None


def _format_sinistro_detail(doc) -> dict:
    base = _format_sinistro(doc)
    base.update({
        "numero_sinistro": doc.get("numero_sinistro"),
        "targa": doc.get("targa"),
        "telaio": doc.get("telaio"),
        "modello_veicolo": doc.get("modello_veicolo"),
        "descrizione_danno": doc.get("descrizione_danno"),
        "data_sinistro": doc.get("data_sinistro"),
        "data_assegnazione": doc.get("data_assegnazione"),
        "priorita": doc.get("priorita"),
        "stato_sinistro": doc.get("stato_sinistro") or doc.get("stato"),
        "compagnia_assicurativa": doc.get("compagnia_assicurativa"),
        "note": doc.get("note"),
        "contatto_cliente": doc.get("contatto_cliente") or {},
        "officina_id": doc.get("officina_id"),
    })
    return base


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def get_detail(request_id):
    try:
        col = _collection()
        doc = _find_by_request_id(col, request_id)
        if not doc:
            return jsonify({"error": "NOT_FOUND",
                            "message": "Intervento non trovato"}), 404
        return jsonify({"data": _format_sinistro_detail(doc)}), 200
    except PyMongoError as e:
        return _mongo_error_response(e, f"/sinistri/{request_id}")


def _apply_action(request_id: str, action: str):
    try:
        col = _collection()
    except PyMongoError as e:
        return _mongo_error_response(e, f"/sinistri/{request_id}/{action}")

    request.get_json(silent=True)  # consuma eventuale body

    doc = _find_by_request_id(col, request_id)
    if not doc:
        return jsonify({"error": "NOT_FOUND",
                        "message": "Intervento non trovato"}), 404

    current_state = _canonical_state(doc)
    transition = _TRANSITIONS.get((current_state, action))
    if transition is None:
        return jsonify({
            "error": "INVALID_ACTION",
            "message": (
                f"Azione '{action}' non disponibile per intervento "
                f"in stato '{current_state}'"
            ),
        }), 409

    new_status, message = transition
    now_iso = datetime.utcnow().isoformat()
    update = {
        "stato_sinistro": new_status,
        "data_aggiornamento_stato": now_iso,
    }
    if new_status == "accepted" and not doc.get("data_assegnazione"):
        update["data_assegnazione"] = now_iso

    try:
        col.update_one({"_id": doc["_id"]}, {"$set": update})
    except PyMongoError as e:
        current_app.logger.error("Update sinistro %s fallito: %s", doc.get("_id"), e)
        return jsonify({"error": "INTERNAL_ERROR",
                        "message": "Aggiornamento fallito"}), 500

    doc.update(update)
    return jsonify({
        "message": message,
        "request_id": request_id,
        "new_status": new_status,
        "data": _format_sinistro_detail(doc),
    }), 200


def take_in_charge(request_id):
    return _apply_action(request_id, "take_in_charge")


def reject(request_id):
    return _apply_action(request_id, "reject")


def complete(request_id):
    return _apply_action(request_id, "complete")


# ---------------------------------------------------------------------------
# Route canoniche (italiane, kebab-case) su `bp` → /api/v1/sinistri
# ---------------------------------------------------------------------------

bp.add_url_rule("/<string:request_id>",                    "get_detail",     get_detail,     methods=["GET"])
bp.add_url_rule("/<string:request_id>/prendi-in-carico",   "take_in_charge", take_in_charge, methods=["POST"])
bp.add_url_rule("/<string:request_id>/rifiuta",            "reject",         reject,         methods=["POST"])
bp.add_url_rule("/<string:request_id>/completa",           "complete",       complete,       methods=["POST"])


# ---------------------------------------------------------------------------
# Alias legacy su `legacy_bp` → /api/dettaglioIntervento
# ---------------------------------------------------------------------------

legacy_bp.add_url_rule("/<string:request_id>",                 "get_detail_legacy",  get_detail,     methods=["GET"])
legacy_bp.add_url_rule("/<string:request_id>/take-in-charge",  "take_legacy",        take_in_charge, methods=["POST"])
legacy_bp.add_url_rule("/<string:request_id>/reject",          "reject_legacy",      reject,         methods=["POST"])
legacy_bp.add_url_rule("/<string:request_id>/complete",        "complete_legacy",    complete,       methods=["POST"])
