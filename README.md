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
