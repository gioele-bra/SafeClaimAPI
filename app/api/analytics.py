from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import uuid

bp = Blueprint("analytics", __name__)

# ==========================================
# MOCK DATABASE - DATI ANALYTICS
# ==========================================

MOCK_REQUESTS_DATA = {
    "total": 1250,
    "pending": 325,
    "accepted": 350,
    "handled": 1085,
    "last_7_days": [120, 145, 132, 150, 110, 160, 140],
}

MOCK_FLEET_STATUS = {
    "available": 12,
    "busy": 8,
    "maintenance": 3,
}

MOCK_AVERAGE_HANDLING_TIME = 34  # minuti

MOCK_AVERAGE_RATING = 4.25

MOCK_REVIEWS = [
    {
        "id": str(uuid.uuid4()),
        "author": "Mario R.",
        "rating": 5,
        "comment": "Servizio rapidissimo.",
        "date": (datetime.now() - timedelta(days=2)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "author": "Anna B.",
        "rating": 4,
        "comment": "Attesa lunga ma risolto.",
        "date": (datetime.now() - timedelta(days=1)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "author": "Giovanni M.",
        "rating": 5,
        "comment": "Professionali e gentili.",
        "date": datetime.now().isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "author": "Elena S.",
        "rating": 3,
        "comment": "Potrebbe essere più veloce.",
        "date": (datetime.now() - timedelta(hours=12)).isoformat()
    },
]

MOCK_TRAFFIC_INCIDENTS = {
    "Milano": [
        {
            "id": str(uuid.uuid4()),
            "title": "Incidente in tangenziale Est a Milano, code di 4 km",
            "source": "Ansa",
            "pubDate": (datetime.now() - timedelta(minutes=15)).isoformat(),
            "link": "https://example.com/1"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Code sulla A4 in direzione Como, uscita al Castellano",
            "source": "Corriere",
            "pubDate": (datetime.now() - timedelta(minutes=8)).isoformat(),
            "link": "https://example.com/2"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Strada chiusa – Via di Niguarda direzione centro città blocca il traffico",
            "source": "TMB",
            "pubDate": (datetime.now() - timedelta(minutes=3)).isoformat(),
            "link": "https://example.com/3"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Incidente in A1 a Milano e Corsico, 3 corsie di 6 traffico bloccato",
            "source": "Ansa",
            "pubDate": (datetime.now() - timedelta(minutes=25)).isoformat(),
            "link": "https://example.com/4"
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Coda sulla circonvallazione esterna, senso unico alternato",
            "source": "Radio Lombardia",
            "pubDate": (datetime.now() - timedelta(minutes=30)).isoformat(),
            "link": "https://example.com/5"
        },
    ]
}

# ==========================================
# 📊 ENDPOINT: RICHIESTE TOTALI
# ==========================================
@bp.get("/total-requests")
def get_total_requests():
    try:
        return jsonify({
            "total": MOCK_REQUESTS_DATA["total"]
        }), 200
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
    try:
        return jsonify({
            "pending": MOCK_REQUESTS_DATA["pending"]
        }), 200
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
    try:
        return jsonify({
            "accepted": MOCK_REQUESTS_DATA["accepted"]
        }), 200
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
    try:
        return jsonify({
            "handled": MOCK_REQUESTS_DATA["handled"]
        }), 200
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
    try:
        if days < 1 or days > 365:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Giorni deve essere tra 1 e 365"
            }), 400
        
        # Restituisce gli ultimi giorni (limita a 7 se superiore)
        data = MOCK_REQUESTS_DATA["last_7_days"][:days] if days <= len(MOCK_REQUESTS_DATA["last_7_days"]) else MOCK_REQUESTS_DATA["last_7_days"]
        
        return jsonify({
            "days": days,
            "data": data
        }), 200
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
    try:
        return jsonify(MOCK_FLEET_STATUS), 200
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
    try:
        return jsonify({
            "average_minutes": MOCK_AVERAGE_HANDLING_TIME
        }), 200
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
    try:
        return jsonify({
            "average_rating": MOCK_AVERAGE_RATING
        }), 200
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
    try:
        return jsonify({
            "reviews": MOCK_REVIEWS,
            "count": len(MOCK_REVIEWS)
        }), 200
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
    try:
        city_capitalized = city.capitalize()
        
        # Se la città non è nel mock, restituisci lista vuota
        if city_capitalized not in MOCK_TRAFFIC_INCIDENTS:
            return jsonify({
                "city": city_capitalized,
                "incidents": [],
                "count": 0
            }), 200
        
        incidents = MOCK_TRAFFIC_INCIDENTS[city_capitalized]
        return jsonify({
            "city": city_capitalized,
            "incidents": incidents,
            "count": len(incidents)
        }), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero del traffico: {str(e)}"
        }), 500