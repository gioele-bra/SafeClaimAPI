from flask_cors import CORS
from mysql.connector.pooling import MySQLConnectionPool
from flask import g

cors = CORS()

_pool = None


def init_mysql(app):
    """Crea un connection pool MySQL all'avvio dell'app."""
    global _pool

    cfg = app.config
    if not cfg.get("MYSQL_HOST"):
        app.logger.warning("MySQL: MYSQL_HOST non configurato, pool non creato")
        return

    _pool = MySQLConnectionPool(
        pool_name="safeclaim",
        pool_size=2,
        host=cfg["MYSQL_HOST"],
        port=cfg["MYSQL_PORT"],
        user=cfg["MYSQL_USERNAME"],
        password=cfg["MYSQL_PASSWORD"],
        database=cfg["MYSQL_DB"],
    )
    app.logger.info("MySQL: pool creato (%s:%s/%s)",
                     cfg["MYSQL_HOST"], cfg["MYSQL_PORT"], cfg["MYSQL_DB"])

    @app.before_request
    def _open_db():
        conn = _pool.get_connection()
        g.db_conn = conn
        g.db = conn.cursor(dictionary=True)

    @app.teardown_appcontext
    def _close_db(exc):
        cursor = g.pop("db", None)
        conn = g.pop("db_conn", None)
        if cursor is not None:
            cursor.close()
        if conn is not None:
            if exc is None:
                conn.commit()
            else:
                conn.rollback()
            conn.close()  # restituisce la connessione al pool
