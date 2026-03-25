from functools import wraps
from flask import request, jsonify


def issue_token(username: str, role: str = "user") -> str:
    # TODO: sostituire con JWT vero o integrazione Keycloak
    return f"demo-token-for:{username}:role:{role}"


def get_current_user(func):
    """Decoratore che simula la validazione del token. In produzione
    dovrebbe estrarre l'utente dal token JWT o da Keycloak.

    Per ora controlla la presenza dell'header Authorization e passa.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"error": "UNAUTHORIZED", "message": "Token mancante"}), 401
        # in un caso reale si farebbe la decodifica e reperimento utente
        return func(*args, **kwargs)
    return wrapper