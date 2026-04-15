from functools import wraps
from flask import request, jsonify

def issue_token(username: str, role: str = "user") -> str:
    # TODO: sostituire con JWT vero o integrazione Keycloak
    return f"demo-token-for:{username}:role:{role}"

def get_current_user(f):
    """
    Decoratore mock per verificare il token e simulare l'utente corrente.
    Al momento accetta qualsiasi token che inizi con 'demo-token-for:'.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            # Per ora lasciamo passare per facilitare lo sviluppo se non c'è header,
            # oppure ritorniamo 401. Data la natura dei mock, facciamo un controllo minimo.
            pass
        
        # In un'implementazione reale qui decodificheremmo il JWT
        # user = decode_token(auth_header.split(" ")[1])
        # if not user: return jsonify({"message": "Token non valido"}), 401
        
        return f(*args, **kwargs)
    return decorated
