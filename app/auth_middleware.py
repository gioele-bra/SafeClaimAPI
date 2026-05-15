"""Middleware globale di autenticazione JWT.

Registra un `before_request` su tutta l'app che:
  * salta whitelist (health, login, status, documentation, OPTIONS);
  * salta se `AUTH_BYPASS_FOR_TESTS` è True (settato dal conftest pytest);
  * se `AUTH_ENFORCEMENT_ENABLED` è False, logga un warning e prosegue
    (modalità "shadow" per rollout graduale);
  * altrimenti verifica il token via `jwt_service.verify_access_token` e
    popola `g.token_claims` e `g.current_user`.
"""

import logging

from flask import abort, current_app, g, request

from .services.jwt_service import (
    TokenError,
    TokenExpired,
    TokenInvalid,
    TokenMissing,
    extract_bearer_token,
    verify_access_token,
)

logger = logging.getLogger(__name__)

# (method, path) esatti — sempre pubblici.
WHITELIST_EXACT = frozenset({
    ("GET", "/"),
    ("GET", "/api/common/health"),
    ("POST", "/api/auth/login"),
    ("GET", "/api/auth/status"),
})

# Prefissi sempre pubblici (la barra finale è opzionale).
WHITELIST_PREFIXES = ("/documentation",)


def _is_whitelisted(method: str, path: str) -> bool:
    if method == "OPTIONS":
        return True
    if (method, path) in WHITELIST_EXACT:
        return True
    return any(path == p or path.startswith(p + "/") or path == p + "/"
               for p in WHITELIST_PREFIXES)


def _build_current_user(claims: dict) -> dict:
    """Riassunto utente derivato dai claim, comodo da leggere nei blueprint."""
    realm_roles = (claims.get("realm_access") or {}).get("roles") or []
    return {
        "sub": claims.get("sub"),
        "email": claims.get("email"),
        "preferred_username": claims.get("preferred_username"),
        "given_name": claims.get("given_name"),
        "family_name": claims.get("family_name"),
        "roles": realm_roles,
    }


def register_auth_middleware(app):
    @app.before_request
    def _enforce_auth():
        # 1) Bypass test (set in conftest)
        if current_app.config.get("AUTH_BYPASS_FOR_TESTS"):
            return None

        # 2) Whitelist (health, login, doc, OPTIONS)
        if _is_whitelisted(request.method, request.path):
            return None

        auth_header = request.headers.get("Authorization")

        try:
            token = extract_bearer_token(auth_header)
            claims = verify_access_token(token)
        except TokenError as e:
            # Rollout graduale: se l'enforcement è disabilitato, prosegui
            # ma logga il problema per monitorare i client da migrare.
            if not current_app.config.get("AUTH_ENFORCEMENT_ENABLED", True):
                logger.warning(
                    "AUTH SHADOW: %s %s rifiutata (%s) ma enforcement OFF",
                    request.method, request.path, e,
                )
                return None
            description = _error_description(e)
            abort(401, description=description)

        g.token_claims = claims
        g.current_user = _build_current_user(claims)
        return None


def _error_description(err: TokenError) -> str:
    if isinstance(err, TokenMissing):
        return "Header Authorization mancante o malformato"
    if isinstance(err, TokenExpired):
        return "Token scaduto"
    if isinstance(err, TokenInvalid):
        return f"Token non valido: {err}"
    return "Token non valido"
