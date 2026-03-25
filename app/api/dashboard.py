from flask import Blueprint, jsonify, request

from .mock_interventi_store import get_dashboard_summary, list_dashboard_requests, update_operational_status

bp = Blueprint("dashboard", __name__)


@bp.get("/summary")
def get_summary():
    return jsonify(get_dashboard_summary()), 200


@bp.get("/requests")
def get_requests():
    requests_data = list_dashboard_requests()
    return jsonify({
        "count": len(requests_data),
        "data": requests_data,
    }), 200


@bp.patch("/operational-status")
def patch_operational_status():
    payload = request.get_json(silent=True) or {}
    operativo_online = payload.get("operativo_online")

    if not isinstance(operativo_online, bool):
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Il campo 'operativo_online' deve essere booleano",
        }), 400

    summary = update_operational_status(operativo_online)
    return jsonify({
        "message": "Stato operativo aggiornato",
        **summary,
    }), 200
