"""Client minimale per l'Admin REST API di Keycloak.

I realm roles devono essere PRE-CREATI lato Keycloak: questo modulo non
crea automaticamente ruoli mancanti. Se un ruolo richiesto non esiste
viene loggato un warning e l'utente viene comunque creato (senza quel
ruolo).
"""

import logging
import threading
import time
from typing import List, Optional

import requests

from ..config import Config

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 10

_token_lock = threading.Lock()
_token_cache = {"access_token": None, "expires_at": 0.0}

_ROLES_TTL = 300
_roles_lock = threading.Lock()
_roles_cache = {"data": None, "expires_at": 0.0}


class KeycloakError(Exception):
    """Errore generico di interazione con Keycloak."""


class KeycloakEmailConflictError(KeycloakError):
    """Email/username già esistente su Keycloak (HTTP 409)."""


def _admin_base() -> str:
    return f"{Config.KC_BASE_URL.rstrip('/')}/admin/realms/{Config.KC_REALM}"


def _token_url() -> str:
    return f"{Config.KC_BASE_URL.rstrip('/')}/realms/{Config.KC_REALM}/protocol/openid-connect/token"


def _get_admin_token() -> str:
    now = time.time()
    with _token_lock:
        if _token_cache["access_token"] and _token_cache["expires_at"] > now:
            return _token_cache["access_token"]

        if not Config.KC_ADMIN_CLIENT_ID or not Config.KC_ADMIN_CLIENT_SECRET:
            raise KeycloakError("KC_ADMIN_CLIENT_ID/KC_ADMIN_CLIENT_SECRET non configurati")

        try:
            resp = requests.post(
                _token_url(),
                data={
                    "grant_type": "client_credentials",
                    "client_id": Config.KC_ADMIN_CLIENT_ID,
                    "client_secret": Config.KC_ADMIN_CLIENT_SECRET,
                },
                timeout=_HTTP_TIMEOUT,
            )
        except requests.RequestException as e:
            raise KeycloakError(f"Errore richiesta token admin: {e}") from e

        if resp.status_code != 200:
            raise KeycloakError(f"Token admin negato: HTTP {resp.status_code} {resp.text}")

        body = resp.json()
        access = body.get("access_token")
        expires_in = int(body.get("expires_in", 60))
        if not access:
            raise KeycloakError("Token admin: response senza access_token")

        _token_cache["access_token"] = access
        _token_cache["expires_at"] = now + max(expires_in - 30, 5)
        return access


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_admin_token()}",
        "Content-Type": "application/json",
    }


def _get_realm_roles_map(force_refresh: bool = False) -> dict:
    """Restituisce {role_name: role_representation}, cachato con TTL."""
    now = time.time()
    with _roles_lock:
        if (not force_refresh
                and _roles_cache["data"] is not None
                and _roles_cache["expires_at"] > now):
            return _roles_cache["data"]

    try:
        resp = requests.get(
            f"{_admin_base()}/roles",
            headers=_auth_headers(),
            timeout=_HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        raise KeycloakError(f"Errore recupero realm roles: {e}") from e

    if resp.status_code != 200:
        raise KeycloakError(
            f"Recupero realm roles fallito: HTTP {resp.status_code} {resp.text}"
        )

    mapping = {r["name"]: r for r in (resp.json() or []) if "name" in r}

    with _roles_lock:
        _roles_cache["data"] = mapping
        _roles_cache["expires_at"] = now + _ROLES_TTL

    return mapping


def kc_create_user(
    email: str,
    nome: str,
    cognome: str,
    password: str,
    telefono: Optional[str] = None,
) -> str:
    """Crea l'utente su Keycloak e ritorna l'id (UUID) parsato da Location."""
    payload = {
        "username": email,
        "email": email,
        "firstName": nome,
        "lastName": cognome,
        "enabled": True,
        "emailVerified": False,
        "credentials": [{
            "type": "password",
            "value": password,
            "temporary": False,
        }],
    }
    if telefono:
        payload["attributes"] = {"telefono": [telefono]}

    try:
        resp = requests.post(
            f"{_admin_base()}/users",
            headers=_auth_headers(),
            json=payload,
            timeout=_HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        raise KeycloakError(f"Errore creazione utente Keycloak: {e}") from e

    if resp.status_code == 409:
        raise KeycloakEmailConflictError("Email già esistente su Keycloak")
    if resp.status_code not in (201, 204):
        raise KeycloakError(
            f"Creazione utente fallita: HTTP {resp.status_code} {resp.text}"
        )

    location = resp.headers.get("Location", "")
    if not location:
        raise KeycloakError("Creazione utente: header Location assente")

    kc_id = location.rstrip("/").rsplit("/", 1)[-1]
    if not kc_id:
        raise KeycloakError(f"Creazione utente: id non parsabile da Location='{location}'")
    return kc_id


def kc_assign_realm_roles(kc_id: str, role_names: List[str]) -> None:
    """Assegna i realm roles richiesti.

    I ruoli non presenti su Keycloak vengono loggati come warning e
    saltati senza far fallire l'operazione: i realm roles vanno
    pre-creati lato Keycloak.
    """
    if not role_names:
        return

    roles_map = _get_realm_roles_map()
    representations = []
    missing = []
    for name in role_names:
        if name in roles_map:
            r = roles_map[name]
            representations.append({"id": r["id"], "name": r["name"]})
        else:
            missing.append(name)

    if missing:
        logger.warning(
            "Keycloak: realm roles non trovati per utente %s: %s "
            "(da pre-creare lato Keycloak)",
            kc_id, missing,
        )

    if not representations:
        return

    try:
        resp = requests.post(
            f"{_admin_base()}/users/{kc_id}/role-mappings/realm",
            headers=_auth_headers(),
            json=representations,
            timeout=_HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        raise KeycloakError(f"Errore assegnazione ruoli: {e}") from e

    if resp.status_code not in (200, 204):
        raise KeycloakError(
            f"Assegnazione ruoli fallita: HTTP {resp.status_code} {resp.text}"
        )


def kc_delete_user(kc_id: str) -> bool:
    """Elimina utente da Keycloak (best-effort per il rollback compensativo).

    Ritorna True se la delete è andata a buon fine (o l'utente non
    esisteva), False altrimenti. Non solleva eccezioni: il chiamante usa
    il booleano per decidere come rispondere.
    """
    try:
        resp = requests.delete(
            f"{_admin_base()}/users/{kc_id}",
            headers=_auth_headers(),
            timeout=_HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        logger.error("Keycloak: rollback delete utente %s fallita: %s", kc_id, e)
        return False
    except KeycloakError as e:
        logger.error("Keycloak: rollback delete utente %s fallita (token/cfg): %s", kc_id, e)
        return False

    if resp.status_code not in (204, 404):
        logger.error(
            "Keycloak: rollback delete utente %s fallita: HTTP %s %s",
            kc_id, resp.status_code, resp.text,
        )
        return False
    return True
