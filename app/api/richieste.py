from flask import Blueprint, jsonify, request

# Definizione del Blueprint
bp = Blueprint("richieste", __name__)

# Dizionario locale che simula il Database
MOCK_DATA = [
    {"id": 1, "datetime": "2024-05-20 10:30:00", "status": "Da gestire"},
    {"id": 2, "datetime": "2024-05-21 11:00:00", "status": "In corso"},
    {"id": 3, "datetime": "2024-05-21 14:20:00", "status": "Completate"},
    {"id": 4, "datetime": "2024-05-22 09:15:00", "status": "Da gestire"}
]

@bp.get("/")
def get_requests():
    # Recuperiamo il parametro 'status' dalla query string (es: ?status=In corso)
    status_filter = request.args.get("status")

    # Se il filtro è presente e non è "Tutte", filtriamo la lista
    if status_filter and status_filter != "Tutte":
        # Validazione base per gli stati ammessi
        valid_statuses = ["Da gestire", "In corso", "Completate"]
        
        if status_filter not in valid_statuses:
            return jsonify({
                "error": "BAD_REQUEST", 
                "message": f"Stato '{status_filter}' non valido."
            }), 400
            
        filtered_data = [r for r in MOCK_DATA if r["status"] == status_filter]
    else:
        # Se status è None o "Tutte", restituiamo tutto
        filtered_data = MOCK_DATA

    return jsonify({
        "success": True,
        "count": len(filtered_data),
        "data": filtered_data
    }), 200