from flask import Blueprint, jsonify, g
from datetime import date, timedelta
import re

bp = Blueprint("analytics", __name__)


def _table_exists(table_name):
    """Verifica se una tabella esiste nel database"""
    try:
        g.db.execute(
            "SELECT COUNT(*) AS count FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND LOWER(table_name) = LOWER(%s)",
            (table_name,),
        )
        row = g.db.fetchone()
        return row and row.get("count", 0) > 0
    except:
        return False

# ==========================================
# 📊 ENDPOINT: RICHIESTE TOTALI
# ==========================================
@bp.get("/total-requests")
def get_total_requests():
    """Ritorna il numero totale di richieste gestite"""
    try:
        g.db.execute("SELECT COUNT(*) AS count FROM Richiesta_Soccorso")
        row = g.db.fetchone()
        total = int(row["count"] or 0) if row else 0

        return jsonify({"total": total}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero delle richieste totali: {str(e)}"
        }), 500

# ==========================================
# ⏳ ENDPOINT: RICHIESTE IN ATTESA
# ==========================================
@bp.get("/pending")
def get_pending():
    """Ritorna il numero di richieste in attesa"""
    try:
        g.db.execute("SELECT COUNT(*) AS count FROM Richiesta_Soccorso WHERE status = %s", ("pending",))
        row = g.db.fetchone()
        pending = int(row["count"] or 0) if row else 0

        return jsonify({"pending": pending}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero delle richieste in attesa: {str(e)}"
        }), 500

# ==========================================
# 🚀 ENDPOINT: RICHIESTE IN CORSO
# ==========================================
@bp.get("/accepted")
def get_accepted():
    """Ritorna il numero di richieste in corso (accettate)"""
    try:
        g.db.execute("SELECT COUNT(*) AS count FROM Richiesta_Soccorso WHERE status = %s", ("accepted",))
        row = g.db.fetchone()
        accepted = int(row["count"] or 0) if row else 0

        return jsonify({"accepted": accepted}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero delle richieste in corso: {str(e)}"
        }), 500

# ==========================================
# ✅ ENDPOINT: RICHIESTE COMPLETATE
# ==========================================
@bp.get("/handled")
def get_handled():
    """Ritorna il numero di richieste completate"""
    try:
        g.db.execute("SELECT COUNT(*) AS count FROM Richiesta_Soccorso WHERE status = %s", ("handled",))
        row = g.db.fetchone()
        handled = int(row["count"] or 0) if row else 0

        return jsonify({"handled": handled}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero delle richieste completate: {str(e)}"
        }), 500

# ==========================================
# 📈 ENDPOINT: RICHIESTE ULTIMI N GIORNI
# ==========================================
@bp.get("/requests-last-days/<int:days>")
def get_requests_last_days(days):
    """Ritorna serie temporale del numero di richieste negli ultimi N giorni"""
    try:
        if days < 1 or days > 365:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Giorni deve essere tra 1 e 365"
            }), 400

        start_date = date.today() - timedelta(days=days - 1)
        g.db.execute(
            "SELECT DATE(data_richiesta) AS day, COUNT(*) AS count "
            "FROM Richiesta_Soccorso "
            "WHERE data_richiesta >= %s "
            "GROUP BY day "
            "ORDER BY day ASC",
            (start_date,),
        )
        rows = g.db.fetchall() or []

        counts_by_day = {
            row["day"].isoformat(): int(row["count"] or 0) for row in rows
        }

        data = [
            counts_by_day.get((start_date + timedelta(days=i)).isoformat(), 0)
            for i in range(days)
        ]

        return jsonify({"days": days, "data": data}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero dati ultimi giorni: {str(e)}"
        }), 500

# ==========================================
# 🚗 ENDPOINT: STATO FLOTTA
# ==========================================
@bp.get("/fleet-status")
def get_fleet_status():
    """Ritorna lo stato attuale della flotta"""
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
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero dello stato flotta: {str(e)}"
        }), 500

# ==========================================
# ⏱️ ENDPOINT: TEMPO MEDIO GESTIONE
# ==========================================
@bp.get("/average-handling-time")
def get_average_handling_time():
    """Ritorna il tempo medio di gestione di una richiesta (in minuti)"""
    try:
        g.db.execute(
            "SELECT AVG(TIMESTAMPDIFF(MINUTE, data_richiesta, orario_arrivo)) AS avg_minutes "
            "FROM Richiesta_Soccorso "
            "WHERE data_richiesta IS NOT NULL AND orario_arrivo IS NOT NULL"
        )
        row = g.db.fetchone()
        avg_minutes = float(row["avg_minutes"] or 0.0) if row else 0.0

        return jsonify({"average_minutes": avg_minutes}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero del tempo medio gestione: {str(e)}"
        }), 500

# ==========================================
# ⭐ ENDPOINT: VALUTAZIONE MEDIA
# ==========================================
@bp.get("/average-rating")
def get_average_rating():
    """Ritorna la valutazione media del servizio"""
    try:
        if not _table_exists("reviews"):
            return jsonify({
                "error": "NOT_IMPLEMENTED",
                "message": "Endpoint non trovato"
            }), 501

        g.db.execute("SELECT AVG(rating) AS avg_rating FROM reviews")
        row = g.db.fetchone()
        avg_rating = float(row["avg_rating"] or 0.0) if row else 0.0

        return jsonify({"average_rating": avg_rating}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero della valutazione media: {str(e)}"
        }), 500

# ==========================================
# 💬 ENDPOINT: RECENSIONI RECENTI
# ==========================================
@bp.get("/reviews")
def get_reviews():
    """Ritorna lista delle recensioni recenti degli utenti"""
    try:
        if not _table_exists("reviews"):
            return jsonify({
                "error": "NOT_IMPLEMENTED",
                "message": "Endpoint non trovato"
            }), 501

        g.db.execute(
            "SELECT id, author, rating, comment, date "
            "FROM reviews ORDER BY date DESC LIMIT 10"
        )
        rows = g.db.fetchall() or []

        reviews = []
        for row in rows:
            review = dict(row)
            if review.get("date") is not None:
                review["date"] = review["date"].isoformat()
            reviews.append(review)

        return jsonify({"reviews": reviews, "count": len(reviews)}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero delle recensioni: {str(e)}"
        }), 500

# ==========================================
# 🚦 ENDPOINT: TRAFFICO LIVE
# ==========================================
@bp.get("/traffic/<city>")
def get_traffic(city):
    """Ritorna segnalazioni traffico/incidenti per la città indicata"""
    try:
        # Validazione parametro city
        if not city or len(city) > 100:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Città non valida"
            }), 400

        # Validazione caratteri (solo lettere, numeri, spazi e accenti)
        if not re.match(r"^[a-zA-Z0-9\s\-àèìòùáéíóúäëïöü]+$", city):
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Città contiene caratteri non validi"
            }), 400

        if not _table_exists("traffic"):
            return jsonify({
                "error": "NOT_IMPLEMENTED",
                "message": "Endpoint non trovato"
            }), 501

        g.db.execute(
            "SELECT id, title, source, pubDate, link "
            "FROM traffic WHERE LOWER(city) = LOWER(%s) ORDER BY pubDate DESC LIMIT 20",
            (city,),
        )
        rows = g.db.fetchall() or []

        incidents = []
        for row in rows:
            incident = dict(row)
            if incident.get("pubDate") is not None:
                incident["pubDate"] = incident["pubDate"].isoformat()
            incidents.append(incident)

        return jsonify({"city": city.capitalize(), "incidents": incidents, "count": len(incidents)}), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero del traffico: {str(e)}"
        }), 500
