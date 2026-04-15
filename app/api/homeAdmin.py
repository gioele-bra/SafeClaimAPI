from flask import Blueprint, jsonify, request, g
from copy import deepcopy

bp = Blueprint("home_admin", __name__)


def _format_user(row):
    """Formatta una riga Utente per la risposta JSON."""
    user = dict(row)
    user.pop("password_hash", None)
    if isinstance(user.get("ruolo"), str):
        user["ruolo"] = user["ruolo"].split(",") if user["ruolo"] else []
    if user.get("data_registrazione"):
        user["data_registrazione"] = user["data_registrazione"].isoformat()
    return user


@bp.get("/stats-ruoli")
def get_stats_ruoli():
    """Restituisce il conteggio reale per ogni ruolo."""
    g.db.execute("SELECT ruolo FROM Utente")
    rows = g.db.fetchall()

    stats = {}
    for row in rows:
        ruoli = row["ruolo"].split(",") if row["ruolo"] else []
        for r in ruoli:
            r = r.strip().capitalize()  # es. Perito, Admin, etc.
            stats[r] = stats.get(r, 0) + 1

    return jsonify({"status": "success", "data": stats}), 200


@bp.get("/notifiche/recenti")
def get_notifiche_recenti():
    """Restituisce le ultime attività del sistema (mock)."""
    mock_notifiche = [
        {
            "id": 1,
            "tipo": "registrazione",
            "messaggio": "Nuovo utente registrato: Mario Rossi",
            "data": "2026-04-15T10:00:00",
            "letta": False
        },
        {
            "id": 2,
            "tipo": "perizia",
            "messaggio": "Richiesta perizia SOS-2491 in sospeso",
            "data": "2026-04-15T09:45:00",
            "letta": False
        },
        {
            "id": 3,
            "tipo": "errore",
            "messaggio": "Segnalazione errore invio email a Luca Verdi",
            "data": "2026-04-15T09:30:00",
            "letta": True
        },
    ]
    return jsonify({"status": "success", "data": mock_notifiche}), 200


@bp.get("/utenti")
def get_utenti_paginati():
    """Ricerca utenti con paginazione lato server."""
    search = (request.args.get("search") or "").strip()
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
    except ValueError:
        return jsonify({"error": "BAD_REQUEST", "message": "page e per_page devono essere interi"}), 400

    offset = (page - 1) * per_page

    query = "SELECT * FROM Utente"
    count_query = "SELECT COUNT(*) as total FROM Utente"
    params = []

    if search:
        where = " WHERE nome LIKE %s OR cognome LIKE %s OR email LIKE %s"
        query += where
        count_query += where
        like_search = f"%{search}%"
        params = [like_search, like_search, like_search]

    query += " LIMIT %s OFFSET %s"
    params_with_limit = params + [per_page, offset]

    g.db.execute(count_query, tuple(params))
    total_row = g.db.fetchone()
    total = total_row["total"] if total_row else 0

    g.db.execute(query, tuple(params_with_limit))
    rows = g.db.fetchall()

    return jsonify({
        "status": "success",
        "data": [_format_user(r) for r in rows],
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    }), 200


@bp.get("/audit-logs")
def get_audit_logs():
    """Restituisce gli ultimi accessi o log di sistema (mock)."""
    mock_logs = [
        {"id": 1, "utente": "Admin", "azione": "Accesso effettuato", "timestamp": "2026-04-15T08:00:00", "ip": "192.168.1.1"},
        {"id": 2, "utente": "Perito1", "azione": "Modifica perizia SOS-2488", "timestamp": "2026-04-15T08:15:00", "ip": "192.168.1.5"},
        {"id": 3, "utente": "Sistema", "azione": "Backup database completato", "timestamp": "2026-04-15T03:00:00", "ip": "localhost"},
    ]
    return jsonify({"status": "success", "data": mock_logs}), 200


@bp.get("/status")
def get_system_status():
    """Restituisce lo stato corrente del sistema (mock)."""
    return jsonify({
        "status": "success",
        "data": {
            "database": "online",
            "auth_provider": "online",
            "storage": "online",
            "last_backup": "2026-04-15T03:00:00",
            "version": "1.0.0"
        }
    }), 200


@bp.get("/me")
def get_admin_me():
    """Recupera il profilo dell'amministratore loggato (mock)."""
    # In una app reale useremmo g.user o il token_service
    return jsonify({
        "status": "success",
        "data": {
            "id": 0,
            "nome": "Admin",
            "cognome": "SafeClaim",
            "email": "admin@safeclaim.it",
            "ruolo": ["admin"],
            "avatar_url": "https://i.pravatar.cc/150?u=admin"
        }
    }), 200
