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
