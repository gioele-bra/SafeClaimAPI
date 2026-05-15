"""Analytics dei soccorsi: aggregate su MongoDB `Proto_Sinistro_SC`.

Stato canonico letto da `stato_sinistro` con fallback su `stato`.
"""

from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, g, jsonify
from pymongo.errors import PyMongoError

from .dashboard import SINISTRI_COLLECTION, _STATE_ALIASES
from ..services.mongo_service import MongoDBService

bp = Blueprint("analytics", __name__)


# Riusa la mappatura centralizzata in dashboard.py (single source of truth).
_BUCKETS = _STATE_ALIASES


def _sinistri():
    return MongoDBService().get_db()[SINISTRI_COLLECTION]


def _parse_iso(value):
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


def _bucketize(raw_state) -> str:
    return _BUCKETS.get(str(raw_state or "").strip().lower(), "other")


@bp.get("/summary")
def get_analytics_summary():
    """Conteggi totali + tempo medio di assegnazione (minuti)."""
    try:
        col = _sinistri()
    except Exception as e:
        current_app.logger.error("Mongo non disponibile per /analytics/summary: %s", e)
        return jsonify({"error": "INTERNAL_ERROR", "message": "Database non disponibile"}), 500

    buckets = {"pending": 0, "accepted": 0, "handled": 0, "rejected": 0, "other": 0}

    cursor = col.find({}, {"stato_sinistro": 1, "stato": 1,
                            "data_sinistro": 1, "data_assegnazione": 1})

    deltas_minutes = []
    total = 0
    for doc in cursor:
        total += 1
        state = doc.get("stato_sinistro") or doc.get("stato")
        buckets[_bucketize(state)] += 1

        start = _parse_iso(doc.get("data_sinistro"))
        end = _parse_iso(doc.get("data_assegnazione"))
        if start and end and end >= start:
            deltas_minutes.append((end - start).total_seconds() / 60.0)

    avg_minutes = int(sum(deltas_minutes) / len(deltas_minutes)) if deltas_minutes else 0

    return jsonify({
        "total": total,
        "pending": buckets["pending"],
        "accepted": buckets["accepted"],
        "handled": buckets["handled"],
        "rejected": buckets["rejected"],
        "average_handling_minutes": avg_minutes,
    }), 200


@bp.get("/last-days/<int:days>")
def get_last_days(days):
    """Serie temporale: numero sinistri per giorno, ultimi N giorni."""
    if days < 1 or days > 365:
        return jsonify({"error": "BAD_REQUEST", "message": "days deve essere 1..365"}), 400

    try:
        col = _sinistri()
    except Exception as e:
        current_app.logger.error("Mongo non disponibile per /analytics/last-days: %s", e)
        return jsonify({"error": "INTERNAL_ERROR", "message": "Database non disponibile"}), 500

    start_day = date.today() - timedelta(days=days - 1)
    start_iso = start_day.isoformat()

    counts = {}
    cursor = col.find(
        {"data_sinistro": {"$gte": start_iso}},
        {"data_sinistro": 1},
    )
    for doc in cursor:
        dt = _parse_iso(doc.get("data_sinistro"))
        if not dt:
            continue
        day = dt.date().isoformat()
        counts[day] = counts.get(day, 0) + 1

    series = [
        counts.get((start_day + timedelta(days=i)).isoformat(), 0)
        for i in range(days)
    ]
    return jsonify({"days": days, "data": series}), 200


@bp.get("/fleet-status")
def get_fleet_status():
    """Stato attuale della flotta letto da MySQL `Veicoli`."""
    try:
        g.db.execute("SELECT status, COUNT(*) AS count FROM Veicoli GROUP BY status")
        rows = g.db.fetchall() or []

        status_map = {"available": 0, "busy": 0, "maintenance": 0}
        for row in rows:
            status = (row.get("status") or "").lower()
            if status in status_map:
                status_map[status] = int(row["count"] or 0)

        return jsonify(status_map), 200
    except Exception as e:
        current_app.logger.error("Errore lettura stato flotta: %s", e)
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": "Errore nel recupero dello stato flotta",
        }), 500
