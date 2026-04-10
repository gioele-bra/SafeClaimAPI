from copy import deepcopy


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
        "requested_at": "2026-04-10T08:45:00",
        "assigned_driver": None,
        "notes": "Veicolo fermo per guasto elettrico. Cliente in attesa sul posto.",
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
        "requested_at": "2026-04-10T09:10:00",
        "assigned_driver": "Officina Centrale",
        "notes": "Richiesto traino verso officina convenzionata.",
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
        "requested_at": "2026-04-10T07:25:00",
        "assigned_driver": "Officina Centrale",
        "notes": "Intervento concluso con successo.",
        "available_actions": [],
    },
]


_STATUS_CONFIG = {
    "pending": {
        "status_text": "In attesa di presa in carico",
        "available_actions": ["take_in_charge", "reject"],
    },
    "accepted": {
        "status_text": "Intervento assegnato",
        "available_actions": ["complete", "reject"],
    },
    "handled": {
        "status_text": "Intervento completato",
        "available_actions": [],
    },
    "rejected": {
        "status_text": "Intervento rifiutato",
        "available_actions": [],
    },
}

_ACTION_TRANSITIONS = {
    ("pending", "take_in_charge"): {
        "new_status": "accepted",
        "message": "Intervento preso in carico con successo",
        "assigned_driver": "Officina Centrale",
    },
    ("pending", "reject"): {
        "new_status": "rejected",
        "message": "Intervento rifiutato con successo",
        "assigned_driver": None,
    },
    ("accepted", "complete"): {
        "new_status": "handled",
        "message": "Intervento completato con successo",
        "assigned_driver": "Officina Centrale",
    },
    ("accepted", "reject"): {
        "new_status": "rejected",
        "message": "Intervento rifiutato con successo",
        "assigned_driver": None,
    },
}


def _clone_request(item):
    return deepcopy(item)


def _get_request_by_id(request_id):
    for item in _dashboard_requests:
        if item["id"] == request_id:
            return item
    return None


def _apply_status(request_item, new_status):
    config = _STATUS_CONFIG[new_status]
    request_item["status"] = new_status
    request_item["status_text"] = config["status_text"]
    request_item["available_actions"] = list(config["available_actions"])


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
    return [_clone_request(item) for item in _dashboard_requests]


def update_operational_status(operativo_online):
    global _operativo_online
    _operativo_online = operativo_online
    return get_dashboard_summary()


def get_intervento_detail(request_id):
    request_item = _get_request_by_id(request_id)
    if request_item is None:
        return None
    return _clone_request(request_item)


def apply_intervento_action(request_id, action):
    request_item = _get_request_by_id(request_id)
    if request_item is None:
        return None, {
            "status_code": 404,
            "error": "NOT_FOUND",
            "message": "Intervento non trovato",
        }

    transition = _ACTION_TRANSITIONS.get((request_item["status"], action))
    if transition is None:
        return None, {
            "status_code": 409,
            "error": "INVALID_ACTION",
            "message": (
                f"Azione '{action}' non disponibile per intervento "
                f"in stato '{request_item['status']}'"
            ),
        }

    request_item["assigned_driver"] = transition["assigned_driver"]
    _apply_status(request_item, transition["new_status"])

    return {
        "message": transition["message"],
        "request_id": request_item["id"],
        "new_status": request_item["status"],
        "data": _clone_request(request_item),
    }, None
