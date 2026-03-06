import os
from dotenv import load_dotenv

# carica prima di leggere le variabili
load_dotenv()

class Config:
    # **Attenzione**: non committare credenziali reali nel repository!
    # Tutte le configurazioni sensibili devono provenire da variabili
    # d'ambiente (es. impostate in un file .env ignorato).

    SECRET_KEY = os.getenv("SECRET_KEY", "")
    JSON_SORT_KEYS = False  # output JSON più leggibile
    
    # === MongoDB Configuration ===
    MONGODB_HOST = os.getenv("MONGODB_HOST", "")
    MONGODB_PORT = int(os.getenv("MONGODB_PORT", 27017))
    MONGODB_USERNAME = os.getenv("MONGODB_USERNAME", "")
    MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "")
    MONGODB_DB = os.getenv("MONGODB_DB", "")
    MONGODB_URI = os.getenv(
        "MONGODB_URI",
        f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD.replace('+', '%2B').replace('=', '%3D')}@{MONGODB_HOST}:{MONGODB_PORT}/"
        if MONGODB_USERNAME and MONGODB_PASSWORD and MONGODB_HOST else ""
    )
    
    # === MySQL Configuration ===
    MYSQL_HOST = os.getenv("MYSQL_HOST", "")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "")

    def __repr__(self):
        # mostra solo valori non sensibili per debugging
        return (
            f"Config(mongo_host={self.MONGODB_HOST}, mongo_db={self.MONGODB_DB}, "
            f"mysql_host={self.MYSQL_HOST}, mysql_db={self.MYSQL_DB})"
        )

    @classmethod
    def _redact_uri(cls, uri: str) -> str:
        """Sostituisce la password in un URI Mongo/MySQL con ****."""
        # semplice regex-like
        if "@" in uri and ":" in uri:
            prefix, rest = uri.split("@", 1)
            if ":" in prefix:
                user, pwd = prefix.split(":", 1)
                return f"{user}:****@{rest}"
        return uri

    @property
    def MONGODB_URI_REDACTED(self) -> str:
        return self._redact_uri(self.MONGODB_URI)

    @property
    def MYSQL_URI_REDACTED(self) -> str:
        # non esiste una singola variabile ma possiamo costruirla
        return self._redact_uri(
            f"mysql://{self.MYSQL_USERNAME}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )