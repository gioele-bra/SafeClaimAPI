import mysql.connector
from flask_cors import CORS
from flask import g

cors = CORS()

def init_mysql(app):
    cfg = app.config
    if not cfg.get("MYSQL_HOST"):
        app.logger.warning("MySQL: MYSQL_HOST non configurato")
        return

    def get_db_config():
        return {
            "host": cfg["MYSQL_HOST"],
            "port": int(cfg["MYSQL_PORT"]),
            "user": cfg["MYSQL_USERNAME"],
            "password": cfg["MYSQL_PASSWORD"],
            "database": cfg["MYSQL_DB"],
            "connection_timeout": 10,
        }

    @app.before_request
    def _open_db():
        try:
            conn = mysql.connector.connect(**get_db_config())
            g.db_conn = conn
            g.db = conn.cursor(dictionary=True)
        except Exception as e:
            app.logger.error("MySQL: impossibile aprire connessione: %s", e)

    @app.teardown_appcontext
    def _close_db(exc):
        cursor = g.pop("db", None)
        conn = g.pop("db_conn", None)
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        if conn is not None:
            try:
                if exc is None:
                    conn.commit()
                else:
                    conn.rollback()
            except Exception as e:
                app.logger.warning("MySQL: errore commit/rollback: %s", e)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass