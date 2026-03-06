import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    JSON_SORT_KEYS = False  # output JSON più leggibile
    
    # === MongoDB Configuration ===
    MONGODB_HOST = os.getenv("MONGODB_HOST", "mongo-safeclaim.aevorastudios.com")
    MONGODB_PORT = int(os.getenv("MONGODB_PORT", 27017))
    MONGODB_USERNAME = os.getenv("MONGODB_USERNAME", "safeclaim")
    MONGODB_PASSWORD = os.getenv("MONGODB_PASSWORD", "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=")
    MONGODB_DB = os.getenv("MONGODB_DB", "safeclaim_mongo")
    MONGODB_URI = os.getenv(
        "MONGODB_URI",
        f"mongodb://{MONGODB_USERNAME}:{MONGODB_PASSWORD.replace('+', '%2B').replace('=', '%3D')}@{MONGODB_HOST}:{MONGODB_PORT}/"
    )
    
    # === MySQL Configuration ===
    MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql-safeclaim.aevorastudios.com")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USERNAME = os.getenv("MYSQL_USERNAME", "safeclaim")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "0tHz31nhJ2hDOIccHehWamwNH8ItCklyZHGIISuE+tM=")
    MYSQL_DB = os.getenv("MYSQL_DB", "safeclaim_db")