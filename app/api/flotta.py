from flask import Blueprint, jsonify, request, g
import uuid

bp = Blueprint("flotta", __name__)

@bp.get("/")
def get_fleet():
    """Ritorna la lista completa dei veicoli dal database"""
    try:
        # Eseguiamo la query per ottenere tutti i veicoli
        g.db.execute("SELECT * FROM Veicoli ORDER BY name ASC")
        rows = g.db.fetchall()
        
        # Convertiamo i risultati in una lista di dizionari
        fleet = [dict(row) for row in rows]
        
        return jsonify(fleet), 200
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore nel recupero della flotta: {str(e)}"
        }), 500

@bp.get("/<int:vehicle_id>")
def get_vehicle(vehicle_id):
    """Ritorna i dettagli di un singolo veicolo tramite ID dal database"""
    try:
        g.db.execute("SELECT * FROM Veicoli WHERE id = %s", (vehicle_id,))
        row = g.db.fetchone()
        
        if row:
            return jsonify(dict(row)), 200
        
        return jsonify({
            "error": "NOT_FOUND",
            "message": f"Veicolo con ID {vehicle_id} non trovato"
        }), 404
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore durante la ricerca del veicolo: {str(e)}"
        }), 500

@bp.post("/contact")
def contact_driver():
    """Gestisce la logica di contatto (logica di business)"""
    try:
        data = request.get_json()
        
        if not data or 'driver' not in data:
            return jsonify({
                "error": "BAD_REQUEST",
                "message": "Dati mancanti: specificare il nome dell'autista"
            }), 400

        driver_name = data.get('driver')
        
        
        
        return jsonify({
            "status": "success",
            "message": f"Chiamata a {driver_name} inoltrata correttamente",
            "timestamp": uuid.uuid4().hex
        }), 200

    except Exception as e:
        return jsonify({
            "error": "INTERNAL_SERVER_ERROR",
            "message": f"Errore durante l'invio della chiamata: {str(e)}"
        }), 500





