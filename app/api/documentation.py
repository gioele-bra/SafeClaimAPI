"""Documentazione API + protezione Keycloak OIDC.

Per accedere a `/documentation/`:
  1. Browser → GET /documentation/ → controlla session cookie.
  2. Se non autenticato → redirect a /documentation/auth/login.
  3. /auth/login genera state, redirige a Keycloak authorize URL.
  4. Keycloak ↩ /documentation/auth/callback?code=...&state=...
  5. Scambio code → token. Verifico ruolo admin in `realm_access.roles`.
  6. Salvo sub+email+roles in session, redirect alla doc.

Variabili `.env` richieste:
  * KC_DOCS_CLIENT_ID
  * KC_DOCS_CLIENT_SECRET
  * KC_DOCS_REQUIRED_ROLE (default "admin")
  * SECRET_KEY (Flask) — DEVE essere settato per la session.
"""

import json
import secrets
from functools import wraps
from urllib.parse import urlencode

import requests
from flask import (
    Blueprint,
    current_app,
    make_response,
    redirect,
    request,
    session,
    url_for,
)

from ..config import Config

bp = Blueprint("documentation", __name__)

_HTTP_TIMEOUT = 10
_SESSION_KEY = "docs_user"
_STATE_KEY = "docs_oauth_state"


# ---------------------------------------------------------------------------
# OIDC helpers
# ---------------------------------------------------------------------------


def _oidc_authorize_url() -> str:
    return (
        f"{Config.KC_BASE_URL.rstrip('/')}"
        f"/realms/{Config.KC_REALM}/protocol/openid-connect/auth"
    )


def _oidc_token_url() -> str:
    return (
        f"{Config.KC_BASE_URL.rstrip('/')}"
        f"/realms/{Config.KC_REALM}/protocol/openid-connect/token"
    )


def _oidc_logout_url() -> str:
    return (
        f"{Config.KC_BASE_URL.rstrip('/')}"
        f"/realms/{Config.KC_REALM}/protocol/openid-connect/logout"
    )


def _redirect_uri() -> str:
    """URL assoluto della callback. Configurato lato Keycloak come
    Valid Redirect URI del client `safeclaim-docs`.
    """
    return url_for("documentation.auth_callback", _external=True)


def require_docs_auth(view):
    """Protegge la view richiedendo session cookie valido.

    Se la session manca o è incompleta, redirige a `/auth/login`
    preservando il `next` URL per il redirect post-login.
    """

    @wraps(view)
    def _wrapped(*args, **kwargs):
        user = session.get(_SESSION_KEY)
        if not user or Config.KC_DOCS_REQUIRED_ROLE not in (user.get("roles") or []):
            session.pop(_SESSION_KEY, None)
            return redirect(
                url_for("documentation.auth_login", next=request.path)
            )
        return view(*args, **kwargs)

    return _wrapped


# ---------------------------------------------------------------------------
# OIDC routes
# ---------------------------------------------------------------------------


@bp.get("/auth/login")
def auth_login():
    if not current_app.config.get("SECRET_KEY"):
        return _render_error(
            "Documentazione non configurata",
            "Flask <code>SECRET_KEY</code> non impostata sul server. "
            "Genera una chiave con "
            "<code>python3 -c \"import secrets; print(secrets.token_hex(32))\"</code> "
            "e mettila in <code>.env</code> come <code>SECRET_KEY=...</code>, poi riavvia."
        ), 503

    if not Config.KC_DOCS_CLIENT_ID or not Config.KC_DOCS_CLIENT_SECRET:
        return _render_error(
            "Documentazione non configurata",
            "Le variabili d'ambiente KC_DOCS_CLIENT_ID e "
            "KC_DOCS_CLIENT_SECRET non sono impostate sul server."
        ), 503

    state = secrets.token_urlsafe(32)
    session[_STATE_KEY] = state
    # Salviamo il path richiesto pre-login (default: root della doc).
    session["docs_next"] = request.args.get("next") or url_for("documentation.get_documentation")

    redirect_uri = _redirect_uri()
    current_app.logger.info("OIDC docs: redirect_uri usato = %s", redirect_uri)

    params = {
        "client_id": Config.KC_DOCS_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return redirect(f"{_oidc_authorize_url()}?{urlencode(params)}")


@bp.get("/auth/callback")
def auth_callback():
    # 1) Validazione state (CSRF)
    expected_state = session.pop(_STATE_KEY, None)
    received_state = request.args.get("state")
    if not expected_state or expected_state != received_state:
        return _render_error(
            "Autenticazione fallita",
            "Stato OAuth non valido (possibile CSRF). Riprovare il login."
        ), 400

    error = request.args.get("error")
    if error:
        desc = request.args.get("error_description") or error
        return _render_error("Autenticazione fallita", desc), 400

    code = request.args.get("code")
    if not code:
        return _render_error("Autenticazione fallita",
                              "Codice di autorizzazione mancante."), 400

    # 2) Scambio code → token
    try:
        resp = requests.post(
            _oidc_token_url(),
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _redirect_uri(),
                "client_id": Config.KC_DOCS_CLIENT_ID,
                "client_secret": Config.KC_DOCS_CLIENT_SECRET,
            },
            timeout=_HTTP_TIMEOUT,
        )
    except requests.RequestException as e:
        current_app.logger.error("Token exchange docs fallito: %s", e)
        return _render_error("Autenticazione fallita",
                              "Servizio identità non raggiungibile."), 502

    if resp.status_code != 200:
        current_app.logger.error("Token exchange docs HTTP %s: %s",
                                  resp.status_code, resp.text[:300])
        return _render_error("Autenticazione fallita",
                              "Keycloak ha rifiutato il code exchange."), 400

    tokens = resp.json() or {}
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    if not access_token:
        return _render_error("Autenticazione fallita",
                              "Token di accesso mancante nella response."), 502

    # 3) Verifica firma + ruolo richiesto
    try:
        from ..services.jwt_service import verify_access_token
        claims = verify_access_token(access_token)
    except Exception as e:
        current_app.logger.error("JWT docs invalid: %s", e)
        return _render_error("Autenticazione fallita",
                              f"Token non valido: {e}"), 400

    realm_roles = (claims.get("realm_access") or {}).get("roles") or []
    if Config.KC_DOCS_REQUIRED_ROLE not in realm_roles:
        return _render_error(
            "Accesso negato",
            f"Servono i privilegi di '{Config.KC_DOCS_REQUIRED_ROLE}' "
            f"per visualizzare la documentazione."
        ), 403

    # 4) Salva session
    session[_SESSION_KEY] = {
        "sub": claims.get("sub"),
        "email": claims.get("email") or claims.get("preferred_username"),
        "name": (claims.get("name")
                 or f"{claims.get('given_name','')} {claims.get('family_name','')}".strip()),
        "roles": realm_roles,
        "refresh_token": refresh_token,
    }

    next_url = session.pop("docs_next", None) or url_for("documentation.get_documentation")
    return redirect(next_url)


@bp.get("/auth/logout")
def auth_logout():
    user = session.pop(_SESSION_KEY, None)
    # Best-effort: invalidiamo anche la sessione su Keycloak.
    if user and user.get("refresh_token") and Config.KC_DOCS_CLIENT_ID:
        try:
            requests.post(
                _oidc_logout_url(),
                data={
                    "client_id": Config.KC_DOCS_CLIENT_ID,
                    "client_secret": Config.KC_DOCS_CLIENT_SECRET,
                    "refresh_token": user["refresh_token"],
                },
                timeout=5,
            )
        except requests.RequestException:
            pass

    return redirect(url_for("documentation.get_documentation"))


# ---------------------------------------------------------------------------
# SECTIONS — struttura della documentazione (v1)
# ---------------------------------------------------------------------------


METHOD_COLORS = {
    "GET": "#61affe",
    "POST": "#49cc90",
    "PUT": "#fca130",
    "DELETE": "#f93e3e",
    "PATCH": "#50e3c2",
}


def _ep(method, path, description, *, auth=True, request_body=None,
        query_params=None, response_example=None, response_code=200,
        errors=None):
    return {
        "method": method, "path": path, "description": description,
        "auth": auth,
        "request_body": request_body, "query_params": query_params,
        "response_example": response_example, "response_code": response_code,
        "errors": errors,
    }


SECTIONS = [
    {
        "name": "System",
        "prefix": "/api/v1",
        "description": "Endpoint di sistema (health, root).",
        "endpoints": [
            _ep("GET", "/", "Root health-check pubblico", auth=False,
                response_example={"name": "SafeClaim API", "status": "ok"}),
            _ep("GET", "/api/v1/health", "Health-check del servizio (pubblico)",
                auth=False,
                response_example={"status": "ok"}),
        ],
    },
    {
        "name": "Auth",
        "prefix": "/api/v1/auth",
        "description": "Profilo utente loggato, cambio password e (legacy) login mock.",
        "endpoints": [
            _ep("POST", "/api/v1/auth/login",
                "Login MOCK (deprecato). Accetta qualsiasi email in DB con password "
                "<code>admin123</code>. Risposta marcata con header <code>X-Deprecated: true</code>. "
                "I client reali fanno password grant direttamente contro Keycloak.",
                auth=False,
                request_body={
                    "email": {"type": "string", "required": True},
                    "password": {"type": "string", "required": True,
                                  "description": "Costante <code>admin123</code> in modalità mock"},
                },
                response_example={
                    "message": "Login OK (mock)",
                    "user": {"id": 1, "nome": "Mario", "cognome": "Rossi",
                              "email": "mario@example.com", "ruolo": ["automobilista"]}
                },
                errors={"400": "email/password mancanti",
                        "401": "Credenziali non valide"}),
            _ep("GET", "/api/v1/auth/me",
                "Profilo dell'utente loggato. Lookup su <code>Utente.keycloak_id</code>, "
                "fallback su email. Il campo <code>cognome</code> è omesso dalla response se NULL o stringa vuota.",
                response_example={
                    "status": "success",
                    "data": {"id": 12, "nome": "Mario", "cognome": "Rossi",
                              "email": "mario@example.com",
                              "telefono": "3331234567",
                              "ruolo": ["soccorso", "perito"]},
                }),
            _ep("PATCH", "/api/v1/auth/me",
                "Aggiorna il proprio account. Solo <code>nome</code> e <code>telefono</code>. "
                "<code>cognome</code> non è modificabile self-service.",
                request_body={
                    "nome": {"type": "string", "required": False},
                    "telefono": {"type": "string", "required": False},
                },
                response_example={
                    "status": "success",
                    "data": {"id": 12, "nome": "Mario", "cognome": "Rossi",
                              "email": "mario@example.com",
                              "telefono": "3333333333",
                              "ruolo": ["soccorso"]},
                },
                errors={"400": "FORBIDDEN_FIELD (cognome non self-modificabile) o BAD_REQUEST"}),
            _ep("POST", "/api/v1/auth/me/password",
                "Cambia la password. La <code>old_password</code> è validata via password "
                "grant su Keycloak; la nuova è impostata via Admin REST.",
                request_body={
                    "old_password": {"type": "string", "required": True},
                    "new_password": {"type": "string", "required": True,
                                      "description": "Minimo 8 caratteri, diversa dalla vecchia"},
                },
                response_example={"status": "success",
                                    "message": "Password aggiornata correttamente"},
                errors={
                    "400": "Validazione: lunghezza min 8 o uguale alla precedente",
                    "401": "INVALID_OLD_PASSWORD",
                    "502": "KEYCLOAK_UNAVAILABLE",
                }),
        ],
    },
    {
        "name": "Utenti",
        "prefix": "/api/v1/utenti",
        "description": "CRUD utenti consolidato (era split tra admin / gestioneUtenti / "
                        "creazioneUtenti / home-admin). Source of truth: MySQL <code>Utente</code> "
                        "con sync su Keycloak.",
        "endpoints": [
            _ep("GET", "/api/v1/utenti",
                "Lista utenti, paginata e con ricerca opzionale.",
                query_params={
                    "search":   {"type": "string",  "required": False,
                                 "description": "Like su nome/cognome/email"},
                    "page":     {"type": "integer", "required": False, "default": "1"},
                    "per_page": {"type": "integer", "required": False, "default": "50",
                                 "description": "Max 200"},
                },
                response_example={
                    "utenti": [{"id": 1, "nome": "Mario", "cognome": "Rossi",
                                  "email": "mario@example.com",
                                  "ruolo": ["automobilista"]}],
                    "pagination": {"total": 1, "page": 1, "per_page": 50, "total_pages": 1},
                }),
            _ep("POST", "/api/v1/utenti",
                "Crea utente su Keycloak + MySQL (con rollback compensativo).",
                request_body={
                    "nome":     {"type": "string", "required": True},
                    "cognome":  {"type": "string", "required": True},
                    "email":    {"type": "string", "required": True},
                    "password": {"type": "string", "required": True},
                    "telefono": {"type": "string", "required": False},
                    "ruolo":    {"type": "string|array", "required": False,
                                 "default": "automobilista",
                                 "description": "CSV o array di ruoli ammessi"},
                },
                response_code=201,
                response_example={
                    "message": "Utente creato con successo",
                    "user": {"id": 42, "nome": "Anna", "cognome": "Bianchi",
                              "email": "anna@example.com", "ruolo": ["perito"]},
                },
                errors={
                    "400": "Validazione (campi obbligatori, formato email, ruoli non riconosciuti)",
                    "500": "INCONSISTENT_STATE (Keycloak ok, rollback fallito)",
                    "502": "KEYCLOAK_UNAVAILABLE",
                }),
            _ep("GET", "/api/v1/utenti/count", "Numero totale di utenti.",
                response_example={"totale_utenti": 42}),
            _ep("GET", "/api/v1/utenti/stats-ruoli",
                "Conteggio utenti per ruolo (capitalizzato).",
                response_example={"status": "success",
                                    "data": {"Admin": 2, "Automobilista": 20, "Perito": 5}}),
            _ep("GET", "/api/v1/utenti/&lt;id&gt;", "Dettaglio singolo utente.",
                response_example={"id": 1, "nome": "Mario", "cognome": "Rossi",
                                    "email": "mario@example.com", "ruolo": ["automobilista"]},
                errors={"404": "Utente non trovato"}),
            _ep("PUT", "/api/v1/utenti/&lt;id&gt;",
                "Aggiorna dati anagrafici utente.",
                request_body={
                    "nome":     {"type": "string", "required": False},
                    "cognome":  {"type": "string", "required": False},
                    "email":    {"type": "string", "required": False},
                    "telefono": {"type": "string", "required": False},
                },
                response_example={"message": "Utente aggiornato", "utente": {"id": 1}},
                errors={"400": "Nessun campo da aggiornare", "404": "Utente non trovato"}),
            _ep("DELETE", "/api/v1/utenti/&lt;id&gt;", "Elimina utente.",
                response_example={"message": "Utente 1 eliminato con successo"},
                errors={"404": "Utente non trovato"}),
            _ep("POST", "/api/v1/utenti/&lt;id&gt;/ruoli",
                "Aggiorna i ruoli di un utente (replace della collezione).",
                request_body={
                    "ruoli": {"type": "array<string>", "required": True,
                               "description": "Ruoli ammessi: admin, automobilista, perito, "
                                              "officina, assicuratore, soccorso, azienda"},
                },
                response_example={"message": "Ruoli aggiornati con successo",
                                    "utente": {"id": 1, "ruolo": ["perito"]}},
                errors={"400": "Ruoli non riconosciuti", "404": "Utente non trovato"}),
        ],
    },
    {
        "name": "Sinistri",
        "prefix": "/api/v1/sinistri",
        "description": "Dettaglio sinistro e azioni (presa in carico, rifiuta, completa). "
                        "Sorgente: MongoDB <code>Proto_Sinistro_SC</code>.",
        "endpoints": [
            _ep("GET", "/api/v1/sinistri/&lt;id&gt;",
                "Dettaglio di un sinistro. <code>id</code> può essere "
                "<code>numero_sinistro</code> o ObjectId.",
                response_example={"data": {"id": "SIN-2026-23860",
                                              "cliente": "Stefano Lombardi",
                                              "stato": "accepted",
                                              "priorita": "bassa",
                                              "modello_veicolo": "Renault Clio",
                                              "targa": "ZQ149BF"}},
                errors={"404": "Intervento non trovato",
                        "500": "MONGO_AUTH_FAILED / MONGO_UNREACHABLE"}),
            _ep("POST", "/api/v1/sinistri/&lt;id&gt;/prendi-in-carico",
                "Imposta lo stato del sinistro a <code>accepted</code>. Funziona anche su "
                "sinistri precedentemente <code>rejected</code> (riprendibilità).",
                response_example={"message": "Intervento preso in carico",
                                    "request_id": "SIN-2026-23860",
                                    "new_status": "accepted",
                                    "data": {}},
                errors={"409": "INVALID_ACTION nello stato corrente"}),
            _ep("POST", "/api/v1/sinistri/&lt;id&gt;/rifiuta",
                "Imposta lo stato a <code>rejected</code>.",
                response_example={"message": "Intervento rifiutato",
                                    "new_status": "rejected"}),
            _ep("POST", "/api/v1/sinistri/&lt;id&gt;/completa",
                "Imposta lo stato a <code>handled</code> (solo da <code>accepted</code>).",
                response_example={"message": "Intervento completato",
                                    "new_status": "handled"}),
        ],
    },
    {
        "name": "Dashboard",
        "prefix": "/api/v1/dashboard",
        "description": "KPI e coda sinistri per la dashboard operativa.",
        "endpoints": [
            _ep("GET", "/api/v1/dashboard/riepilogo",
                "KPI di dashboard: richieste attive, completati oggi, tempo medio assegnazione, "
                "stato operativo del servizio.",
                response_example={
                    "data": {
                        "workshop_name": "Centrale Soccorso",
                        "operativo_online": True,
                        "kpi": {"richieste_attive": 6, "completati_oggi": 0,
                                  "tempo_medio_minuti": 178},
                        "selected_request_id": "SIN-2026-23860",
                    }
                }),
            _ep("GET", "/api/v1/dashboard/coda",
                "Coda dei sinistri da gestire (<code>attivo=true</code>, stato "
                "pending/accepted/rejected), ordinata per priorità+data.",
                response_example={"count": 1,
                                    "data": [{"id": "SIN-2026-23860",
                                                "cliente": "Stefano Lombardi",
                                                "status": "accepted",
                                                "available_actions": ["complete", "reject"]}]}),
            _ep("PATCH", "/api/v1/dashboard/stato-operativo",
                "Toggle dello stato operativo del soccorso (online/offline). Persistito su "
                "MongoDB <code>Proto_Impostazioni_Soccorso_SC</code>.",
                request_body={
                    "operativo_online": {"type": "boolean", "required": True},
                },
                response_example={"data": {"operativo_online": False}}),
        ],
    },
    {
        "name": "Analytics",
        "prefix": "/api/v1/analytics",
        "description": "Aggregate sui sinistri MongoDB + stato flotta MySQL.",
        "endpoints": [
            _ep("GET", "/api/v1/analytics/riepilogo",
                "Conteggi per stato + tempo medio di assegnazione (minuti).",
                response_example={"total": 6, "pending": 0, "accepted": 6,
                                    "handled": 0, "rejected": 0,
                                    "average_handling_minutes": 178}),
            _ep("GET", "/api/v1/analytics/ultimi-giorni/&lt;n&gt;",
                "Serie temporale: numero sinistri per giorno negli ultimi N giorni.",
                response_example={"days": 7, "data": [0, 0, 3, 2, 1, 0, 0]},
                errors={"400": "days deve essere 1..365"}),
            _ep("GET", "/api/v1/analytics/stato-flotta",
                "Conteggio veicoli per stato. Sorgente: MySQL <code>Veicoli</code>.",
                response_example={"available": 5, "busy": 2, "maintenance": 1}),
        ],
    },
    {
        "name": "Veicoli (Flotta)",
        "prefix": "/api/v1/veicoli",
        "description": "CRUD veicoli + contatto autista. Sorgente: MySQL <code>Veicoli</code>.",
        "endpoints": [
            _ep("GET", "/api/v1/veicoli", "Lista completa dei veicoli.",
                response_example=[{"id": 1, "name": "Carro-01",
                                      "status": "available", "driver": "Rossi"}]),
            _ep("GET", "/api/v1/veicoli/&lt;id&gt;", "Dettaglio veicolo.",
                errors={"404": "Veicolo non trovato"}),
            _ep("POST", "/api/v1/veicoli/contatto-autista",
                "Mock di chiamata autista (non integra ancora con un servizio reale).",
                request_body={
                    "driver": {"type": "string", "required": True},
                },
                response_example={"status": "success",
                                    "message": "Chiamata a Rossi inoltrata correttamente",
                                    "timestamp": "abc123"}),
        ],
    },
    {
        "name": "Soccorsi (legacy MySQL)",
        "prefix": "/api/v1/soccorsi",
        "description": "Lista richieste storiche da MySQL <code>Richiesta_Soccorso</code>. "
                        "Tabella legacy, NON allineata con i sinistri Mongo.",
        "endpoints": [
            _ep("GET", "/api/v1/soccorsi", "Lista richieste di soccorso (ordinate per data desc).",
                response_example={"count": 1, "data": [{"id": 1,
                                                              "data_richiesta": "2026-03-01T10:00:00"}]}),
        ],
    },
    {
        "name": "Impostazioni Soccorso",
        "prefix": "/api/v1/impostazioni",
        "description": "Configurazione del servizio soccorso (profilo, notifiche, parametri operativi). "
                        "Sorgente: MongoDB <code>Proto_Impostazioni_Soccorso_SC</code>.",
        "endpoints": [
            _ep("GET", "/api/v1/impostazioni",
                "Lettura completa delle impostazioni. Se Mongo non disponibile ritorna default + warning.",
                response_example={"status": "success",
                                    "data": {"profilo": {"nome": "Soccorso SafeClaim"},
                                              "notifiche": {"push": True, "email": False, "sms": False},
                                              "parametri_operativi": {"operativo_online": True}}}),
            _ep("PATCH", "/api/v1/impostazioni/profilo", "Aggiorna campi del profilo servizio.",
                request_body={
                    "nome":               {"type": "string|null", "required": False},
                    "email_contatto":     {"type": "string|null", "required": False},
                    "telefono_contatto":  {"type": "string|null", "required": False},
                    "avatar_url":         {"type": "string|null", "required": False},
                }),
            _ep("PATCH", "/api/v1/impostazioni/notifiche",
                "Toggle delle preferenze notifiche (booleani).",
                request_body={
                    "push":  {"type": "boolean", "required": False},
                    "email": {"type": "boolean", "required": False},
                    "sms":   {"type": "boolean", "required": False},
                }),
            _ep("PATCH", "/api/v1/impostazioni/parametri-operativi",
                "Aggiorna parametri operativi: orari, coda max, accettazione auto.",
                request_body={
                    "operativo_online":         {"type": "boolean", "required": False},
                    "orario_inizio":            {"type": "string (HH:MM)", "required": False},
                    "orario_fine":              {"type": "string (HH:MM)", "required": False},
                    "max_coda":                 {"type": "integer >= 0", "required": False},
                    "accettazione_automatica":  {"type": "boolean", "required": False},
                }),
        ],
    },
    {
        "name": "Alias legacy",
        "prefix": "(vari)",
        "description": "Tutti i vecchi path continuano a funzionare come alias permanenti. Mapping completo:",
        "endpoints": [
            _ep("*", "/api/common/health", "→ /api/v1/health", auth=False),
            _ep("*", "/api/auth/*",        "→ /api/v1/auth/* (login, status, me, me/password)", auth=False),
            _ep("*", "/api/gestioneUtenti/utenti*",   "→ /api/v1/utenti*"),
            _ep("*", "/api/gestioneUtenti/utenti/cerca?q=", "→ /api/v1/utenti?search="),
            _ep("*", "/api/creazioneUtenti/users",    "→ POST /api/v1/utenti"),
            _ep("*", "/api/home-admin/stats-ruoli",   "→ /api/v1/utenti/stats-ruoli"),
            _ep("*", "/api/dettaglioIntervento/&lt;id&gt;/*",
                "→ /api/v1/sinistri/&lt;id&gt;/* (take-in-charge → prendi-in-carico, reject → rifiuta, complete → completa)"),
            _ep("*", "/api/dashboard/*",   "→ /api/v1/dashboard/* (summary → riepilogo, requests → coda, operational-status → stato-operativo)"),
            _ep("*", "/api/analytics/*",   "→ /api/v1/analytics/* (summary → riepilogo, last-days → ultimi-giorni, fleet-status → stato-flotta)"),
            _ep("*", "/api/flotta/*",      "→ /api/v1/veicoli/* (contact → contatto-autista)"),
            _ep("*", "/api/soccorsi/",     "→ /api/v1/soccorsi"),
            _ep("*", "/api/impostazioni/*", "→ /api/v1/impostazioni/*"),
        ],
    },
]


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------


def _build_method_badge(method):
    color = METHOD_COLORS.get(method, "#999")
    return f'<span class="method-badge" style="background:{color}">{method}</span>'


def _build_params_table(params, title):
    if not params:
        return ""
    rows = ""
    for name, info in params.items():
        required = ('<span class="tag required">obbligatorio</span>'
                    if info.get("required")
                    else '<span class="tag optional">opzionale</span>')
        type_str = info.get("type", "string")
        default = (f' <span class="tag default">default: {info["default"]}</span>'
                    if info.get("default") else "")
        desc = info.get("description", "")
        rows += (f"<tr><td><code>{name}</code></td>"
                 f"<td><code>{type_str}</code></td>"
                 f"<td>{required}{default}</td>"
                 f"<td>{desc}</td></tr>")
    return f"""
    <div class="params-block">
        <h4>{title}</h4>
        <table class="params-table">
            <thead><tr><th>Campo</th><th>Tipo</th><th>Vincoli</th><th>Descrizione</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""


def _build_errors_block(errors):
    if not errors:
        return ""
    items = "".join(
        f'<li><span class="error-code">{code}</span> {msg}</li>'
        for code, msg in errors.items()
    )
    return f'<div class="errors-block"><h4>Errori</h4><ul>{items}</ul></div>'


def _build_response_block(endpoint):
    example = endpoint.get("response_example")
    if example is None:
        return ""
    code = endpoint.get("response_code", 200)
    formatted = json.dumps(example, indent=2, ensure_ascii=False)
    return f"""
    <div class="response-block">
        <h4>Risposta <span class="response-code">{code}</span></h4>
        <pre><code>{formatted}</code></pre>
    </div>"""


def _build_endpoint_card(ep):
    badge = _build_method_badge(ep["method"])
    body_table = _build_params_table(ep.get("request_body"), "Request Body")
    query_table = _build_params_table(ep.get("query_params"), "Query Parameters")
    response = _build_response_block(ep)
    errors = _build_errors_block(ep.get("errors"))
    auth_tag = ('<span class="tag auth-pub">pubblico</span>'
                if ep.get("auth") is False
                else '<span class="tag auth-priv">JWT richiesto</span>')

    return f"""
    <div class="endpoint-card">
        <div class="endpoint-header">
            {badge}
            <code class="endpoint-path">{ep["path"]}</code>
            {auth_tag}
        </div>
        <p class="endpoint-desc">{ep["description"]}</p>
        {body_table}
        {query_table}
        {response}
        {errors}
    </div>"""


def _build_nav(sections):
    items = ""
    for s in sections:
        anchor = s["name"].replace(" ", "-").replace("(", "").replace(")", "").lower()
        items += f'<a href="#{anchor}">{s["name"]}</a>'
    return items


_BASE_CSS = """
:root {
    --bg: #fafafa; --surface: #fff; --text: #1a1a2e; --text-muted: #555;
    --border: #e0e0e0; --primary: #2563eb; --primary-light: #dbeafe;
    --code-bg: #f1f5f9;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.55;
}
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
.topbar {
    display: flex; align-items: center; gap: 16px;
    padding: 14px 24px; background: var(--surface);
    border-bottom: 1px solid var(--border); position: sticky; top: 0; z-index: 10;
}
.topbar h1 { font-size: 1.05rem; font-weight: 700; flex: 1; }
.user-chip {
    background: var(--primary-light); color: var(--primary);
    padding: 6px 12px; border-radius: 12px; font-size: .85rem; font-weight: 600;
}
.logout-btn {
    background: transparent; border: 1px solid var(--border); padding: 6px 12px;
    border-radius: 8px; cursor: pointer; font-size: .85rem; color: var(--text-muted);
    text-decoration: none;
}
.logout-btn:hover { color: var(--text); border-color: var(--text-muted); }
.nav { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 24px; }
.nav a {
    padding: 6px 12px; background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; font-size: .85rem; color: var(--text-muted); text-decoration: none;
}
.nav a:hover { background: var(--primary-light); color: var(--primary); border-color: var(--primary); }
.info-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px; margin-bottom: 28px;
}
.info-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; padding: 14px;
}
.info-card h3 { font-size: .9rem; color: var(--text-muted); margin-bottom: 8px; }
.info-card p, .info-card ul, .info-card pre { font-size: .85rem; }
.info-card ul { list-style: none; }
.info-card code { background: var(--code-bg); padding: 1px 6px; border-radius: 4px; font-size: .82rem; }
section { margin-bottom: 36px; }
.section-header {
    display: flex; align-items: baseline; gap: 12px; padding-bottom: 8px;
    border-bottom: 2px solid var(--border); margin-bottom: 12px;
}
.section-header h2 { font-size: 1.4rem; }
.section-prefix { background: var(--code-bg); padding: 3px 8px; border-radius: 6px; font-size: .85rem; color: var(--text-muted); }
.section-desc { color: var(--text-muted); font-size: .9rem; margin-bottom: 14px; }
.endpoint-card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; margin-bottom: 12px;
}
.endpoint-header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.endpoint-path { background: var(--code-bg); padding: 4px 10px; border-radius: 6px; font-size: .9rem; flex: 1; min-width: 0; word-break: break-all; }
.endpoint-desc { color: var(--text-muted); font-size: .92rem; margin-bottom: 12px; }
.method-badge { color: white; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: .78rem; min-width: 60px; text-align: center; }
.params-block, .response-block, .errors-block { margin-top: 12px; }
h4 { font-size: .85rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px; letter-spacing: .04em; }
.params-table { width: 100%; border-collapse: collapse; font-size: .85rem; background: var(--surface); }
.params-table th, .params-table td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }
.params-table th { background: var(--code-bg); font-weight: 600; }
.tag { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: .72rem; font-weight: 600; }
.tag.required { background: #fee2e2; color: #b91c1c; }
.tag.optional { background: var(--code-bg); color: var(--text-muted); }
.tag.default { background: #ecfdf5; color: #047857; }
.tag.auth-priv { background: #fef3c7; color: #92400e; }
.tag.auth-pub { background: #d1fae5; color: #065f46; }
.response-block pre, .error-schema pre { background: var(--code-bg); padding: 10px; border-radius: 8px; overflow-x: auto; font-size: .82rem; }
.response-code { background: #10b981; color: white; padding: 1px 6px; border-radius: 4px; font-size: .72rem; font-weight: 700; margin-left: 6px; }
.errors-block li { margin-left: 12px; list-style: disc; font-size: .85rem; }
.error-code { background: #fee2e2; color: #b91c1c; padding: 1px 6px; border-radius: 4px; font-weight: 700; font-size: .78rem; }
.center-card {
    max-width: 420px; margin: 80px auto; background: var(--surface);
    border: 1px solid var(--border); border-radius: 14px; padding: 36px 32px;
    text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,.04);
}
.center-card h1 { font-size: 1.4rem; margin-bottom: 12px; }
.center-card p { color: var(--text-muted); margin-bottom: 20px; }
.btn-primary {
    display: inline-block; background: var(--primary); color: white;
    padding: 10px 22px; border-radius: 10px; font-weight: 600; text-decoration: none;
}
.btn-primary:hover { filter: brightness(1.08); }
.error-banner {
    background: #fee2e2; color: #b91c1c; padding: 12px 16px;
    border-radius: 10px; margin-bottom: 16px; font-size: .9rem;
}
"""


def _render_login_page():
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>SafeClaim API — Documentazione</title>
    <style>{_BASE_CSS}</style>
</head>
<body>
    <div class="center-card">
        <h1>📘 SafeClaim API Docs</h1>
        <p>L'accesso alla documentazione richiede credenziali con ruolo <code>{Config.KC_DOCS_REQUIRED_ROLE}</code> sul realm <code>{Config.KC_REALM}</code>.</p>
        <a class="btn-primary" href="{url_for('documentation.auth_login')}">Accedi con Keycloak</a>
    </div>
</body>
</html>"""
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


def _render_error(title, message):
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>{_BASE_CSS}</style>
</head>
<body>
    <div class="center-card">
        <h1>⚠️ {title}</h1>
        <p>{message}</p>
        <a class="btn-primary" href="{url_for('documentation.auth_login')}">Riprova login</a>
    </div>
</body>
</html>"""
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@bp.get("/")
def get_documentation():
    user = session.get(_SESSION_KEY)
    if not user or Config.KC_DOCS_REQUIRED_ROLE not in (user.get("roles") or []):
        return _render_login_page()

    nav = _build_nav(SECTIONS)
    sections_html = ""
    for section in SECTIONS:
        anchor = section["name"].replace(" ", "-").replace("(", "").replace(")", "").lower()
        endpoints_html = "".join(_build_endpoint_card(ep) for ep in section["endpoints"])
        sections_html += f"""
        <section id="{anchor}">
            <div class="section-header">
                <h2>{section["name"]}</h2>
                <code class="section-prefix">{section["prefix"]}</code>
            </div>
            <p class="section-desc">{section["description"]}</p>
            {endpoints_html}
        </section>"""

    display_name = user.get("name") or user.get("email") or "Admin"

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SafeClaim API — Documentazione</title>
<style>{_BASE_CSS}</style>
</head>
<body>
<div class="topbar">
    <h1>📘 SafeClaim API <code style="font-size:.85rem;background:var(--primary-light);padding:2px 8px;border-radius:6px;color:var(--primary);">v1</code></h1>
    <span class="user-chip">{display_name}</span>
    <a class="logout-btn" href="{url_for('documentation.auth_logout')}">Logout</a>
</div>

<div class="container">
    <p style="color:var(--text-muted); font-size:.9rem; margin-bottom:18px;">
        Tutte le rotte sotto <code>/api/v1/*</code> richiedono <strong>Bearer JWT Keycloak</strong>
        (realm <code>{Config.KC_REALM}</code>), eccetto quelle marcate <span class="tag auth-pub">pubblico</span>.
        I vecchi path pre-v1 funzionano ancora come alias.
    </p>

    <nav class="nav">{nav}</nav>

    <div class="info-grid">
        <div class="info-card">
            <h3>Autenticazione</h3>
            <p>JWT firmato Keycloak (RS256). Header: <code>Authorization: Bearer &lt;token&gt;</code>.
            Issuer atteso: <code>{Config.KC_ISSUER}</code>.</p>
        </div>
        <div class="info-card">
            <h3>Ruoli</h3>
            <ul>
                <li>admin</li><li>automobilista</li><li>perito</li>
                <li>officina</li><li>assicuratore</li><li>soccorso</li><li>azienda</li>
            </ul>
        </div>
        <div class="info-card">
            <h3>Formato errori</h3>
            <div class="error-schema"><pre>{{"error": "CODICE", "message": "..."}}</pre></div>
        </div>
        <div class="info-card">
            <h3>Errori globali</h3>
            <ul>
                <li><span class="error-code">401</span> UNAUTHORIZED (JWT mancante/non valido)</li>
                <li><span class="error-code">404</span> NOT_FOUND</li>
                <li><span class="error-code">405</span> METHOD_NOT_ALLOWED</li>
                <li><span class="error-code">500</span> INTERNAL_ERROR (incluse MONGO_AUTH_FAILED/UNREACHABLE)</li>
            </ul>
        </div>
    </div>

    {sections_html}
</div>
</body>
</html>"""

    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp
