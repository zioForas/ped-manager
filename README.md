<div align="center">

# 🗓 PED Manager

### Piano Editoriale Digitale — gestione social automatizzata con AI

*Dalla generazione dei contenuti alla pubblicazione, con l'approvazione del cliente nel mezzo.*

<br>

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![AI](https://img.shields.io/badge/AI-Groq%20%C2%B7%20Gemini%20%C2%B7%20Cerebras-F55036?logo=googlegemini&logoColor=white)
![Meta](https://img.shields.io/badge/API-Meta%20Graph-0866FF?logo=meta&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-22c55e)

</div>

---

## 📖 Cos'è

**PED Manager** è una piattaforma web **white-label** che automatizza l'intero ciclo di gestione dei social media per i clienti di un'agenzia. L'AI genera i contenuti, il cliente li approva via email, il sistema li pubblica su Facebook e Instagram — il tutto da un unico pannello, senza una riga di codice per chi lo usa.

Ogni cliente è una cartella in `clienti/<slug>/` con la sua `strategia.json` (tono, argomenti, sedi, hashtag, brand). Aggiungere un cliente = aggiungere una cartella.

---

## ✨ Funzionalità

| | Funzione | Descrizione |
|---|---|---|
| 🤖 | **Generazione AI** | Post e storie del mese (testi, hashtag, orari) nello stile del cliente |
| 📄 | **PDF del piano** | Documento professionale del piano editoriale, pronto da inviare |
| 📧 | **Invio al cliente** | Email automatica con i pulsanti *Approva* / *Richiedi modifiche* |
| ✅ | **Approvazione** | Pagine pubbliche di risposta; lo stato torna automaticamente nel pannello |
| 🔁 | **Modifiche con AI** | Se il cliente chiede cambiamenti, l'AI rigenera i testi seguendo le note |
| 💬 | **Assistente AI in chat** | Comandi in linguaggio naturale, 3 modalità (guida / azioni sicure / esegui) |
| 🔀 | **Switch modello AI** | Più modelli con **fallback automatico** + indicatore di disponibilità |
| 🖼 | **Media automatici** | Scarica le foto da Google Drive e le classifica per argomento con AI vision |
| 📲 | **Pubblicazione Meta** | Post su Facebook e Instagram via Graph API |
| 🎨 | **White-label** | Un colore `--brand` per cliente; tema chiaro/scuro automatico |
| 🔐 | **Login protetto** | Account condiviso, auto-login, anti brute-force + honeypot |

---

## 🔄 Come funziona

```
  ┌───────────┐   ┌────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────────┐
  │ 1. Genera │ → │ 2. PDF │ → │ 3. Email al  │ → │ 4. Approva/ │ → │ 5. Pubblica  │
  │   con AI  │   │  piano │   │   cliente    │   │  Modifiche  │   │  FB + IG     │
  └───────────┘   └────────┘   └──────────────┘   └─────────────┘   └──────────────┘
```

---

## 🧠 Modelli AI

Modulo centralizzato ([`agente/ai.py`](agente/ai.py)) con **fallback automatico**: se il modello selezionato esaurisce il limite, passa da solo al successivo. Provider supportati: **Cerebras**, **Groq**, **OpenRouter**, **Google Gemini**.

---

## 🛠 Stack

| Componente | Tecnologia |
|---|---|
| Backend / Web UI | **Flask** (Python 3.13), Gunicorn |
| Frontend | **React + Vite** (white-label, glass UI) |
| AI testi / vision | Groq · Gemini · Cerebras · OpenRouter |
| Email | **Brevo** HTTP API |
| Social | **Meta Graph API** (Facebook + Instagram) |
| Media | **Google Drive API** (service account) |
| PDF | fpdf2 |

---

## 📁 Struttura

```
ped-manager/
├── agente/                  # logica core
│   ├── ai.py                # registry modelli AI + fallback
│   ├── copywriter.py        # generazione post
│   ├── stories.py           # generazione storie
│   ├── genera_pdf.py        # PDF piano editoriale
│   ├── mailer.py            # invio email (Brevo)
│   ├── media_finder.py      # download + classificazione media da Drive
│   ├── meta_poster.py       # pubblicazione FB + IG
│   └── main.py              # orchestratore workflow
├── webapp/
│   ├── app.py               # web app Flask (pagine + API + chat + login)
│   └── templates/           # index.html, cliente.html
├── frontend/                # SPA React (build → /app)
├── clienti/<slug>/          # strategia.json per cliente
├── output/                  # JSON, PDF e media generati (non versionati)
├── Procfile                 # gunicorn
├── requirements.txt
├── .env.example             # template variabili d'ambiente
└── DEPLOY.md                # guida deploy
```

---

## 💻 Sviluppo locale

```bash
# 1. backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # poi compila le chiavi

# 2. frontend (opzionale, per ricostruire la SPA /app)
cd frontend && pnpm install && pnpm build && cd ..

# 3. avvia
python webapp/app.py          # → http://localhost:7777
```

Aggiungere un cliente: crea `clienti/<slug>/strategia.json` (parti da `clienti/example/`).

---

## 🚀 Deploy

Pronto per qualsiasi host che supporti `requirements.txt` + `Procfile` (Railway, Render, Fly, …). Tutte le credenziali sono **variabili d'ambiente**, mai nel repo. Guida in [`DEPLOY.md`](DEPLOY.md).

---

## 📄 Licenza

MIT.

