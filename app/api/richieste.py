from flask import Blueprint, jsonify, request, current_app
from bson import json_util
import json
from pymongo import MongoClient

bp = Blueprint("richieste", __name__)

def get_db():
    # Recuperiamo il database usando l'URI e il nome DB nel config
    client = MongoClient(current_app.config["MONGODB_URI"])
    return client[current_app.config["MONGODB_DB"]]

@bp.get("/")
def get_requests():
    db = get_db()
    collection = db["Proto_Intervento_SC"]

    # 1. Recuperiamo il parametro dalla query string
    status_filter = request.args.get("stato")

    # 2. Costruiamo la query per MongoDB
    query = {}
   
    # Mappa i nomi "belli" dell'UI con i valori reali sul DB (visti nello screenshot)
    # Esempio: ?status=In corso -> cerca "in_corso"
    status_mapping = {
        "In corso": "in_corso",
        "Completate": "completato",
        "Da gestire": "da_gestire"
    }

    if status_filter and status_filter != "Tutte":
        db_status = status_mapping.get(status_filter, status_filter)
        query["stato"] = db_status

    try:
        # 3. Eseguiamo la query
        # .find(query) restituisce un cursore
        cursor = collection.find(query)
       
        # Trasformiamo il cursore in una lista
        # Usiamo json_util per gestire i tipi speciali di Mongo come l'ObjectId
        data = json.loads(json_util.dumps(list(cursor)))

        return jsonify({
            "success": True,
            "count": len(data),
            "data": data
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
