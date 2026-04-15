class UserAlreadyExistsError(Exception):
    """Eccezione sollevata quando si tenta di creare un utente già esistente."""
    pass

class User:
    def __init__(self, id, username, email, roles):
        self.id = id
        self.username = username
        self.email = email
        self.roles = roles

def create_user(username, email, password, roles):
    # TODO: Implementazione reale con MySQL
    # Per ora restituiamo un oggetto mock per non bloccare l'app
    return User(id=999, username=username, email=email, roles=roles)

# Esempi delle funzioni service che dovrai implementare
def get_user_list():
    # Query DB per lista utenti
    pass

def get_user_count():
    # Conta totale utenti
    pass

def get_active_roles():
    # Ruoli attivi nel sistema
    pass

def activate_user(user_id):
    # Attiva utente
    pass

def delete_user(user_id):
    # Elimina utente
    pass

def search_users(query):
    # Cerca utenti con LIKE su nome, cognome, email, username
    pass
