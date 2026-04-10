from copy import deepcopy

from flask import Blueprint, jsonify, request

try:
    from .mock_interventi_store import (
        get_dashboard_summary,
        list_dashboard_requests,
        update_operational_status,
    )
except ImportError:
    _operativo_online = True
    _dashboard_requests = [
        {
            "id": "SOS-2491",
            "vehicle_type": "Furgone",
            "vehicle_label": "Fiat Ducato",
            "cliente": "Mario Rossi",
            "posizione": "Milano Centrale",
            "lat": 45.4841,
            "lng": 9.2043,
            "status": "pending",
            "status_text": "In attesa di presa in carico",
            "available_actions": ["take_in_charge", "reject"],
        },
        {
            "id": "SOS-2492",
            "vehicle_type": "SUV",
            "vehicle_label": "BMW X3",
            "cliente": "Anna Bianchi",
            "posizione": "Navigli",
            "lat": 45.4517,
            "lng": 9.1765,
            "status": "accepted",
            "status_text": "Intervento assegnato",
            "available_actions": ["complete", "reject"],
        },
        {
            "id": "SOS-2488",
            "vehicle_type": "City Car",
            "vehicle_label": "Smart ForTwo",
            "cliente": "Luca Verdi",
            "posizione": "Porta Romana",
            "lat": 45.4522,
            "lng": 9.2021,
            "status": "handled",
            "status_text": "Intervento completato",
            "available_actions": [],
        },
    ]

    def get_dashboard_summary():
        active_requests = [
            item
            for item in _dashboard_requests
            if item["status"] in {"pending", "accepted"}
        ]
        selected_request_id = active_requests[0]["id"] if active_requests else None

        return {
            "workshop_name": "Officina Centrale",
            "operativo_online": _operativo_online,
            "kpi": {
                "richieste_attive": len(active_requests),
                "completati_oggi": sum(
                    1 for item in _dashboard_requests if item["status"] == "handled"
                ),
                "tempo_medio_minuti": 34,
            },
            "selected_request_id": selected_request_id,
        }

    def list_dashboard_requests():
        return deepcopy(_dashboard_requests)

    def update_operational_status(operativo_online):
        global _operativo_online
        _operativo_online = operativo_online
        return get_dashboard_summary()


bp = Blueprint("dashboard", __name__)


@bp.get("/summary")
def get_summary():
    summary = get_dashboard_summary()
    return jsonify({"data": summary}), 200


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
        "data": summary,
    }), 200
