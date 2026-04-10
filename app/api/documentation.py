import json
from flask import Blueprint, make_response

bp = Blueprint("documentation", __name__)

METHOD_COLORS = {
    "GET": "#61affe",
    "POST": "#49cc90",
    "PUT": "#fca130",
    "DELETE": "#f93e3e",
    "PATCH": "#50e3c2",
}

SECTIONS = [
    {
        "name": "Root",
        "prefix": "/",
        "description": "Endpoint di stato generale dell'API",
        "endpoints": [
            {
                "method": "GET",
                "path": "/",
                "description": "Health check generale",
                "response_example": {"name": "SafeClaim API", "status": "ok"},
            }
        ],
    },
    {
        "name": "Common",
        "prefix": "/api/common",
        "description": "Endpoint comuni di supporto",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/common/health",
                "description": "Health check del servizio",
                "response_example": {"status": "ok"},
            }
        ],
    },
    {
        "name": "Autenticazione",
        "prefix": "/api/auth",
        "description": "Endpoint di autenticazione (mock &ndash; Keycloak in arrivo)",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/auth/login",
                "description": "Login utente (mock). Accetta qualsiasi email in DB con password <code>admin123</code>.",
                "request_body": {
                    "email": {"type": "string", "required": True, "description": "Email dell'utente"},
                    "password": {"type": "string", "required": True, "description": "Password dell'utente"},
                },
                "response_example": {
                    "message": "Login OK (mock)",
                    "user": {"id": 1, "nome": "Mario", "cognome": "Rossi", "email": "mario@example.com", "ruolo": ["automobilista"]},
                },
                "errors": {"400": "email e password obbligatori", "401": "Credenziali non valide"},
            },
            {
                "method": "GET",
                "path": "/api/auth/status",
                "description": "Stato del provider di autenticazione",
                "response_example": {"message": "Autenticazione gestita da Keycloak (mock attivo)", "provider": "mock"},
            },
        ],
    },
    {
        "name": "Admin &ndash; Gestione Utenti",
        "prefix": "/api/admin",
        "description": "CRUD utenti lato amministrativo",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/admin/",
                "description": "Lista tutti gli utenti",
                "response_example": [{"id": 1, "nome": "Mario", "cognome": "Rossi", "email": "mario@example.com", "telefono": "3331234567", "ruolo": ["automobilista"], "data_registrazione": "2025-01-01T00:00:00"}],
            },
            {
                "method": "GET",
                "path": "/api/admin/count",
                "description": "Numero totale utenti",
                "response_example": {"total_users": 42},
            },
            {
                "method": "GET",
                "path": "/api/admin/roles-report",
                "description": "Report conteggio utenti per ruolo",
                "response_example": {"status": "success", "roles_count": {"automobilista": 20, "perito": 5, "admin": 2}},
            },
            {
                "method": "GET",
                "path": "/api/admin/&lt;user_id&gt;",
                "description": "Dettaglio singolo utente per ID",
                "response_example": {"id": 1, "nome": "Mario", "cognome": "Rossi", "email": "mario@example.com", "telefono": "3331234567", "ruolo": ["automobilista"], "data_registrazione": "2025-01-01T00:00:00"},
                "errors": {"404": "Utente non trovato"},
            },
            {
                "method": "POST",
                "path": "/api/admin/",
                "description": "Crea un nuovo utente",
                "request_body": {
                    "nome": {"type": "string", "required": True},
                    "cognome": {"type": "string", "required": True},
                    "email": {"type": "string", "required": True},
                    "password": {"type": "string", "required": True},
                    "telefono": {"type": "string", "required": False},
                    "ruolo": {"type": "string", "required": False, "default": "automobilista"},
                },
                "response_code": 201,
                "errors": {"400": "Campi obbligatori mancanti / Email gi&agrave; registrata"},
            },
            {
                "method": "PUT",
                "path": "/api/admin/&lt;user_id&gt;",
                "description": "Aggiorna dati utente (nome, cognome, email, telefono)",
                "request_body": {
                    "nome": {"type": "string", "required": False},
                    "cognome": {"type": "string", "required": False},
                    "email": {"type": "string", "required": False},
                    "telefono": {"type": "string", "required": False},
                },
                "errors": {"400": "Nessun campo da aggiornare", "404": "Utente non trovato"},
            },
            {
                "method": "DELETE",
                "path": "/api/admin/&lt;user_id&gt;",
                "description": "Elimina utente per ID",
                "response_example": {"message": "Utente 1 eliminato con successo"},
                "errors": {"404": "Utente non trovato"},
            },
        ],
    },
    {
        "name": "Creazione Utenti",
        "prefix": "/api/creazioneUtenti",
        "description": "Registrazione utenti con validazione ruoli",
        "endpoints": [
            {
                "method": "POST",
                "path": "/api/creazioneUtenti/users",
                "description": "Crea un nuovo utente con validazione email e ruoli",
                "request_body": {
                    "nome": {"type": "string", "required": True},
                    "cognome": {"type": "string", "required": True},
                    "email": {"type": "string", "required": True, "description": "Deve contenere @ e dominio valido"},
                    "password": {"type": "string", "required": True},
                    "telefono": {"type": "string", "required": False},
                    "ruolo": {"type": "string | array", "required": False, "default": "automobilista",
                              "description": "Uno o pi&ugrave; ruoli separati da virgola oppure array. Valori ammessi: admin, automobilista, perito, officina, assicuratore, azienda"},
                },
                "response_code": 201,
                "response_example": {"message": "Utente creato con successo", "user": {"id": 1, "nome": "Mario", "cognome": "Rossi", "email": "mario@example.com", "ruolo": ["automobilista"]}},
                "errors": {"400": "Campi obbligatori mancanti / Formato email non valido / Ruoli non riconosciuti / Email gi&agrave; registrata"},
            }
        ],
    },
    {
        "name": "Gestione Utenti",
        "prefix": "/api/gestioneUtenti",
        "description": "CRUD e ricerca utenti",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/gestioneUtenti/utenti",
                "description": "Lista tutti gli utenti",
                "response_example": {"utenti": [{"id": 1, "nome": "Mario", "cognome": "Rossi", "email": "mario@example.com", "telefono": "3331234567", "ruolo": ["automobilista"], "data_registrazione": "2025-01-01T00:00:00"}]},
            },
            {
                "method": "GET",
                "path": "/api/gestioneUtenti/utenti/count",
                "description": "Numero totale utenti",
                "response_example": {"totale_utenti": 42},
            },
            {
                "method": "GET",
                "path": "/api/gestioneUtenti/utenti/ruoli",
                "description": "Lista ruoli attualmente in uso nel sistema",
                "response_example": {"ruoli_attivi": ["admin", "automobilista", "perito"]},
            },
            {
                "method": "GET",
                "path": "/api/gestioneUtenti/utenti/cerca",
                "description": "Cerca utenti per nome, cognome o email (ricerca parziale)",
                "query_params": {"q": {"type": "string", "required": True, "description": "Termine di ricerca"}},
                "response_example": {"utenti_trovati": [{"id": 1, "nome": "Mario", "cognome": "Rossi", "email": "mario@example.com"}]},
                "errors": {"400": "parametro 'q' obbligatorio"},
            },
            {
                "method": "GET",
                "path": "/api/gestioneUtenti/utenti/&lt;user_id&gt;",
                "description": "Dettaglio singolo utente per ID",
                "errors": {"404": "UTENTE_NON_TROVATO"},
            },
            {
                "method": "PUT",
                "path": "/api/gestioneUtenti/utenti/&lt;user_id&gt;",
                "description": "Modifica dati utente (nome, cognome, email, telefono)",
                "request_body": {
                    "nome": {"type": "string", "required": False},
                    "cognome": {"type": "string", "required": False},
                    "email": {"type": "string", "required": False},
                    "telefono": {"type": "string", "required": False},
                },
                "response_example": {"message": "Utente aggiornato", "utente": {"id": 1, "nome": "Mario", "cognome": "Rossi", "email": "mario@example.com"}},
                "errors": {"400": "Nessun campo da aggiornare", "404": "Utente non trovato"},
            },
            {
                "method": "DELETE",
                "path": "/api/gestioneUtenti/utenti/&lt;user_id&gt;",
                "description": "Elimina utente per ID",
                "response_example": {"message": "Utente 1 eliminato con successo"},
                "errors": {"404": "Utente non trovato"},
            },
        ],
    },
    {
        "name": "Soccorsi",
        "prefix": "/api/soccorsi",
        "description": "Richieste di soccorso stradale",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/soccorsi/",
                "description": "Lista tutte le richieste di soccorso (ordinate per data decrescente)",
                "response_example": {"count": 1, "data": [{"id": 1, "data_richiesta": "2025-06-01T10:30:00", "orario_arrivo": "2025-06-01T11:00:00"}]},
            },
            {
                "method": "GET",
                "path": "/api/soccorsi/&lt;soccorso_id&gt;",
                "description": "Dettaglio singola richiesta di soccorso",
                "errors": {"404": "Richiesta non trovata"},
            },
        ],
    },
    {
        "name": "Richieste",
        "prefix": "/api/richieste",
        "description": "Gestione richieste con filtro per stato",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/richieste/",
                "description": "Lista richieste, con filtro opzionale per stato",
                "query_params": {"status": {"type": "string", "required": False, "description": "Filtra per stato. Valori ammessi: in_attesa, assegnata, in_corso, completata, annullata"}},
                "response_example": {"success": True, "count": 1, "data": [{"id": 1, "data_richiesta": "2025-06-01T10:30:00", "orario_arrivo": "2025-06-01T11:00:00"}]},
                "errors": {"400": "Stato non valido"},
            },
            {
                "method": "GET",
                "path": "/api/richieste/&lt;richiesta_id&gt;",
                "description": "Dettaglio singola richiesta per ID",
                "errors": {"404": "Richiesta non trovata"},
            },
        ],
    },
    {
        "name": "Dashboard Soccorso",
        "prefix": "/api/dashboard",
        "description": "Endpoint per la dashboard del soccorso (KPI, richieste e stato operativo)",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/dashboard/summary",
                "description": "Recupera il sommario della dashboard (nome officina, KPI e ID richiesta selezionata)",
                "response_example": {
                    "data": {
                        "workshop_name": "Officina Centrale",
                        "operativo_online": True,
                        "kpi": {
                            "richieste_attive": 2,
                            "completati_oggi": 1,
                            "tempo_medio_minuti": 34
                        },
                        "selected_request_id": "SOS-2491"
                    }
                },
            },
            {
                "method": "GET",
                "path": "/api/dashboard/requests",
                "description": "Lista tutte le richieste visibili in dashboard",
                "response_example": {
                    "count": 3,
                    "data": [
                        {
                            "id": "SOS-2491",
                            "vehicle_type": "Furgone",
                            "vehicle_label": "Fiat Ducato",
                            "cliente": "Mario Rossi",
                            "posizione": "Milano Centrale",
                            "lat": 45.4841,
                            "lng": 9.2043,
                            "status": "pending",
                            "status_text": "In attesa di presa in carico",
                            "available_actions": ["take_in_charge", "reject"]
                        }
                    ]
                },
            },
            {
                "method": "PATCH",
                "path": "/api/dashboard/operational-status",
                "description": "Aggiorna lo stato di disponibilità (online/offline) dell'officina",
                "request_body": {
                    "operativo_online": {"type": "boolean", "required": True, "description": "Nuovo stato operativo"}
                },
                "response_example": {
                    "message": "Stato operativo aggiornato",
                    "data": {
                        "workshop_name": "Officina Centrale",
                        "operativo_online": False,
                        "kpi": {"richieste_attive": 2, "completati_oggi": 1, "tempo_medio_minuti": 34},
                        "selected_request_id": "SOS-2491"
                    }
                },
                "errors": {"400": "Il campo 'operativo_online' deve essere booleano"},
            },
        ],
    },
    {
        "name": "Dettaglio Intervento",
        "prefix": "/api/dettaglioIntervento",
        "description": "Dettaglio intervento e azioni operative usate dal frontend soccorso",
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/dettaglioIntervento/&lt;request_id&gt;",
                "description": "Recupera il dettaglio di un intervento specifico",
                "response_example": {
                    "data": {
                        "id": "SOS-2491",
                        "cliente": "Mario Rossi",
                        "vehicle_type": "Furgone",
                        "vehicle_label": "Fiat Ducato",
                        "status": "pending",
                        "status_text": "In attesa di presa in carico",
                        "lat": 45.4841,
                        "lng": 9.2043,
                        "posizione": "Milano Centrale",
                        "requested_at": "2026-04-10T08:45:00",
                        "assigned_driver": None,
                        "notes": "Veicolo fermo per guasto elettrico. Cliente in attesa sul posto.",
                        "available_actions": ["take_in_charge", "reject"]
                    }
                },
                "errors": {"404": "Intervento non trovato"},
            },
            {
                "method": "POST",
                "path": "/api/dettaglioIntervento/&lt;request_id&gt;/take-in-charge",
                "description": "Prende in carico un intervento in stato pending",
                "request_body": {},
                "response_example": {
                    "message": "Intervento preso in carico con successo",
                    "request_id": "SOS-2491",
                    "new_status": "accepted",
                    "data": {
                        "id": "SOS-2491",
                        "cliente": "Mario Rossi",
                        "vehicle_type": "Furgone",
                        "status": "accepted",
                        "status_text": "Intervento assegnato",
                        "lat": 45.4841,
                        "lng": 9.2043,
                        "posizione": "Milano Centrale",
                        "requested_at": "2026-04-10T08:45:00",
                        "assigned_driver": "Officina Centrale",
                        "notes": "Veicolo fermo per guasto elettrico. Cliente in attesa sul posto.",
                        "available_actions": ["complete", "reject"]
                    }
                },
                "errors": {
                    "404": "Intervento non trovato",
                    "409": "Azione non disponibile per lo stato corrente",
                },
            },
            {
                "method": "POST",
                "path": "/api/dettaglioIntervento/&lt;request_id&gt;/reject",
                "description": "Rifiuta un intervento in stato pending o accepted",
                "request_body": {},
                "response_example": {
                    "message": "Intervento rifiutato con successo",
                    "request_id": "SOS-2491",
                    "new_status": "rejected",
                    "data": {
                        "id": "SOS-2491",
                        "cliente": "Mario Rossi",
                        "vehicle_type": "Furgone",
                        "status": "rejected",
                        "status_text": "Intervento rifiutato",
                        "lat": 45.4841,
                        "lng": 9.2043,
                        "posizione": "Milano Centrale",
                        "requested_at": "2026-04-10T08:45:00",
                        "assigned_driver": None,
                        "notes": "Veicolo fermo per guasto elettrico. Cliente in attesa sul posto.",
                        "available_actions": []
                    }
                },
                "errors": {
                    "404": "Intervento non trovato",
                    "409": "Azione non disponibile per lo stato corrente",
                },
            },
            {
                "method": "POST",
                "path": "/api/dettaglioIntervento/&lt;request_id&gt;/complete",
                "description": "Completa un intervento in stato accepted",
                "request_body": {},
                "response_example": {
                    "message": "Intervento completato con successo",
                    "request_id": "SOS-2492",
                    "new_status": "handled",
                    "data": {
                        "id": "SOS-2492",
                        "cliente": "Anna Bianchi",
                        "vehicle_type": "SUV",
                        "status": "handled",
                        "status_text": "Intervento completato",
                        "lat": 45.4517,
                        "lng": 9.1765,
                        "posizione": "Navigli",
                        "requested_at": "2026-04-10T09:10:00",
                        "assigned_driver": "Officina Centrale",
                        "notes": "Richiesto traino verso officina convenzionata.",
                        "available_actions": []
                    }
                },
                "errors": {
                    "404": "Intervento non trovato",
                    "409": "Azione non disponibile per lo stato corrente",
                },
            },
        ],
    },
    {
        "name": "Documentazione",
        "prefix": "/documentation",
        "description": "Questo endpoint",
        "endpoints": [
            {
                "method": "GET",
                "path": "/documentation",
                "description": "Restituisce la documentazione completa dell'API in formato HTML",
            }
        ],
    },
]


def _build_method_badge(method):
    color = METHOD_COLORS.get(method, "#999")
    return f'<span class="method-badge" style="background:{color}">{method}</span>'


def _build_params_table(params, title):
    if not params:
        return ""
    rows = ""
    for name, info in params.items():
        required = '<span class="tag required">obbligatorio</span>' if info.get("required") else '<span class="tag optional">opzionale</span>'
        type_str = info.get("type", "string")
        default = f' <span class="tag default">default: {info["default"]}</span>' if info.get("default") else ""
        desc = info.get("description", "")
        rows += f"<tr><td><code>{name}</code></td><td><code>{type_str}</code></td><td>{required}{default}</td><td>{desc}</td></tr>"
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
    items = "".join(f'<li><span class="error-code">{code}</span> {msg}</li>' for code, msg in errors.items())
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

    return f"""
    <div class="endpoint-card">
        <div class="endpoint-header">
            {badge}
            <code class="endpoint-path">{ep["path"]}</code>
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
        anchor = s["name"].replace(" ", "-").replace("&ndash;", "-")
        items += f'<a href="#{anchor}">{s["name"]}</a>'
    return items


@bp.get("/")
def get_documentation():
    nav = _build_nav(SECTIONS)

    sections_html = ""
    for section in SECTIONS:
        anchor = section["name"].replace(" ", "-").replace("&ndash;", "-")
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

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SafeClaim API &ndash; Documentazione</title>
<style>
    :root {{
        --bg: #fafafa;
        --surface: #ffffff;
        --text: #1a1a2e;
        --text-muted: #555;
        --border: #e0e0e0;
        --primary: #2563eb;
        --primary-light: #dbeafe;
        --code-bg: #f1f5f9;
        --sidebar-w: 260px;
    }}

    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.6;
    }}

    /* ── Sidebar ── */
    .sidebar {{
        position: fixed;
        top: 0; left: 0;
        width: var(--sidebar-w);
        height: 100vh;
        background: var(--surface);
        border-right: 1px solid var(--border);
        padding: 24px 16px;
        overflow-y: auto;
        z-index: 10;
    }}
    .sidebar h1 {{
        font-size: 1.2rem;
        margin-bottom: 4px;
        color: var(--primary);
    }}
    .sidebar .version {{
        font-size: .75rem;
        color: var(--text-muted);
        margin-bottom: 20px;
        display: block;
    }}
    .sidebar a {{
        display: block;
        padding: 6px 10px;
        margin: 2px 0;
        border-radius: 6px;
        text-decoration: none;
        color: var(--text);
        font-size: .875rem;
        transition: background .15s;
    }}
    .sidebar a:hover {{
        background: var(--primary-light);
        color: var(--primary);
    }}

    /* ── Main ── */
    .main {{
        margin-left: var(--sidebar-w);
        padding: 32px 40px 60px;
        max-width: 960px;
    }}

    .hero {{
        margin-bottom: 36px;
    }}
    .hero h1 {{
        font-size: 2rem;
        margin-bottom: 8px;
    }}
    .hero p {{
        color: var(--text-muted);
        font-size: 1rem;
        max-width: 600px;
    }}

    /* Info cards */
    .info-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-bottom: 40px;
    }}
    .info-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 18px 20px;
    }}
    .info-card h3 {{
        font-size: .85rem;
        text-transform: uppercase;
        letter-spacing: .5px;
        color: var(--text-muted);
        margin-bottom: 8px;
    }}
    .info-card code {{
        background: var(--code-bg);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: .85rem;
    }}
    .role-list {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        list-style: none;
    }}
    .role-list li {{
        background: var(--primary-light);
        color: var(--primary);
        padding: 3px 10px;
        border-radius: 20px;
        font-size: .8rem;
        font-weight: 500;
    }}
    .error-schema pre {{
        background: var(--code-bg);
        padding: 10px 14px;
        border-radius: 6px;
        font-size: .8rem;
        overflow-x: auto;
    }}

    /* ── Sections ── */
    section {{
        margin-bottom: 40px;
    }}
    .section-header {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 4px;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--primary);
    }}
    .section-header h2 {{
        font-size: 1.3rem;
    }}
    .section-prefix {{
        background: var(--code-bg);
        padding: 2px 8px;
        border-radius: 4px;
        font-size: .85rem;
        color: var(--text-muted);
    }}
    .section-desc {{
        color: var(--text-muted);
        margin-bottom: 16px;
        font-size: .9rem;
    }}

    /* ── Endpoint card ── */
    .endpoint-card {{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 14px;
        transition: box-shadow .2s;
    }}
    .endpoint-card:hover {{
        box-shadow: 0 2px 12px rgba(0,0,0,.06);
    }}
    .endpoint-header {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 6px;
    }}
    .method-badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        color: #fff;
        font-weight: 700;
        font-size: .75rem;
        min-width: 60px;
        text-align: center;
        letter-spacing: .3px;
    }}
    .endpoint-path {{
        font-size: .95rem;
        font-weight: 600;
        color: var(--text);
    }}
    .endpoint-desc {{
        color: var(--text-muted);
        font-size: .875rem;
        margin-bottom: 10px;
    }}

    /* Params table */
    .params-block {{ margin-bottom: 10px; }}
    .params-block h4 {{
        font-size: .8rem;
        text-transform: uppercase;
        letter-spacing: .4px;
        color: var(--text-muted);
        margin-bottom: 6px;
    }}
    .params-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: .85rem;
    }}
    .params-table th {{
        text-align: left;
        padding: 6px 8px;
        background: var(--code-bg);
        font-weight: 600;
        font-size: .75rem;
        text-transform: uppercase;
        letter-spacing: .3px;
        color: var(--text-muted);
    }}
    .params-table td {{
        padding: 6px 8px;
        border-bottom: 1px solid var(--border);
        vertical-align: top;
    }}

    .tag {{
        display: inline-block;
        padding: 1px 7px;
        border-radius: 3px;
        font-size: .7rem;
        font-weight: 600;
        margin-right: 4px;
    }}
    .tag.required {{ background: #fee2e2; color: #dc2626; }}
    .tag.optional {{ background: #e0f2fe; color: #0284c7; }}
    .tag.default  {{ background: #f0fdf4; color: #16a34a; }}

    /* Response */
    .response-block {{ margin-bottom: 10px; }}
    .response-block h4 {{
        font-size: .8rem;
        text-transform: uppercase;
        letter-spacing: .4px;
        color: var(--text-muted);
        margin-bottom: 6px;
    }}
    .response-code {{
        background: #dcfce7;
        color: #16a34a;
        padding: 1px 6px;
        border-radius: 3px;
        font-size: .75rem;
        font-weight: 700;
    }}
    .response-block pre {{
        background: #1e293b;
        color: #e2e8f0;
        padding: 14px 18px;
        border-radius: 8px;
        overflow-x: auto;
        font-size: .8rem;
        line-height: 1.5;
    }}

    /* Errors */
    .errors-block h4 {{
        font-size: .8rem;
        text-transform: uppercase;
        letter-spacing: .4px;
        color: var(--text-muted);
        margin-bottom: 4px;
    }}
    .errors-block ul {{
        list-style: none;
        font-size: .85rem;
    }}
    .errors-block li {{
        padding: 3px 0;
    }}
    .error-code {{
        display: inline-block;
        background: #fee2e2;
        color: #dc2626;
        padding: 1px 6px;
        border-radius: 3px;
        font-size: .75rem;
        font-weight: 700;
        margin-right: 6px;
        font-family: monospace;
    }}

    /* ── Responsive ── */
    @media (max-width: 768px) {{
        .sidebar {{ display: none; }}
        .main {{ margin-left: 0; padding: 20px 16px; }}
        .info-grid {{ grid-template-columns: 1fr; }}
    }}
</style>
</head>
<body>

<nav class="sidebar">
    <h1>SafeClaim API</h1>
    <span class="version">v1.0.0</span>
    {nav}
</nav>

<div class="main">
    <div class="hero">
        <h1>SafeClaim API</h1>
        <p>Documentazione completa dell'API REST per la gestione sinistri, utenti e richieste di soccorso stradale.</p>
    </div>

    <div class="info-grid">
        <div class="info-card">
            <h3>Autenticazione</h3>
            <p>Attualmente <strong>mock</strong> (Keycloak in fase di integrazione).<br>
            Login con qualsiasi email in DB e password <code>admin123</code>.</p>
        </div>
        <div class="info-card">
            <h3>Ruoli validi</h3>
            <ul class="role-list">
                <li>admin</li>
                <li>automobilista</li>
                <li>perito</li>
                <li>officina</li>
                <li>assicuratore</li>
                <li>azienda</li>
            </ul>
        </div>
        <div class="info-card">
            <h3>Formato errori</h3>
            <div class="error-schema"><pre>{{"error": "CODICE_ERRORE", "message": "Descrizione"}}</pre></div>
        </div>
        <div class="info-card">
            <h3>Errori globali</h3>
            <ul style="list-style:none; font-size:.85rem;">
                <li><span class="error-code">404</span> Endpoint non trovato</li>
                <li><span class="error-code">405</span> Metodo non consentito</li>
                <li><span class="error-code">500</span> Errore interno</li>
            </ul>
        </div>
    </div>

    {sections_html}
</div>

</body>
</html>"""

    response = make_response(html)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response
