# SafeClaimAPI

API backend basato su Flask per gestire utenti, autenticazione e servizi.

## Configurazione locale

1. Copiare `.env.example` in `.env`:
   ```bash
   cp .env.example .env
   ```
2. Modificare i valori all'interno del file `.env` con le credenziali del DB.
3. Assicurarsi che `.env` sia incluso in `.gitignore` (già configurato).

## Requisiti
```bash
pip install -r requirements.txt
```

## Avviare l'app
```bash
python run.py
```

Le rotte MongoDB sono esposte sotto `/api/mongo`.

## Esempio test
```bash
pytest -q
```

## RICHIESTE API GESTIONE UTENTI

<img width="743" height="315" alt="Screenshot 2026-03-11 084331" src="https://github.com/user-attachments/assets/1879c135-dc49-4e63-a4f7-1f5fbd630495" />

## Integrazione Keycloak

L'endpoint `POST /api/creazioneUtenti/users` crea l'utente prima su
Keycloak (source of truth dell'identita') e poi su MySQL, salvando
l'id Keycloak nella colonna `Utente.keycloak_id`. In caso di errore
lato MySQL viene eseguito un rollback compensativo eliminando l'utente
da Keycloak.

### Variabili d'ambiente

| Variabile | Default | Note |
| --- | --- | --- |
| `KC_BASE_URL` | `https://keycloak.giobra.com` | URL base di Keycloak |
| `KC_REALM` | `safeClaim` | Nome del realm |
| `KC_ADMIN_CLIENT_ID` | — | Client ID del client confidenziale per l'Admin API |
| `KC_ADMIN_CLIENT_SECRET` | — | Secret del client |

### Setup lato Keycloak (passi manuali)

1. Nel realm `safeClaim` creare un **client confidenziale** con
   *Client authentication* ON e *Service accounts roles* ON.
2. Nel tab "Service account roles" del client assegnare i client roles
   di `realm-management`:
   - `manage-users`
   - `view-users`
   - `query-users`
   - `view-realm`
3. Pre-creare i **realm roles** corrispondenti ai ruoli applicativi:
   `admin`, `automobilista`, `perito`, `officina`, `assicuratore`,
   `soccorso`, `azienda`. Se uno di questi manca al momento della
   creazione l'API logga un warning e prosegue senza assegnarlo.
4. Copiare client ID e secret nel file `.env`
   (`KC_ADMIN_CLIENT_ID`, `KC_ADMIN_CLIENT_SECRET`).

### Migrazione DB

Eseguire una volta sola sul DB MySQL prima di usare l'endpoint:

```sql
ALTER TABLE Utente
  ADD COLUMN keycloak_id VARCHAR(36) NULL UNIQUE AFTER password_hash;
```
