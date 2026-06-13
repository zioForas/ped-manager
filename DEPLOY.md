# Deploy

L'app è un singolo servizio Flask servito da Gunicorn (`Procfile`). Funziona su qualsiasi
host PaaS che rilevi `requirements.txt` + `Procfile` (Railway, Render, Fly.io, …).

## 1. Build
L'host installa le dipendenze da `requirements.txt` e avvia il comando del `Procfile`:

```
web: gunicorn -w 2 -b 0.0.0.0:$PORT --chdir webapp app:app --timeout 300
```

Per la SPA React (`/app`), builda il frontend prima del deploy:

```bash
cd frontend && pnpm install && pnpm build
```

## 2. Volume persistente (opzionale)
Per conservare i file generati (PED, media, PDF) tra un deploy e l'altro, monta un volume
persistente su `/app/output`.

## 3. Variabili d'ambiente
Copia le chiavi da `.env.example` nella dashboard dell'host. Le principali:

```
APP_USERNAME / APP_PASSWORD / APP_SECRET_KEY   # accesso al pannello
PUBLIC_BASE_URL                                # URL pubblico (link nelle email)
GROQ_API_KEY / GEMINI_API_KEY / ...            # provider AI (almeno uno)
BREVO_API_KEY / BREVO_SENDER                   # invio email
META_ACCESS_TOKEN / META_PAGE_ID_FB / ...      # pubblicazione social
GOOGLE_DRIVE_FOLDER_ID / GOOGLE_CREDENTIALS_PATH
```

### Credenziale Google Drive (service account)
Il file JSON del service account **non va nel repo**. In produzione passalo come variabile
`GOOGLE_SERVICE_ACCOUNT_JSON` (tutto il contenuto del JSON): all'avvio l'app lo scrive sul
path indicato da `GOOGLE_CREDENTIALS_PATH` (vedi `_bootstrap_credenziali_da_env()` in
`webapp/app.py`).

## 4. URL pubblico
`PUBLIC_BASE_URL` deve puntare all'URL pubblico assegnato dall'host: serve a generare i
link "Approva / Richiedi modifiche" nelle email al cliente.

## Note
- Le pagine `/approva`, `/modifiche`, `/stato/<token>` sono servite dallo stesso processo
  della webapp — non serve un secondo server né un tunnel.
- Cambiare provider AI = aggiornare le variabili d'ambiente; il codice resta invariato.
