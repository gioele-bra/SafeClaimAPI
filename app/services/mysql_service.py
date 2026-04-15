import mysql.connector
from mysql.connector import Error
from ..config import Config
import logging

logger = logging.getLogger(__name__)

class MySQLService:
    """Servizio per gestire connessioni e query a MySQL"""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MySQLService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            self._connect()
    
    def _connect(self):
        """Crea la connessione a MySQL"""
        try:
            self._connection = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USERNAME,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                autocommit=True
            )
            if self._connection.is_connected():
                logger.info("Connessione a MySQL stabilita")
        except Error as e:
            logger.error(f"Errore connessione MySQL: {str(e)}")
            raise
    
    def get_connection(self):
        """Ritorna la connessione a MySQL"""
        if self._connection is None or not self._connection.is_connected():
            self._connect()
        return self._connection
    
    def close(self):
        """Chiude la connessione a MySQL"""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None
            logger.info("Connessione a MySQL chiusa")

    def get_requests(self, status_filter=None):
        """
        Recupera le richieste dal database MySQL.
        Apre il puntatore (cursor), prende i dati e lo chiude.
        """
        conn = self.get_connection()
        # dictionary=True per avere i risultati come dizionari invece di tuple
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = "SELECT * FROM richieste"
            params = []
            
            if status_filter and status_filter != "Tutte":
                query += " WHERE status = %s"
                params.append(status_filter)
            
            cursor.execute(query, params)
            requests = cursor.fetchall()
            return requests
            
        except Error as e:
            logger.error(f"Errore query MySQL: {str(e)}")
            raise
        finally:
            # Chiusura del puntatore dopo aver preso i dati
            cursor.close()
