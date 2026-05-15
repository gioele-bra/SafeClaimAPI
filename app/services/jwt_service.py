"""Validazione JWT emessi da Keycloak via JWKS.

Recupera e cachea le chiavi pubbliche del realm (`KC_JWKS_URL`) con TTL e
refresh-on-kid-miss. Verifica firma RS256, issuer ed `exp`/`iat`/`nbf`
con leeway configurabile. Non valida `aud` (Keycloak in password grant
usa `aud: account` di default).
"""

import logging
import threading
import time

import jwt
import requests
from jwt.algorithms import RSAAlgorithm

from ..config import Config

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 5
_JWKS_TTL_SECONDS = 600

_jwks_lock = threading.Lock()
_jwks_cache = {"data": None, "expires_at": 0.0}


class TokenError(Exception):
    """Errore generico di validazione token."""


class TokenMissing(TokenError):
    """Header Authorization mancante o malformato."""


class TokenInvalid(TokenError):
    """Token non valido (firma, formato, issuer, claim)."""


class TokenExpired(TokenError):
    """Token scaduto."""


def _fetch_jwks(force_refresh: bool = False) -> dict:
    """Scarica i JWKS dal realm e li memorizza in cache."""
    now = time.time()
    with _jwks_lock:
        if (
            not force_refresh
            and _jwks_cache["data"] is not None
            and _jwks_cache["expires_at"] > now
        ):
            return _jwks_cache["data"]

    try:
        resp = requests.get(Config.KC_JWKS_URL, timeout=_HTTP_TIMEOUT)
    except requests.RequestException as e:
        raise TokenInvalid(f"Impossibile recuperare JWKS: {e}") from e

    if resp.status_code != 200:
        raise TokenInvalid(
            f"JWKS endpoint ha risposto {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json() or {}
    keys_by_kid = {k.get("kid"): k for k in data.get("keys", []) if k.get("kid")}

    with _jwks_lock:
        _jwks_cache["data"] = keys_by_kid
        _jwks_cache["expires_at"] = time.time() + _JWKS_TTL_SECONDS

    return keys_by_kid


def _get_signing_key(kid: str):
    """Restituisce la chiave pubblica RSA per il `kid` indicato.

    In caso di miss, forza un refresh del JWKS (rotazione chiavi).
    """
    keys = _fetch_jwks(force_refresh=False)
    jwk = keys.get(kid)
    if jwk is None:
        keys = _fetch_jwks(force_refresh=True)
        jwk = keys.get(kid)
    if jwk is None:
        raise TokenInvalid(f"Nessuna chiave pubblica trovata per kid={kid}")
    return RSAAlgorithm.from_jwk(jwk)


def extract_bearer_token(auth_header: str | None) -> str:
    """Estrae il token da un header `Authorization: Bearer ...`."""
    if not auth_header:
        raise TokenMissing("Header Authorization mancante")
    parts = auth_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise TokenMissing("Header Authorization malformato")
    return parts[1].strip()


def verify_access_token(token: str) -> dict:
    """Verifica firma e claim del JWT e ritorna il payload decodificato."""
    try:
        unverified = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise TokenInvalid(f"Header JWT non valido: {e}") from e

    kid = unverified.get("kid")
    if not kid:
        raise TokenInvalid("Token senza 'kid' nell'header")

    signing_key = _get_signing_key(kid)

    try:
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=Config.KC_ISSUER,
            leeway=Config.JWT_LEEWAY_SECONDS,
            options={
                "verify_aud": False,
                "require": ["exp", "iat", "iss"],
            },
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenExpired("Token scaduto") from e
    except jwt.InvalidIssuerError as e:
        raise TokenInvalid(f"Issuer non valido: {e}") from e
    except jwt.PyJWTError as e:
        raise TokenInvalid(f"Token non valido: {e}") from e


# Esposto per testabilità (alcuni test possono voler resettare la cache).
def _reset_cache_for_tests() -> None:
    with _jwks_lock:
        _jwks_cache["data"] = None
        _jwks_cache["expires_at"] = 0.0
