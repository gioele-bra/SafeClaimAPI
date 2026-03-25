from copy import deepcopy


WORKSHOP_STATE = {
    "workshop_name": "Officina Centrale",
    "operativo_online": True,
    "tempo_medio_minuti": 14,
}

REQUESTS = [
    {
        "id": "SOS-2491",
        "vehicle_type": "Furgone",
        "vehicle_label": "Fiat Ducato (Furgone)",
        "cliente": "+39 333 1234567",
        "posizione": "Milano Centro",
        "lat": 45.4642,
        "lng": 9.1900,
        "status": "pending",
        "requested_at": "2026-03-25T08:30:00",
        "assigned_driver": None,
        "notes": "Veicolo fermo in carreggiata.",
    },
    {
        "id": "SOS-2492",
        "vehicle_type": "SUV",
        "vehicle_label": "BMW X3 (SUV)",
        "cliente": "+39 338 9876543",
        "posizione": "Rho Fiera",
        "lat": 45.5184,
        "lng": 9.0519,
        "status": "accepted",
        "requested_at": "2026-03-25T08:15:00",
        "assigned_driver": "Mario Rossi",
        "notes": "Cliente in attesa nel parcheggio principale.",
    },
    {
        "id": "SOS-2488",
        "vehicle_type": "City Car",
        "vehicle_label": "Smart ForTwo (City Car)",
        "cliente": "+39 339 0000000",
        "posizione": "Linate",
        "lat": 45.4610,
        "lng": 9.2782,
        "status": "handled",
        "requested_at": "2026-03-25T06:45:00",
        "assigned_driver": "Luca Bianchi",
        "notes": "Intervento completato, veicolo consegnato in officina.",
    },
]

STATUS_TEXT = {
    "pending": "In Attesa",
    "accepted": "In Corso",
    "handled": "Completato",
    "rejected": "Rifiutato",
}

AVAILABLE_ACTIONS = {
    "pending": ["take_in_charge", "reject"],
    "accepted": ["complete", "reject"],
    "handled": [],
    "rejected": [],
}

DASHBOARD_VISIBLE_STATUSES = {"pending", "accepted", "handled"}


def _copy_request(request_item):
    data = deepcopy(request_item)
    status = data["status"]
    data["status_text"] = STATUS_TEXT.get(status, status.upper())
    data["available_actions"] = AVAILABLE_ACTIONS.get(status, [])
    return data


def list_dashboard_requests():
    visible = [
        _copy_request(item)
        for item in REQUESTS
        if item["status"] in DASHBOARD_VISIBLE_STATUSES
    ]
    order = {"pending": 0, "accepted": 1, "handled": 2}
    visible.sort(key=lambda item: (order.get(item["status"], 99), item["id"]))
    return visible


def get_request_or_none(request_id):
    for item in REQUESTS:
        if item["id"] == request_id:
            return item
    return None


def get_request_detail(request_id):
    item = get_request_or_none(request_id)
    if not item:
        return None
    return _copy_request(item)


def get_dashboard_summary():
    requests = list_dashboard_requests()
    active_count = sum(1 for item in requests if item["status"] in {"pending", "accepted"})
    completed_today = sum(1 for item in REQUESTS if item["status"] == "handled")
    return {
        "workshop_name": WORKSHOP_STATE["workshop_name"],
        "operativo_online": WORKSHOP_STATE["operativo_online"],
        "kpi": {
            "richieste_attive": active_count,
            "completati_oggi": completed_today,
            "tempo_medio_minuti": WORKSHOP_STATE["tempo_medio_minuti"],
        },
        "selected_request_id": requests[0]["id"] if requests else None,
    }


def update_operational_status(is_online):
    WORKSHOP_STATE["operativo_online"] = is_online
    return get_dashboard_summary()


def transition_request(request_id, action):
    item = get_request_or_none(request_id)
    if not item:
        return None, ("NOT_FOUND", "Richiesta non trovata", 404)

    current_status = item["status"]
    transitions = {
        "take_in_charge": {
            "from": {"pending"},
            "to": "accepted",
            "message": "Richiesta presa in carico",
        },
        "reject": {
            "from": {"pending", "accepted"},
            "to": "rejected",
            "message": "Richiesta rifiutata",
        },
        "complete": {
            "from": {"accepted"},
            "to": "handled",
            "message": "Intervento completato",
        },
    }

    transition = transitions.get(action)
    if not transition:
        return None, ("BAD_REQUEST", "Azione non supportata", 400)

    if current_status not in transition["from"]:
        return None, (
            "BAD_REQUEST",
            f"Azione '{action}' non consentita per stato '{current_status}'",
            400,
        )

    item["status"] = transition["to"]
    if action == "take_in_charge" and not item.get("assigned_driver"):
        item["assigned_driver"] = "Mario Rossi"

    return {
        "message": transition["message"],
        "request_id": item["id"],
        "new_status": item["status"],
        "data": _copy_request(item),
    }, None
