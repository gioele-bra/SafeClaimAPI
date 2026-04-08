from flask import Blueprint, jsonify

bp = Blueprint("documentation", __name__)


@bp.get("/")
def get_documentation():
    """Restituisce la documentazione completa dell'API."""
    docs = {
        "api_name": "SafeClaim API",
        "version": "1.0.0",
        "description": "API REST per la gestione sinistri, utenti e richieste di soccorso stradale.",
        "base_url": "/api",
        "authentication": {
            "type": "mock (Keycloak in fase di integrazione)",
            "description": "Attualmente l'autenticazione e' mock. "
                           "Il login accetta qualsiasi email presente nel DB con password 'admin123'."
        },
        "valid_roles": [
            "admin", "automobilista", "perito",
            "officina", "assicuratore", "azienda"
        ],
        "error_format": {
            "description": "Tutti gli errori seguono questo formato standard",
            "schema": {
                "error": "CODICE_ERRORE",
                "message": "Descrizione leggibile dell'errore"
            },
            "global_errors": {
                "404": {"error": "NOT_FOUND", "message": "Endpoint non trovato"},
                "405": {"error": "METHOD_NOT_ALLOWED", "message": "Metodo non consentito"},
                "500": {"error": "INTERNAL_ERROR", "message": "Errore interno"}
            }
        },
        "sections": [
            # ── Root ──
            {
                "name": "Root",
                "prefix": "/",
                "description": "Endpoint di stato generale dell'API",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/",
                        "description": "Health check generale",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {
                            "name": "SafeClaim API",
                            "status": "ok"
                        }
                    }
                ]
            },
            # ── Common ──
            {
                "name": "Common",
                "prefix": "/api/common",
                "description": "Endpoint comuni di supporto",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/api/common/health",
                        "description": "Health check del servizio",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {"status": "ok"}
                    }
                ]
            },
            # ── Auth ──
            {
                "name": "Autenticazione",
                "prefix": "/api/auth",
                "description": "Endpoint di autenticazione (mock – Keycloak in arrivo)",
                "endpoints": [
                    {
                        "method": "POST",
                        "path": "/api/auth/login",
                        "description": "Login utente (mock). Accetta qualsiasi email in DB con password 'admin123'.",
                        "request_body": {
                            "email": {"type": "string", "required": True, "description": "Email dell'utente"},
                            "password": {"type": "string", "required": True, "description": "Password dell'utente"}
                        },
                        "query_params": None,
                        "response_example": {
                            "message": "Login OK (mock)",
                            "user": {
                                "id": 1,
                                "nome": "Mario",
                                "cognome": "Rossi",
                                "email": "mario@example.com",
                                "ruolo": ["automobilista"]
                            }
                        },
                        "errors": {
                            "400": "email e password obbligatori",
                            "401": "Credenziali non valide"
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/api/auth/status",
                        "description": "Stato del provider di autenticazione",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {
                            "message": "Autenticazione gestita da Keycloak (mock attivo)",
                            "provider": "mock"
                        }
                    }
                ]
            },
            # ── Admin ──
            {
                "name": "Admin – Gestione Utenti",
                "prefix": "/api/admin",
                "description": "CRUD utenti lato amministrativo",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/api/admin/",
                        "description": "Lista tutti gli utenti",
                        "request_body": None,
                        "query_params": None,
                        "response_example": [
                            {
                                "id": 1, "nome": "Mario", "cognome": "Rossi",
                                "email": "mario@example.com", "telefono": "3331234567",
                                "ruolo": ["automobilista"], "data_registrazione": "2025-01-01T00:00:00"
                            }
                        ]
                    },
                    {
                        "method": "GET",
                        "path": "/api/admin/count",
                        "description": "Numero totale utenti",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {"total_users": 42}
                    },
                    {
                        "method": "GET",
                        "path": "/api/admin/roles-report",
                        "description": "Report conteggio utenti per ruolo",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {
                            "status": "success",
                            "roles_count": {"automobilista": 20, "perito": 5, "admin": 2}
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/api/admin/<user_id>",
                        "description": "Dettaglio singolo utente per ID",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {
                            "id": 1, "nome": "Mario", "cognome": "Rossi",
                            "email": "mario@example.com", "telefono": "3331234567",
                            "ruolo": ["automobilista"], "data_registrazione": "2025-01-01T00:00:00"
                        },
                        "errors": {"404": "Utente non trovato"}
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
                            "ruolo": {"type": "string", "required": False, "default": "automobilista"}
                        },
                        "query_params": None,
                        "response_code": 201,
                        "errors": {
                            "400": "Campi obbligatori mancanti / Email gia' registrata"
                        }
                    },
                    {
                        "method": "PUT",
                        "path": "/api/admin/<user_id>",
                        "description": "Aggiorna dati utente (nome, cognome, email, telefono)",
                        "request_body": {
                            "nome": {"type": "string", "required": False},
                            "cognome": {"type": "string", "required": False},
                            "email": {"type": "string", "required": False},
                            "telefono": {"type": "string", "required": False}
                        },
                        "query_params": None,
                        "errors": {
                            "400": "Nessun campo da aggiornare",
                            "404": "Utente non trovato"
                        }
                    },
                    {
                        "method": "DELETE",
                        "path": "/api/admin/<user_id>",
                        "description": "Elimina utente per ID",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {"message": "Utente 1 eliminato con successo"},
                        "errors": {"404": "Utente non trovato"}
                    }
                ]
            },
            # ── Creazione Utenti ──
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
                            "ruolo": {
                                "type": "string | array",
                                "required": False,
                                "default": "automobilista",
                                "description": "Uno o piu' ruoli separati da virgola oppure array. "
                                               "Valori ammessi: admin, automobilista, perito, officina, assicuratore, azienda"
                            }
                        },
                        "query_params": None,
                        "response_code": 201,
                        "response_example": {
                            "message": "Utente creato con successo",
                            "user": {
                                "id": 1, "nome": "Mario", "cognome": "Rossi",
                                "email": "mario@example.com", "ruolo": ["automobilista"]
                            }
                        },
                        "errors": {
                            "400": "Campi obbligatori mancanti / Formato email non valido / "
                                   "Ruoli non riconosciuti / Email gia' registrata"
                        }
                    }
                ]
            },
            # ── Gestione Utenti ──
            {
                "name": "Gestione Utenti",
                "prefix": "/api/gestioneUtenti",
                "description": "CRUD e ricerca utenti",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/api/gestioneUtenti/utenti",
                        "description": "Lista tutti gli utenti",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {
                            "utenti": [
                                {
                                    "id": 1, "nome": "Mario", "cognome": "Rossi",
                                    "email": "mario@example.com", "telefono": "3331234567",
                                    "ruolo": ["automobilista"], "data_registrazione": "2025-01-01T00:00:00"
                                }
                            ]
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/api/gestioneUtenti/utenti/count",
                        "description": "Numero totale utenti",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {"totale_utenti": 42}
                    },
                    {
                        "method": "GET",
                        "path": "/api/gestioneUtenti/utenti/ruoli",
                        "description": "Lista ruoli attualmente in uso nel sistema",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {"ruoli_attivi": ["admin", "automobilista", "perito"]}
                    },
                    {
                        "method": "GET",
                        "path": "/api/gestioneUtenti/utenti/cerca",
                        "description": "Cerca utenti per nome, cognome o email (ricerca parziale)",
                        "request_body": None,
                        "query_params": {
                            "q": {"type": "string", "required": True, "description": "Termine di ricerca"}
                        },
                        "response_example": {
                            "utenti_trovati": [
                                {
                                    "id": 1, "nome": "Mario", "cognome": "Rossi",
                                    "email": "mario@example.com", "telefono": "3331234567",
                                    "ruolo": ["automobilista"], "data_registrazione": "2025-01-01T00:00:00"
                                }
                            ]
                        },
                        "errors": {"400": "parametro 'q' obbligatorio"}
                    },
                    {
                        "method": "GET",
                        "path": "/api/gestioneUtenti/utenti/<user_id>",
                        "description": "Dettaglio singolo utente per ID",
                        "request_body": None,
                        "query_params": None,
                        "errors": {"404": "UTENTE_NON_TROVATO"}
                    },
                    {
                        "method": "PUT",
                        "path": "/api/gestioneUtenti/utenti/<user_id>",
                        "description": "Modifica dati utente (nome, cognome, email, telefono)",
                        "request_body": {
                            "nome": {"type": "string", "required": False},
                            "cognome": {"type": "string", "required": False},
                            "email": {"type": "string", "required": False},
                            "telefono": {"type": "string", "required": False}
                        },
                        "query_params": None,
                        "response_example": {
                            "message": "Utente aggiornato",
                            "utente": {
                                "id": 1, "nome": "Mario", "cognome": "Rossi",
                                "email": "mario@example.com", "telefono": "3331234567",
                                "ruolo": ["automobilista"], "data_registrazione": "2025-01-01T00:00:00"
                            }
                        },
                        "errors": {
                            "400": "Nessun campo da aggiornare",
                            "404": "Utente non trovato"
                        }
                    },
                    {
                        "method": "DELETE",
                        "path": "/api/gestioneUtenti/utenti/<user_id>",
                        "description": "Elimina utente per ID",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {"message": "Utente 1 eliminato con successo"},
                        "errors": {"404": "Utente non trovato"}
                    }
                ]
            },
            # ── Soccorsi ──
            {
                "name": "Soccorsi",
                "prefix": "/api/soccorsi",
                "description": "Richieste di soccorso stradale",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/api/soccorsi/",
                        "description": "Lista tutte le richieste di soccorso (ordinate per data decrescente)",
                        "request_body": None,
                        "query_params": None,
                        "response_example": {
                            "count": 1,
                            "data": [
                                {
                                    "id": 1, "data_richiesta": "2025-06-01T10:30:00",
                                    "orario_arrivo": "2025-06-01T11:00:00"
                                }
                            ]
                        }
                    },
                    {
                        "method": "GET",
                        "path": "/api/soccorsi/<soccorso_id>",
                        "description": "Dettaglio singola richiesta di soccorso",
                        "request_body": None,
                        "query_params": None,
                        "errors": {"404": "Richiesta non trovata"}
                    }
                ]
            },
            # ── Richieste ──
            {
                "name": "Richieste",
                "prefix": "/api/richieste",
                "description": "Gestione richieste con filtro per stato",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/api/richieste/",
                        "description": "Lista richieste, con filtro opzionale per stato",
                        "request_body": None,
                        "query_params": {
                            "status": {
                                "type": "string",
                                "required": False,
                                "description": "Filtra per stato. Valori ammessi: in_attesa, assegnata, in_corso, completata, annullata"
                            }
                        },
                        "response_example": {
                            "success": True,
                            "count": 1,
                            "data": [
                                {
                                    "id": 1, "data_richiesta": "2025-06-01T10:30:00",
                                    "orario_arrivo": "2025-06-01T11:00:00"
                                }
                            ]
                        },
                        "errors": {"400": "Stato non valido"}
                    },
                    {
                        "method": "GET",
                        "path": "/api/richieste/<richiesta_id>",
                        "description": "Dettaglio singola richiesta per ID",
                        "request_body": None,
                        "query_params": None,
                        "errors": {"404": "Richiesta non trovata"}
                    }
                ]
            },
            # ── Documentazione ──
            {
                "name": "Documentazione",
                "prefix": "/documentation",
                "description": "Questo endpoint",
                "endpoints": [
                    {
                        "method": "GET",
                        "path": "/documentation",
                        "description": "Restituisce la documentazione completa dell'API",
                        "request_body": None,
                        "query_params": None
                    }
                ]
            }
        ]
    }

    return jsonify(docs), 200
