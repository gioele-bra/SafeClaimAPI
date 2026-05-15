"""Endpoint dashboard del soccorritore, alimentati da MongoDB.

Sorgente dati: collection `Proto_Sinistro_SC` (sinistri attivi/storici).
Lo stato canonico è `stato_sinistro`; in lettura fallback su `stato`.
Toggle `operativo_online` persistito in `Proto_Impostazioni_Soccorso_SC`
(stessa collection usata da `/api/impostazioni/parametri-operativi`).
"""

from datetime import date, datetime, time, timedelta

from flask import Blueprint, current_app, jsonify, request
from pymongo.errors import PyMongoError

from ..services.mongo_service import MongoDBService

bp = Blueprint("dashboard", __name__)

SINISTRI_COLLECTION = "Proto_Sinistro_SC"
SETTINGS_COLLECTION = "Proto_Impostazioni_Soccorso_SC"
SETTINGS_KEY = "soccorso"

# Stati canonici lato dashboard (allineati a quelli del mock precedente).
_STATUS_TEXT = {
    "pending": "In attesa di presa in carico",
    "accepted": "Intervento assegnato",
    "handled": "Intervento completato",
    "rejected": "Intervento rifiutato",
}

_AVAILABLE_ACTIONS = {
    "pending": ["take_in_charge", "reject"],
    "accepted": ["complete", "reject"],
    "rejected": ["take_in_charge"],  # riprendibile dopo un rifiuto
    "handled": [],
}

# Mapping dei valori raw del DB (inglese + italiano) verso i 4 stati canonici.
# Tutto ciò che non è in questa mappa è "other" e non concorre alle azioni.
_CANONICAL_TO_RAW = {
    "pending": [
        "pending", "nuovo", "creato",
        "da_assegnare", "da_gestire", "da_accettare",
    ],
    "accepted": [
        "accepted", "accettato", "assegnato", "approvato",
        "in_corso", "in_carico", "in_lavorazione",
    ],
    "handled": [
        "handled", "completato", "fatto", "chiuso",
    ],
    "rejected": [
        "rejected", "rifiutato", "annullato",
    ],
}
_STATE_ALIASES = {
    raw: canonical
    for canonical, raws in _CANONICAL_TO_RAW.items()
    for raw in raws
}

# Insiemi precalcolati riusati nelle query Mongo $in.
_ACTIVE_RAW = (
    _CANONICAL_TO_RAW["pending"] + _CANONICAL_TO_RAW["accepted"]
)
_HANDLED_RAW = _CANONICAL_TO_RAW["handled"]
_QUEUE_RAW = _ACTIVE_RAW + _CANONICAL_TO_RAW["rejected"]


def _db():
    return MongoDBService().get_db()


def _sinistri():
    return _db()[SINISTRI_COLLECTION]


def _canonical_state(doc) -> str:
    raw = doc.get("stato_sinistro") or doc.get("stato") or "pending"
    raw = str(raw).strip().lower()
    return _STATE_ALIASES.get(raw, raw)


def _format_sinistro(doc) -> dict:
    posizione = doc.get("posizione_soccorso") or {}
    coords = posizione.get("coordinates") or [0.0, 0.0]
    try:
        lng = float(coords[0]) if len(coords) > 0 else 0.0
        lat = float(coords[1]) if len(coords) > 1 else 0.0
    except (TypeError, ValueError):
        lng, lat = 0.0, 0.0

    status = _canonical_state(doc)
    return {
        "id": doc.get("numero_sinistro") or str(doc.get("_id")),
        "vehicle_type": doc.get("modello_veicolo") or "",
        "vehicle_label": _vehicle_label(doc),
        "cliente": doc.get("cliente") or "",
        "posizione": doc.get("descrizione_danno") or "Posizione segnalata",
        "lat": lat,
        "lng": lng,
        "status": status,
        "status_text": _STATUS_TEXT.get(status, status),
        "available_actions": list(_AVAILABLE_ACTIONS.get(status, [])),
    }


def _vehicle_label(doc) -> str:
    parts = []
    if doc.get("modello_veicolo"):
        parts.append(str(doc["modello_veicolo"]))
    if doc.get("targa"):
        parts.append(f"({doc['targa']})")
    return " ".join(parts) if parts else "Veicolo"


def _parse_iso(value):
    """Accetta sia stringhe ISO che datetime BSON nativi."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _avg_assignment_minutes(col) -> int:
    """Tempo medio di assegnazione = data_assegnazione − data_sinistro (minuti)."""
    cursor = col.find(
        {"data_assegnazione": {"$ne": None}, "data_sinistro": {"$ne": None}},
        {"data_sinistro": 1, "data_assegnazione": 1},
    )
    deltas = []
    for doc in cursor:
        start = _parse_iso(doc.get("data_sinistro"))
        end = _parse_iso(doc.get("data_assegnazione"))
        if start and end and end >= start:
            deltas.append((end - start).total_seconds() / 60.0)
    if not deltas:
        return 0
    return int(sum(deltas) / len(deltas))


# ---------------------------------------------------------------------------
# Operativo online — letto/scritto sulla collection impostazioni soccorso.
# ---------------------------------------------------------------------------


def _get_operativo_online() -> bool:
    try:
        doc = _db()[SETTINGS_COLLECTION].find_one({"chiave": SETTINGS_KEY}) or {}
        value = (doc.get("parametri_operativi") or {}).get("operativo_online")
        return bool(value) if value is not None else False
    except PyMongoError as e:
        current_app.logger.warning("Lettura operativo_online fallita: %s", e)
        return False


def _set_operativo_online(value: bool) -> None:
    _db()[SETTINGS_COLLECTION].update_one(
        {"chiave": SETTINGS_KEY},
        {
            "$set": {
                "parametri_operativi.operativo_online": value,
                "updated_at": datetime.utcnow().isoformat(),
            },
            "$setOnInsert": {"chiave": SETTINGS_KEY, "ambito": "soccorso"},
        },
        upsert=True,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.get("/summary")
def get_summary():
    try:
        col = _sinistri()
    except Exception as e:
        current_app.logger.error("Mongo non disponibile per /dashboard/summary: %s", e)
        return jsonify({"error": "INTERNAL_ERROR", "message": "Database non disponibile"}), 500

    today_start = datetime.combine(date.today(), time.min)
    today_end = datetime.combine(date.today(), time.max)
    today_start_iso = today_start.isoformat()
    today_end_iso = today_end.isoformat()

    active_filter = {
        "attivo": True,
        "$or": [
            {"stato_sinistro": {"$in": _ACTIVE_RAW}},
            {"stato": {"$in": _ACTIVE_RAW}},
        ],
    }
    richieste_attive = col.count_documents(active_filter)

    completati_oggi = col.count_documents({
        "$or": [
            {"stato_sinistro": {"$in": _HANDLED_RAW}},
            {"stato": {"$in": _HANDLED_RAW}},
        ],
        "data_assegnazione": {"$gte": today_start_iso, "$lte": today_end_iso},
    })

    tempo_medio = _avg_assignment_minutes(col)

    # Prima richiesta attiva per centrare la mappa.
    first_active = col.find_one(active_filter, sort=[("data_sinistro", 1)])
    selected_request_id = None
    if first_active:
        selected_request_id = first_active.get("numero_sinistro") or str(first_active.get("_id"))

    return jsonify({"data": {
        "workshop_name": "Centrale Soccorso",
        "operativo_online": _get_operativo_online(),
        "kpi": {
            "richieste_attive": richieste_attive,
            "completati_oggi": completati_oggi,
            "tempo_medio_minuti": tempo_medio,
        },
        "selected_request_id": selected_request_id,
    }}), 200


@bp.get("/requests")
def get_requests():
    try:
        col = _sinistri()
    except Exception as e:
        current_app.logger.error("Mongo non disponibile per /dashboard/requests: %s", e)
        return jsonify({"error": "INTERNAL_ERROR", "message": "Database non disponibile"}), 500

    cursor = col.find({
        "attivo": True,
        "$or": [
            {"stato_sinistro": {"$in": _QUEUE_RAW}},
            {"stato": {"$in": _QUEUE_RAW}},
        ],
    }).sort([("priorita", 1), ("data_sinistro", 1)])

    data = [_format_sinistro(doc) for doc in cursor]
    return jsonify({"count": len(data), "data": data}), 200


@bp.patch("/operational-status")
def patch_operational_status():
    payload = request.get_json(silent=True) or {}
    operativo_online = payload.get("operativo_online")

    if not isinstance(operativo_online, bool):
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "Il campo 'operativo_online' deve essere booleano",
        }), 400

    try:
        _set_operativo_online(operativo_online)
    except PyMongoError as e:
        current_app.logger.error("Persist operativo_online fallito: %s", e)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "Impossibile salvare lo stato operativo",
        }), 500

    # Ritorna la summary aggiornata per coerenza con il vecchio contratto.
    return get_summary()
