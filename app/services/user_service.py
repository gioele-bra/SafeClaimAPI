from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    id: int
    username: str
    email: str
    nome: str
    cognome: str
    attivo: bool = True
    ruolo: str = "user"
    roles: List[str] = field(default_factory=list)
    password: str = ""

    def __post_init__(self):
        if not self.roles:
            self.roles = [self.ruolo]


class UserAlreadyExistsError(Exception):
    pass


_users: List[User] = [
    User(id=1, username="alice", email="alice@example.com", nome="Alice", cognome="Rossi", attivo=True, ruolo="admin"),
    User(id=2, username="bob", email="bob@example.com", nome="Bob", cognome="Verdi", attivo=False, ruolo="user"),
    User(id=3, username="carla", email="carla@example.com", nome="Carla", cognome="Bianchi", attivo=True, ruolo="perito"),
]


def get_user_list(active_only: bool = False, user_id: Optional[int] = None):
    """Restituisce la lista di utenti.

    Args:
        active_only: se True filtra soltanto quelli con ``attivo == True``
        user_id: se fornito ritorna solo l'utente con quell'id (o ``None`` se non
            trovato). Questo parametro è usato dall'endpoint del singolo utente.

    Returns:
        Lista di oggetti ``User`` (non dizionari) che rappresentano gli utenti.
    """
    results = _users
    if active_only:
        results = [u for u in results if u.attivo]
    if user_id is not None:
        results = [u for u in results if u.id == user_id]
    return results


def get_user_count(active_only: bool = False):
    """Conta gli utenti esistenti.

    ``active_only`` permette di considerare solamente gli utenti attivi."""
    if active_only:
        return len([u for u in _users if u.attivo])
    return len(_users)


def get_active_roles():
    """Restituisce l'insieme dei ruoli associati agli utenti attivi."""
    return list({u.ruolo for u in _users if u.attivo})


def activate_user(user_id):
    """Imposta ``attivo=True`` su un utente esistente; ritorna ``True`` se
    l'utente è stato trovato e aggiornato, ``False`` altrimenti."""
    for u in _users:
        if u.id == user_id:
            u.attivo = True
            return True
    return False


def delete_user(user_id):
    """Elimina un utente dalla lista in memoria."""
    global _users
    for idx, u in enumerate(_users):
        if u.id == user_id:
            del _users[idx]
            return True
    return False


def search_users(query):
    """Cerca utenti confrontando ``query`` con vari campi (case insensitive)."""
    q = (query or "").lower()
    return [u for u in _users if q in u.username.lower()
            or q in u.email.lower()
            or q in u.nome.lower()
            or q in u.cognome.lower()]


def create_user(username: str, email: str, password: str, roles: Optional[List[str]] = None):
    """Crea un utente in memoria per gli endpoint demo."""
    normalized_username = (username or "").strip()
    normalized_email = (email or "").strip().lower()
    normalized_roles = list(dict.fromkeys(roles or ["user"]))

    existing = next(
        (
            u for u in _users
            if u.username.lower() == normalized_username.lower()
            or u.email.lower() == normalized_email
        ),
        None,
    )
    if existing:
        raise UserAlreadyExistsError("Username o email gia registrati")

    next_id = max((u.id for u in _users), default=0) + 1
    user = User(
        id=next_id,
        username=normalized_username,
        email=normalized_email,
        nome=normalized_username,
        cognome="",
        ruolo=normalized_roles[0],
        roles=normalized_roles,
        password=password,
    )
    _users.append(user)
    return user
