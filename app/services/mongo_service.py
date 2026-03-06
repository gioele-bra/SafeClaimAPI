from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from ..config import Config
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class MongoDBService:
    """Servizio per gestire connessioni e query a MongoDB"""
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Crea la connessione a MongoDB"""
        try:
            self._client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True
            )
            # Test della connessione
            self._client.admin.command('ping')
            self._db = self._client[Config.MONGODB_DB]
            logger.info("Connessione a MongoDB stabilita")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Errore connessione MongoDB: {str(e)}")
            raise
    
    def get_connection(self):
        """Ritorna la connessione a MongoDB"""
        if self._client is None:
            self._connect()
        return self._client
    
    def get_db(self):
        """Ritorna il database MongoDB"""
        if self._db is None:
            self._connect()
        return self._db
    
    def close(self):
        """Chiude la connessione a MongoDB"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("Connessione a MongoDB chiusa")
    
    def _sanitize_user_doc(self, user: Dict) -> Dict:
        """Rimuove dai documenti qualsiasi campo sensibile.

        Attualmente scarta i campi:
        - password / pwd / pwdHash
        - secret / token / apiKey
        - qualunque chiave inizi con "_" oltre all'id (protegge metadata interni)
        """
        sanitized = {}
        for k, v in user.items():
            low = k.lower()
            if low in ("password", "pwd", "pwdhash", "secret", "token", "apikey"):
                continue
            if k.startswith("_") and k != "_id":
                # non includere campi interni di MongoDB come _cls, _type, etc.
                continue
            sanitized[k] = v
        return sanitized

    def get_active_users(self) -> List[Dict]:
        """
        Recupera tutti gli utenti attivi da MongoDB
        
        I documenti restituiti vengono filtrati sul lato server per
        escludere eventuali campi sensibili indesiderati.
        """
        try:
            db = self.get_db()
            users_collection = db['users']
            
            # Query per trovare utenti attivi (status = "active" o active = true)
            active_users = list(users_collection.find(
                {
                    "$or": [
                        {"status": "active"},
                        {"active": True},
                        {"state": "active"}
                    ]
                },
                {
                    "_id": 1,
                    "username": 1,
                    "email": 1,
                    "name": 1,
                    "category": 1,
                    "status": 1,
                    "active": 1,
                    "createdAt": 1,
                    "lastLogin": 1
                }
            ))
            
            # Converti ObjectId a string per la serializzazione JSON e sanifica
            sanitized = []
            for user in active_users:
                if "_id" in user:
                    user["_id"] = str(user["_id"])
                sanitized.append(self._sanitize_user_doc(user))
            
            return sanitized
        except Exception as e:
            logger.error(f"Errore nel recupero utenti attivi: {str(e)}")
            raise
    
    def get_users_by_category(self, category: str) -> List[Dict]:
        """
        Recupera tutti gli utenti **attivi** di una specifica categoria.
        
        La query applica sia il filtro sulla categoria (supportando sia
        il campo singolo "category" che un array "categories") che una
        condizione di stato/attività per assicurarsi che vengano
        ritornati solamente utenti attivi.
        
        Args:
            category: La categoria degli utenti da filtrare
        
        Returns:
            Lista di utenti attivi appartenenti alla categoria specifica
        """
        try:
            db = self.get_db()
            users_collection = db['users']
            
            # Query per trovare utenti attivi nella categoria richiesta
            users = list(users_collection.find(
                {
                    "$and": [
                        {
                            "$or": [
                                {"category": category},
                                {"categories": category},
                                {"category": {"$in": [category]}}
                            ]
                        },
                        {
                            "$or": [
                                {"status": "active"},
                                {"active": True},
                                {"state": "active"}
                            ]
                        }
                    ]
                },
                {
                    "_id": 1,
                    "username": 1,
                    "email": 1,
                    "name": 1,
                    "category": 1,
                    "categories": 1,
                    "status": 1,
                    "active": 1,
                    "createdAt": 1
                }
            ))
            
            # Converti ObjectId a string per la serializzazione JSON e sanifica
            sanitized = []
            for user in users:
                if "_id" in user:
                    user["_id"] = str(user["_id"])
                sanitized.append(self._sanitize_user_doc(user))
            
            return sanitized
        except Exception as e:
            logger.error(f"Errore nel recupero utenti per categoria '{category}': {str(e)}")
            raise
    
    def get_all_categories(self) -> List[str]:
        """
        Recupera tutte le categorie disponibili
        
        Returns:
            Lista di categorie uniche
        """
        try:
            db = self.get_db()
            users_collection = db['users']
            
            # Trova tutte le categorie uniche
            categories = users_collection.distinct("category")
            
            # Se non ci sono risultati, prova con "categories" array
            if not categories:
                categories = users_collection.distinct("categories")
            
            return sorted(categories)
        except Exception as e:
            logger.error(f"Errore nel recupero categorie: {str(e)}")
            return []
