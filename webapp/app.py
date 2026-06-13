import hmac
import json
import os
import secrets as _secrets
import sys
import threading
import time as _time
from datetime import datetime, timedelta
from flask import (Flask, render_template, render_template_string, request,
                   jsonify, send_file, session, redirect, url_for)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agente'))

from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

app = Flask(__name__)
BASE = os.path.join(os.path.dirname(__file__), '..')

# ── Sicurezza sessione / login ──
app.secret_key = os.getenv("APP_SECRET_KEY") or _secrets.token_hex(32)
app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),   # "ricordami" → auto-login 30 giorni
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    # cookie solo-HTTPS in cloud (PUBLIC_BASE_URL impostata); in locale resta off
    SESSION_COOKIE_SECURE=bool(os.getenv("PUBLIC_BASE_URL")),
)

AUTH_USER = os.getenv("APP_USERNAME", "admin")
AUTH_PASS = os.getenv("APP_PASSWORD", "")
# pagine pubbliche: login/logout, healthcheck e le pagine di approvazione del
# cliente (aperte dal link nella mail, senza login)
_PUBLIC_PREFIXES = ("/login", "/logout", "/ping", "/approva", "/modifiche", "/stato")
_login_attempts = {}  # ip -> [timestamp dei tentativi falliti] (anti brute-force)


def _client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd else (request.remote_addr or "?"))


def _troppi_tentativi(ip):
    now = _time.time()
    arr = [t for t in _login_attempts.get(ip, []) if now - t < 900]  # finestra 15 min
    _login_attempts[ip] = arr
    return len(arr) >= 5


def _registra_fallimento(ip):
    _login_attempts.setdefault(ip, []).append(_time.time())


# API di autenticazione usate dalla SPA (sempre pubbliche)
_PUBLIC_API = ("/api/login", "/api/me", "/api/logout")
# shell della nuova UI React (servita pubblicamente: l'auth la gestisce il client)
_SPA_PREFIX = "/app"


@app.before_request
def _require_login():
    p = request.path
    if p.startswith("/static") or any(p == x or p.startswith(x) for x in _PUBLIC_PREFIXES):
        return
    if p in _PUBLIC_API or p == _SPA_PREFIX or p.startswith(_SPA_PREFIX + "/"):
        return
    if not session.get("auth"):
        if p.startswith("/api/"):
            return jsonify({"errore": "Non autenticato"}), 401
        return redirect(url_for("login"))


HTML_LOGIN = """
<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PED Manager — Accesso</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0;}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    background:radial-gradient(1000px 600px at 70% -10%,rgba(124,92,255,.18),transparent 60%),
               radial-gradient(800px 500px at -10% 20%,rgba(91,141,239,.16),transparent 55%),#0b0d13;
    color:#e6e9f0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;}
  .card{background:linear-gradient(180deg,#171b27,#12151f);border:1px solid #252a38;border-radius:20px;
    padding:40px 36px;width:400px;max-width:95vw;box-shadow:0 30px 80px rgba(0,0,0,.55);}
  .brand{font-size:24px;font-weight:900;background:linear-gradient(135deg,#5b8def,#7c5cff);
    -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:.3px;}
  .sub{color:#8a91a3;font-size:13px;margin:6px 0 26px;}
  label{display:block;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#6a7186;margin:0 0 7px 2px;}
  .inp{width:100%;background:#0e121b;border:1px solid #252a38;border-radius:11px;color:#e6e9f0;
    padding:13px 14px;font-size:14px;font-family:inherit;margin-bottom:18px;transition:.15s;}
  .inp:focus{outline:none;border-color:#5b8def;box-shadow:0 0 0 3px rgba(91,141,239,.18);}
  .row{display:flex;align-items:center;gap:9px;margin-bottom:22px;color:#aab1c2;font-size:13px;}
  .row input{width:17px;height:17px;accent-color:#5b8def;}
  .btn{width:100%;background:linear-gradient(135deg,#5b8def,#3f6fe0);border:none;border-radius:11px;
    color:#fff;font-weight:800;font-size:15px;padding:14px;cursor:pointer;box-shadow:0 8px 24px rgba(63,111,224,.4);
    transition:.15s;letter-spacing:.2px;}
  .btn:hover{filter:brightness(1.07);}
  .err{background:#2a0f12;border:1px solid #7c2d2d;color:#fca5a5;border-radius:10px;
    padding:11px 13px;font-size:13px;margin-bottom:18px;}
  .hp{position:absolute;left:-9999px;top:-9999px;opacity:0;height:0;width:0;}
  .foot{text-align:center;color:#4a5266;font-size:11px;margin-top:22px;}
</style></head>
<body>
  <form class="card" method="POST" autocomplete="off">
    <div class="brand">PED Manager</div>
    <div class="sub">Accesso riservato</div>
    {% if error %}<div class="err">⚠ {{ error }}</div>{% endif %}
    <label>Username</label>
    <input class="inp" type="text" name="username" autofocus required>
    <label>Password</label>
    <input class="inp" type="password" name="password" required>
    <!-- honeypot anti-bot: invisibile, gli umani lo lasciano vuoto -->
    <input class="hp" type="text" name="website" tabindex="-1" autocomplete="off">
    <div class="row"><input type="checkbox" name="ricordami" id="r" checked>
      <label for="r" style="margin:0;text-transform:none;letter-spacing:0;font-size:13px;color:#aab1c2;">Resta connesso su questo dispositivo</label></div>
    <button class="btn" type="submit">Accedi →</button>
    <div class="foot">Connessione protetta · uso interno</div>
  </form>
</body></html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("auth"):
        return redirect("/")
    error = ""
    if request.method == "POST":
        ip = _client_ip()
        if _troppi_tentativi(ip):
            error = "Troppi tentativi falliti. Riprova tra qualche minuto."
        else:
            u = request.form.get("username", "")
            pw = request.form.get("password", "")
            honey = request.form.get("website", "")  # honeypot: deve essere vuoto
            ok = (not honey) and AUTH_PASS \
                and hmac.compare_digest(u, AUTH_USER) \
                and hmac.compare_digest(pw, AUTH_PASS)
            if ok:
                session["auth"] = True
                session.permanent = bool(request.form.get("ricordami"))
                return redirect("/")
            _registra_fallimento(ip)
            _time.sleep(1.2)  # rallenta il brute-force
            error = "Username o password non validi."
    return render_template_string(HTML_LOGIN, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ────────────────────────────── NUOVA UI (SPA React su /app) ──────────────────────────────
SPA_DIR = os.path.join(os.path.dirname(__file__), 'static', 'spa')


def _serve_spa():
    idx = os.path.join(SPA_DIR, 'index.html')
    if not os.path.exists(idx):
        return "Nuova UI non ancora compilata (esegui: cd frontend && pnpm build).", 503
    return send_file(idx)


@app.route("/app")
@app.route("/app/")
@app.route("/app/<path:_sub>")
def spa(_sub=None):
    return _serve_spa()


# ── API di autenticazione per la SPA ──
@app.route("/api/me")
def api_me():
    if session.get("auth"):
        return jsonify({"auth": True, "username": AUTH_USER})
    return jsonify({"auth": False})


@app.route("/api/login", methods=["POST"])
def api_login():
    ip = _client_ip()
    if _troppi_tentativi(ip):
        return jsonify({"ok": False, "errore": "Troppi tentativi. Riprova tra qualche minuto."})
    d = request.json or {}
    u, pw = d.get("username", ""), d.get("password", "")
    ok = AUTH_PASS and hmac.compare_digest(u, AUTH_USER) and hmac.compare_digest(pw, AUTH_PASS)
    if ok:
        session["auth"] = True
        session.permanent = bool(d.get("ricordami"))
        return jsonify({"ok": True, "username": AUTH_USER})
    _registra_fallimento(ip)
    _time.sleep(1.0)
    return jsonify({"ok": False, "errore": "Username o password non validi."})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok": True})


def _bootstrap_credenziali_da_env():
    """Su hosting cloud le credenziali Google non possono stare nel repo:
    se GOOGLE_SERVICE_ACCOUNT_JSON è valorizzata, scrive il file al path
    indicato da GOOGLE_CREDENTIALS_PATH (se non esiste già)."""
    contenuto = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")
    if contenuto and path and not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(contenuto)


_bootstrap_credenziali_da_env()


# Versione del seed: bumpala quando aggiorni i contenuti base in seed/ per forzare
# il re-seed sul volume persistente (altrimenti i vecchi file resterebbero).
SEED_VERSION = "2025-06-07-copy-fb-designs"


def _bootstrap_seed():
    """Ripristina i contenuti base in output/ dal seed/.
    Su volume persistente (vuoto al primo avvio) i file dell'immagine sono nascosti:
    li ri-seminiamo. Inoltre, se SEED_VERSION è cambiata, ri-semina (sovrascrive)
    i contenuti base — utile quando aggiorniamo i testi. NON tocca sessioni.json
    (non è nel seed), quindi i token di approvazione restano intatti."""
    import shutil
    seed_dir = os.path.join(BASE, 'seed')
    out_dir = os.path.join(BASE, 'output')
    if not os.path.isdir(seed_dir):
        return
    os.makedirs(out_dir, exist_ok=True)
    ver_file = os.path.join(out_dir, '.seed_version')
    cur = ''
    try:
        with open(ver_file) as f:
            cur = f.read().strip()
    except Exception:
        pass
    forza = cur != SEED_VERSION
    # copia ricorsiva: replica la struttura di seed/ (inclusi i design) in output/
    for root, _dirs, files in os.walk(seed_dir):
        rel = os.path.relpath(root, seed_dir)
        dst_root = out_dir if rel == '.' else os.path.join(out_dir, rel)
        os.makedirs(dst_root, exist_ok=True)
        for nome in files:
            dst = os.path.join(dst_root, nome)
            if forza or not os.path.exists(dst):
                try:
                    shutil.copy2(os.path.join(root, nome), dst)
                except Exception:
                    pass
    if forza:
        try:
            with open(ver_file, 'w') as f:
                f.write(SEED_VERSION)
        except Exception:
            pass


_bootstrap_seed()


def output_path(cliente, tipo, mesi, anno):
    m1, m2 = mesi[0].lower(), mesi[-1].lower()
    paths = {
        "ped":      f'ped_{cliente}_{m1}_{m2}_{anno}.json',
        "stories":  f'stories_{cliente}_{m1}_{m2}_{anno}.json',
        "pdf":      f'PED_{cliente}_{mesi[0]}_{mesi[-1]}_{anno}.pdf',
        "sessioni": 'sessioni.json',
        "meta":     f'meta_report_{cliente}_{m1}_{m2}_{anno}.json',
    }
    return os.path.join(BASE, 'output', paths[tipo])


def carica_strategia(cliente):
    with open(os.path.join(BASE, 'clienti', cliente, 'strategia.json')) as f:
        return json.load(f)


def lista_clienti():
    clienti_dir = os.path.join(BASE, 'clienti')
    return [d for d in os.listdir(clienti_dir)
            if os.path.isdir(os.path.join(clienti_dir, d))
            and os.path.exists(os.path.join(clienti_dir, d, 'strategia.json'))]


def stato_sessione(cliente, mesi, anno):
    path = output_path(cliente, "sessioni", mesi, anno)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        sessioni = json.load(f)
    for token, s in reversed(list(sessioni.items())):
        if cliente in s.get("pdf_path", ""):
            return s
    return None


# ────────────────────────────── PAGINE ──────────────────────────────

@app.route("/")
def index():
    clienti = lista_clienti()
    dati = []
    for c in clienti:
        try:
            s = carica_strategia(c)
            mesi, anno = s["mesi"], s["anno"]
            sessione = stato_sessione(c, mesi, anno)

            # controlla se schedulato su Meta
            meta_path = output_path(c, "meta", mesi, anno)
            meta_ok = os.path.exists(meta_path)

            stato = "schedulato" if meta_ok else (
                sessione.get("stato", "in_attesa") if sessione else "non_inviato"
            )
            dati.append({
                "id": c, "nome": s["cliente"],
                "periodo": f"{mesi[0]} - {mesi[-1]} {anno}",
                "ped_exists": os.path.exists(output_path(c, "ped", mesi, anno)),
                "pdf_exists": os.path.exists(output_path(c, "pdf", mesi, anno)),
                "stato": stato
            })
        except Exception:
            pass
    return render_template("index.html", clienti=dati)


@app.route("/cliente/<cliente>")
def cliente_view(cliente):
    s = carica_strategia(cliente)
    mesi, anno = s["mesi"], s["anno"]
    ped, stories = [], []
    try:
        with open(output_path(cliente, "ped", mesi, anno)) as f:
            ped = json.load(f)
    except Exception:
        pass

    # arricchisce con il path del design (immagine scelta) se già generato
    try:
        design_path_file = os.path.join(BASE, "output", f"ped_{cliente}_con_design.json")
        with open(design_path_file) as f:
            ped_con_design = json.load(f)
        designs_per_numero = {p["numero"]: p.get("design_path", "") for p in ped_con_design}
        for post in ped:
            dp = designs_per_numero.get(post["numero"], "")
            if dp:
                post["design_url"] = f"/design/{cliente}/{os.path.basename(dp)}"
    except Exception:
        pass
    try:
        with open(output_path(cliente, "stories", mesi, anno)) as f:
            stories = json.load(f)
        for story in stories:
            mp = story.get("media_path", "")
            if mp:
                story["media_url"] = f"/story-media/{cliente}/{mp}"
    except Exception:
        pass
    sessione = stato_sessione(cliente, mesi, anno)
    return render_template("cliente.html",
        cliente=cliente, strategia=s, ped=ped, stories=stories,
        sessione=sessione, periodo=f"{mesi[0]} - {mesi[-1]} {anno}",
        env_meta_token=os.getenv("META_ACCESS_TOKEN", ""),
        env_page_id=os.getenv("META_PAGE_ID_FB", ""),
        env_ig_id=os.getenv("META_INSTAGRAM_ACCOUNT_ID", ""))


# ── Dati JSON per la SPA ──
@app.route("/api/clienti")
def api_clienti():
    dati = []
    for c in lista_clienti():
        try:
            s = carica_strategia(c)
            mesi, anno = s["mesi"], s["anno"]
            sessione = stato_sessione(c, mesi, anno)
            meta_ok = os.path.exists(output_path(c, "meta", mesi, anno))
            stato = "schedulato" if meta_ok else (sessione.get("stato", "in_attesa") if sessione else "non_inviato")
            dati.append({
                "id": c, "nome": s["cliente"],
                "periodo": f"{mesi[0]} - {mesi[-1]} {anno}",
                "ped_exists": os.path.exists(output_path(c, "ped", mesi, anno)),
                "pdf_exists": os.path.exists(output_path(c, "pdf", mesi, anno)),
                "stato": stato,
            })
        except Exception:
            pass
    return jsonify({"clienti": dati})


@app.route("/api/cliente/<cliente>")
def api_cliente(cliente):
    try:
        s = carica_strategia(cliente)
    except Exception:
        return jsonify({"errore": "Cliente non trovato"}), 404
    mesi, anno = s["mesi"], s["anno"]
    ped, stories = [], []
    try:
        with open(output_path(cliente, "ped", mesi, anno)) as f:
            ped = json.load(f)
    except Exception:
        pass
    try:
        with open(os.path.join(BASE, "output", f"ped_{cliente}_con_design.json")) as f:
            ped_con_design = json.load(f)
        d_per_num = {p["numero"]: p.get("design_path", "") for p in ped_con_design}
        for post in ped:
            dp = d_per_num.get(post["numero"], "")
            if dp:
                post["design_url"] = f"/design/{cliente}/{os.path.basename(dp)}"
    except Exception:
        pass
    try:
        with open(output_path(cliente, "stories", mesi, anno)) as f:
            stories = json.load(f)
        for story in stories:
            if story.get("media_path"):
                story["media_url"] = f"/story-media/{cliente}/{story['media_path']}"
    except Exception:
        pass
    return jsonify({
        "strategia": s, "ped": ped, "stories": stories,
        "sessione": stato_sessione(cliente, mesi, anno),
        "periodo": f"{mesi[0]} - {mesi[-1]} {anno}",
        "meta": {
            "page_id": os.getenv("META_PAGE_ID_FB", ""),
            "ig_id": os.getenv("META_INSTAGRAM_ACCOUNT_ID", ""),
        },
    })


# ────────────────────────────── API CONTENUTI ──────────────────────────────

@app.route("/api/post/<cliente>/<int:numero>", methods=["GET", "PUT"])
def api_post(cliente, numero):
    s = carica_strategia(cliente)
    path = output_path(cliente, "ped", s["mesi"], s["anno"])
    with open(path) as f:
        ped = json.load(f)
    post = next((p for p in ped if p["numero"] == numero), None)
    if not post:
        return jsonify({"errore": "non trovato"}), 404
    if request.method == "PUT":
        for k in ["caption", "hashtag", "nota_grafica", "orario"]:
            if k in request.json:
                post[k] = request.json[k]
        post["modificato_manualmente"] = True
        with open(path, 'w') as f:
            json.dump(ped, f, ensure_ascii=False, indent=2)
    return jsonify(post)


@app.route("/api/story/<cliente>/<int:numero>", methods=["GET", "PUT"])
def api_story(cliente, numero):
    s = carica_strategia(cliente)
    path = output_path(cliente, "stories", s["mesi"], s["anno"])
    with open(path) as f:
        stories = json.load(f)
    story = next((x for x in stories if x["numero"] == numero), None)
    if not story:
        return jsonify({"errore": "non trovata"}), 404
    if request.method == "PUT":
        for k in ["testo", "musica_suggerita", "nota_grafica"]:
            if k in request.json:
                story[k] = request.json[k]
        story["modificato_manualmente"] = True
        with open(path, 'w') as f:
            json.dump(stories, f, ensure_ascii=False, indent=2)
    return jsonify(story)


ESTENSIONI_IMMAGINE = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@app.route("/api/story/<cliente>/<int:numero>/media", methods=["POST"])
def api_story_media(cliente, numero):
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"errore": "nessun file ricevuto"}), 400
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ESTENSIONI_IMMAGINE:
        return jsonify({"errore": "formato immagine non supportato"}), 400

    s = carica_strategia(cliente)
    path = output_path(cliente, "stories", s["mesi"], s["anno"])
    with open(path) as f:
        stories = json.load(f)
    story = next((x for x in stories if x["numero"] == numero), None)
    if not story:
        return jsonify({"errore": "non trovata"}), 404

    upload_dir = os.path.join(BASE, "output", "media", cliente, "stories_upload")
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"story_{numero}{ext}"
    file.save(os.path.join(upload_dir, filename))

    story["media_path"] = filename
    story["modificato_manualmente"] = True
    with open(path, 'w') as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "media_url": f"/story-media/{cliente}/{filename}"})


@app.route("/story-media/<cliente>/<path:filename>")
def vedi_story_media(cliente, filename):
    path = os.path.join(BASE, "output", "media", cliente, "stories_upload", filename)
    if not os.path.exists(path):
        return "Immagine non trovata", 404
    return send_file(path, as_attachment=False)


@app.route("/api/ignora_note/<cliente>", methods=["POST"])
def api_ignora_note(cliente):
    s = carica_strategia(cliente)
    path = output_path(cliente, "sessioni", s["mesi"], s["anno"])
    if not os.path.exists(path):
        return jsonify({"errore": "sessione non trovata"}), 404
    with open(path) as f:
        sessioni = json.load(f)
    for token, sess in reversed(list(sessioni.items())):
        if cliente in sess.get("pdf_path", "") and sess.get("stato") == "modifiche_richieste":
            sess["note_modifiche"] = ""
            sess["note_ignorate"] = True
            with open(path, 'w') as f:
                json.dump(sessioni, f, ensure_ascii=False, indent=2)
            return jsonify({"ok": True})
    return jsonify({"errore": "nessuna richiesta di modifiche da ignorare"}), 404


@app.route("/api/rigenera/<cliente>/<int:numero>", methods=["POST"])
def api_rigenera(cliente, numero):
    from copywriter import carica_strategia as cs, genera_post
    from datetime import datetime
    s = cs(cliente)
    path = output_path(cliente, "ped", s["mesi"], s["anno"])
    with open(path) as f:
        ped = json.load(f)
    post = next((p for p in ped if p["numero"] == numero), None)
    if not post:
        return jsonify({"errore": "non trovato"}), 404
    data = datetime.strptime(post["data"], "%Y-%m-%d")
    try:
        nuovo = genera_post(s, data, numero, post["argomento"], post["orario"])
    except Exception as e:
        msg = str(e)
        if any(t in msg.lower() for t in ("rate_limit", "rate limit", "429", "tokens per day", "tpd")):
            msg = "Limite giornaliero AI raggiunto (Groq free tier). Riprova più tardi o passa a un piano a pagamento."
        return jsonify({"ok": False, "errore": msg}), 200
    for i, p in enumerate(ped):
        if p["numero"] == numero:
            ped[i] = nuovo
    with open(path, 'w') as f:
        json.dump(ped, f, ensure_ascii=False, indent=2)
    return jsonify({"ok": True, "post": nuovo})


@app.route("/api/rigenera_tutti/<cliente>", methods=["POST"])
def api_rigenera_tutti(cliente):
    if rigenera_tutti_stato.get(cliente, {}).get("in_corso"):
        return jsonify({"ok": False, "errore": "Rigenerazione già in corso"})

    note = (request.json or {}).get("note", "") if request.is_json else ""
    if not note:
        s_tmp = carica_strategia(cliente)
        sess = stato_sessione(cliente, s_tmp["mesi"], s_tmp["anno"])
        note = (sess or {}).get("note_modifiche", "")

    def run():
        from copywriter import carica_strategia as cs, genera_post
        from datetime import datetime
        s = cs(cliente)
        path = output_path(cliente, "ped", s["mesi"], s["anno"])
        with open(path) as f:
            ped = json.load(f)
        rigenera_tutti_stato[cliente] = {"in_corso": True, "fatti": 0, "totale": len(ped)}
        try:
            for i, post in enumerate(ped):
                data = datetime.strptime(post["data"], "%Y-%m-%d")
                nuovo = genera_post(s, data, post["numero"], post["argomento"], post["orario"], note_cliente=note)
                ped[i] = nuovo
                rigenera_tutti_stato[cliente]["fatti"] = i + 1
                with open(path, 'w') as f:
                    json.dump(ped, f, ensure_ascii=False, indent=2)
        finally:
            rigenera_tutti_stato[cliente]["in_corso"] = False

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/rigenera_tutti/<cliente>/stato")
def api_rigenera_tutti_stato(cliente):
    st = rigenera_tutti_stato.get(cliente, {"in_corso": False, "fatti": 0, "totale": 0})
    return jsonify(st)


genera_stato = {}

@app.route("/api/genera/<cliente>", methods=["POST"])
def api_genera(cliente):
    if genera_stato.get(cliente, {}).get("in_corso"):
        return jsonify({"ok": False, "errore": "Generazione già in corso"})

    def run():
        import copywriter, stories
        genera_stato[cliente] = {"in_corso": True, "fase": "post", "fatti": 0,
                                 "totale": 0, "errore": ""}
        try:
            def prog_post(fatti, totale):
                genera_stato[cliente].update({"fase": "post", "fatti": fatti, "totale": totale})
            copywriter.genera_ped_completo(cliente, on_progress=prog_post)

            def prog_story(fatti, totale):
                genera_stato[cliente].update({"fase": "stories", "fatti": fatti, "totale": totale})
            stories.genera_stories_completo(cliente, on_progress=prog_story)
        except Exception as e:
            genera_stato[cliente]["errore"] = str(e)
            print(f"[GENERA] Errore: {e}")
        finally:
            genera_stato[cliente]["in_corso"] = False

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/genera/<cliente>/stato")
def api_genera_stato(cliente):
    return jsonify(genera_stato.get(cliente, {"in_corso": False, "fase": "", "fatti": 0, "totale": 0, "errore": ""}))


@app.route("/api/pdf/<cliente>", methods=["POST"])
def api_genera_pdf(cliente):
    from genera_pdf import genera_pdf
    path = genera_pdf(cliente)
    return jsonify({"ok": True, "path": path})


@app.route("/api/invia/<cliente>", methods=["POST"])
def api_invia(cliente):
    def run():
        import main
        main.run(cliente=cliente, skip_genera=True)
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/pdf/<cliente>")
def scarica_pdf(cliente):
    s = carica_strategia(cliente)
    path = output_path(cliente, "pdf", s["mesi"], s["anno"])
    if not os.path.exists(path):
        return "PDF non trovato", 404
    return send_file(path, as_attachment=False)


@app.route("/design/<cliente>/<path:filename>")
def vedi_design(cliente, filename):
    path = os.path.join(BASE, "output", "designs", cliente, filename)
    if not os.path.exists(path):
        return "Immagine non trovata", 404
    return send_file(path, as_attachment=False)


# ────────────────────────────── API STRATEGIA ──────────────────────────────

@app.route("/api/strategia/<cliente>", methods=["GET", "PUT"])
def api_strategia(cliente):
    path = os.path.join(BASE, 'clienti', cliente, 'strategia.json')
    with open(path) as f:
        s = json.load(f)
    if request.method == "PUT":
        aggiornamenti = request.json
        for k in ["tono", "hashtag_fissi", "orari_post", "orari_stories", "argomenti"]:
            if k in aggiornamenti:
                s[k] = aggiornamenti[k]
        with open(path, 'w') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True})
    return jsonify(s)


@app.route("/api/nuovo_cliente", methods=["POST"])
def api_nuovo_cliente():
    d = request.json
    cliente_id = d.get("id", "").strip().lower().replace(" ", "_")
    if not cliente_id or not d.get("nome"):
        return jsonify({"errore": "id e nome obbligatori"}), 400

    cliente_dir = os.path.join(BASE, 'clienti', cliente_id)
    if os.path.exists(cliente_dir):
        return jsonify({"errore": "cliente già esistente"}), 409

    os.makedirs(cliente_dir, exist_ok=True)

    mese_inizio = d.get("mese_inizio", "Giugno")
    mese_fine = d.get("mese_fine", "Luglio")
    from datetime import datetime
    anno = datetime.now().year

    strategia = {
        "cliente": d["nome"],
        "sito": d.get("sito", ""),
        "ig": "",
        "fb": "",
        "localita": "Italia",
        "tono": d.get("tono", "professionale ma caldo, rassicurante"),
        "emoji": True,
        "hashtag_fissi": [],
        "hashtag_per_argomento": {},
        "argomenti": ["Presentazione Studio", "Igiene E Prevenzione", "Team E Staff", "Servizi"],
        "mesi": [mese_inizio, mese_fine],
        "anno": anno,
        "post_settimana": 2,
        "orari_post": ["09:00", "18:00"],
        "orari_stories": ["10:00", "19:00"],
        "email_cliente": d.get("email", "")
    }
    with open(os.path.join(cliente_dir, 'strategia.json'), 'w') as f:
        json.dump(strategia, f, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "id": cliente_id})


# ────────────────────────────── API MEDIA ──────────────────────────────

media_running = {}
rigenera_tutti_stato = {}

@app.route("/api/media/scarica/<cliente>", methods=["POST"])
def api_media_scarica(cliente):
    if media_running.get(cliente):
        return jsonify({"ok": False, "errore": "Download già in corso"})

    def run():
        media_running[cliente] = True
        try:
            from media_finder import scarica_media
            scarica_media(cliente, force_redownload=True)
        finally:
            media_running[cliente] = False

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/media/stato/<cliente>")
def api_media_stato(cliente):
    media_root = os.path.join(BASE, "output", "media", cliente)
    classif_path = os.path.join(media_root, "_classificazioni.json")

    estensioni = (".jpg", ".jpeg", ".png", ".webp")
    candidati = set()
    for sub in ("_raw", "foto"):
        d = os.path.join(media_root, sub)
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                candidati.update(f for f in files if f.lower().endswith(estensioni))
    totale = len(candidati)

    classificazioni = {}
    if os.path.exists(classif_path):
        with open(classif_path) as f:
            classificazioni = json.load(f)
    classificate = len(classificazioni)

    conteggi = {}
    for arg in classificazioni.values():
        conteggi[arg] = conteggi.get(arg, 0) + 1

    return jsonify({
        "in_corso": media_running.get(cliente, False),
        "totale": totale,
        "classificate": classificate,
        "per_argomento": conteggi,
        "completato": totale > 0 and classificate >= totale
    })


# ────────────────────────────── API META ──────────────────────────────

@app.route("/api/meta/verifica")
def api_meta_verifica():
    try:
        from meta_poster import verifica_credenziali
        return jsonify(verifica_credenziali())
    except Exception as e:
        return jsonify({"token": False, "errori": [str(e)]})


@app.route("/api/meta/schedula/<cliente>", methods=["POST"])
def api_meta_schedula(cliente):
    try:
        from meta_poster import schedula_ped_completo
        risultati = schedula_ped_completo(cliente, dry_run=False)
        ok_fb = sum(1 for r in risultati if isinstance(r.get("fb"), dict) and r["fb"].get("ok"))
        ok_ig = sum(1 for r in risultati if isinstance(r.get("ig"), dict) and r["ig"].get("ok"))
        return jsonify({"ok": True, "totale": len(risultati), "ok_fb": ok_fb, "ok_ig": ok_ig})
    except Exception as e:
        return jsonify({"ok": False, "errore": str(e)}), 500


@app.route("/api/meta/browser/<cliente>", methods=["POST"])
def api_meta_browser(cliente):
    fb_email = os.getenv("FB_EMAIL", "")
    fb_password = os.getenv("FB_PASSWORD", "")
    if not fb_email or not fb_password:
        return jsonify({"ok": False, "errore": "FB_EMAIL e FB_PASSWORD mancanti nel .env"}), 400
    def run():
        from meta_browser import schedula_con_browser
        schedula_con_browser(cliente, fb_email, fb_password,
                             os.getenv("FB_PAGE_NAME", ""), headless=False)
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True, "messaggio": "Browser avviato — controlla il desktop"})


@app.route("/api/meta/dry_run/<cliente>", methods=["POST"])
def api_meta_dry_run(cliente):
    try:
        from meta_poster import schedula_ped_completo
        risultati = schedula_ped_completo(cliente, dry_run=True)
        return jsonify({"ok": True, "totale": len(risultati)})
    except Exception as e:
        return jsonify({"ok": False, "errore": str(e)}), 500


# ────────────────────────────── TEST FLOW ──────────────────────────────

test_log = []
test_running = False

def log(msg):
    print(msg)
    test_log.append(msg)

@app.route("/api/test_flow/<cliente>", methods=["POST"])
def api_test_flow(cliente):
    global test_log, test_running
    if test_running:
        return jsonify({"ok": False, "errore": "Test già in corso"})

    # email destinatario opzionale: se l'utente la specifica nel pannello,
    # il test invia a quella (così puoi provarlo su un indirizzo di test).
    email_override = ((request.json or {}).get("email", "") if request.is_json else "").strip()

    test_log = []
    test_running = True

    def run():
        global test_running
        try:
            import time, requests as req
            from dotenv import load_dotenv
            load_dotenv(os.path.join(BASE, '.env'))

            page_id    = os.getenv("META_PAGE_ID_FB", "")
            page_token = os.getenv("META_PAGE_ACCESS_TOKEN", "")

            # 1. URL pubblico per i link "Approva/Modifiche" nella mail
            #    (le pagine /approva, /modifiche girano nello stesso processo:
            #    non serve più ngrok né un server separato)
            base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
            if not base_url:
                log("✗ PUBLIC_BASE_URL non configurato — impossibile generare link pubblici")
                return
            log(f"✓ URL pubblico: {base_url}")

            # 2. Invia mail
            log("▶ Invio email al cliente...")
            sys.path.insert(0, os.path.join(BASE, 'agente'))
            from mailer import invia_pdf
            s = carica_strategia(cliente)
            pdf = output_path(cliente, "pdf", s["mesi"], s["anno"])
            ped_json = output_path(cliente, "ped", s["mesi"], s["anno"])
            with open(ped_json) as f:
                ped = json.load(f)
            stories_json = output_path(cliente, "stories", s["mesi"], s["anno"])
            with open(stories_json) as f:
                stories = json.load(f)

            email_dest = email_override or s["email_cliente"]
            token = invia_pdf(
                pdf_path=pdf,
                cliente=s["cliente"],
                email_cliente=email_dest,
                mesi=s["mesi"],
                anno=s["anno"],
                n_post=len(ped),
                n_stories=len(stories),
                base_url=base_url
            )
            log(f"✓ Mail inviata a {email_dest}")
            log(f"  Token: {token[:16]}...")

            # 3. Aspetta approvazione
            log("⏳ Attendo approvazione (clicca il link nella mail)...")
            sessioni_path = os.path.join(BASE, 'output', 'sessioni.json')
            for i in range(600):
                try:
                    with open(sessioni_path) as f:
                        sess = json.load(f)
                    stato = sess.get(token, {}).get("stato", "in_attesa")
                    if stato == "approvato":
                        log("✅ APPROVATO!")
                        break
                    elif stato == "modifiche_richieste":
                        log("⚠ Modifiche richieste — test interrotto")
                        return
                except Exception:
                    pass
                time.sleep(1)
            else:
                log("✗ Timeout — nessuna risposta in 10 minuti")
                return

            # 4. Posta su FB — con immagine (design) se disponibile, altrimenti testo
            log("▶ Pubblico su Facebook...")
            post0 = ped[0] if ped else {"caption": "Test post PED", "numero": 1}
            testo = post0.get("caption", "Test post PED")
            if post0.get("hashtag"):
                testo += f"\n\n{post0['hashtag']}"
            numero = post0.get("numero", 1)
            img_path = os.path.join(BASE, 'output', 'designs', cliente, f"post_{numero:02d}.png")
            media_url = ""
            if os.path.exists(img_path):
                log("  📷 Pubblico con immagine (design)...")
                media_url = f"/design/{cliente}/post_{numero:02d}.png"
                with open(img_path, 'rb') as imgf:
                    r = req.post(
                        f"https://graph.facebook.com/v19.0/{page_id}/photos",
                        data={"message": testo, "access_token": page_token},
                        files={"source": imgf}, timeout=60)
                data = r.json()
                pid = data.get("post_id") or data.get("id")
            else:
                log("  (nessuna immagine: pubblico solo testo)")
                r = req.post(
                    f"https://graph.facebook.com/v19.0/{page_id}/feed",
                    data={"message": testo, "access_token": page_token})
                data = r.json()
                pid = data.get("id")
            if pid:
                log(f"✅ Post pubblicato su Facebook! ID: {pid}")
                _salva_pubblicato(cliente, pid, testo, "facebook", origine="test", media_url=media_url)
            else:
                log(f"✗ Errore FB: {data}")

        except Exception as e:
            log(f"✗ Errore: {e}")
        finally:
            test_running = False

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/test_flow/log")
def api_test_log():
    return jsonify({"log": test_log, "running": test_running})


# ────────────────────────────── POST PUBBLICATI ──────────────────────────────
PUBBLICATI_PATH = os.path.join(BASE, 'output', 'pubblicati.json')


def _salva_pubblicato(cliente, post_id, testo, piattaforma="facebook", origine="test", media_url=""):
    """Registra un post realmente pubblicato (sopravvive ai deploy: sta sul volume)."""
    items = []
    if os.path.exists(PUBBLICATI_PATH):
        try:
            with open(PUBBLICATI_PATH) as f:
                items = json.load(f)
        except Exception:
            items = []
    # link al post: Graph restituisce id "pagina_post" → permalink Facebook
    url = f"https://www.facebook.com/{post_id}" if piattaforma == "facebook" else ""
    items.insert(0, {
        "id": post_id, "cliente": cliente, "piattaforma": piattaforma,
        "origine": origine, "testo": (testo or "")[:240], "url": url, "media_url": media_url,
        "data": datetime.now().isoformat(timespec="seconds"),
    })
    try:
        with open(PUBBLICATI_PATH, 'w') as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


@app.route("/api/pubblicati/<cliente>")
def api_pubblicati(cliente):
    items = []
    if os.path.exists(PUBBLICATI_PATH):
        try:
            with open(PUBBLICATI_PATH) as f:
                items = json.load(f)
        except Exception:
            items = []
    return jsonify({"pubblicati": [x for x in items if x.get("cliente") == cliente]})


# ────────────────────────────── CHAT AGENT ──────────────────────────────
# Assistente AI nel pannello: l'utente scrive comandi in linguaggio naturale e
# l'agente esegue le azioni del PED Manager via function-calling (Groq).
# 3 modalità (switch nella chat):
#   - assistente : solo lettura/risposte, nessuna azione
#   - sicure     : genera/rigenera/modifica/PDF, ma NON invia email né pubblica
#   - tutto      : tutto, con conferma esplicita su email e pubblicazione Meta

import ai as ai_module

TOOLS_CONFERMA = {"invia_email", "pubblica_meta"}


@app.route("/api/ai_models")
def api_ai_models():
    return jsonify({"models": ai_module.MODELS,
                    "selected": ai_module.get_selected_model(),
                    "status": ai_module.model_status()})


@app.route("/api/ai_models/check", methods=["POST"])
def api_ai_models_check():
    try:
        return jsonify({"ok": True, "status": ai_module.check_availability()})
    except Exception as e:
        return jsonify({"ok": False, "errore": str(e)}), 500


@app.route("/api/ai_log")
def api_ai_log():
    return jsonify({"log": ai_module.get_log(), "last_model": ai_module.LAST_MODEL})


@app.route("/api/ai_model", methods=["POST"])
def api_ai_model():
    mid = (request.json or {}).get("model", "")
    try:
        ai_module.set_selected_model(mid)
        return jsonify({"ok": True, "selected": mid})
    except Exception as e:
        return jsonify({"ok": False, "errore": str(e)}), 400

_TOOL_CATALOGO = {
    "stato_cliente": {
        "type": "function",
        "function": {
            "name": "stato_cliente",
            "description": "Restituisce lo stato attuale del cliente: numero di post e storie, stato approvazione, eventuali note del cliente, stato dei media. Usalo per rispondere a domande sullo stato.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    "leggi_post": {
        "type": "function",
        "function": {
            "name": "leggi_post",
            "description": "Legge il contenuto di un post specifico (caption, hashtag, argomento, orario, data) dato il suo numero.",
            "parameters": {"type": "object", "properties": {
                "numero": {"type": "integer", "description": "Numero del post"}}, "required": ["numero"]},
        },
    },
    "genera_contenuti": {
        "type": "function",
        "function": {
            "name": "genera_contenuti",
            "description": "Genera da zero TUTTI i post e le storie con l'AI (sovrascrive i contenuti esistenti). Operazione lunga: parte in background.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    "genera_pdf": {
        "type": "function",
        "function": {
            "name": "genera_pdf",
            "description": "Genera il PDF del piano editoriale dai contenuti attuali.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    "rigenera_post": {
        "type": "function",
        "function": {
            "name": "rigenera_post",
            "description": "Rigenera con l'AI il testo di un singolo post, dato il suo numero.",
            "parameters": {"type": "object", "properties": {
                "numero": {"type": "integer", "description": "Numero del post da rigenerare"}}, "required": ["numero"]},
        },
    },
    "rigenera_tutti": {
        "type": "function",
        "function": {
            "name": "rigenera_tutti",
            "description": "Rigenera TUTTI i post con l'AI, opzionalmente applicando delle note/indicazioni del cliente. Parte in background.",
            "parameters": {"type": "object", "properties": {
                "note": {"type": "string", "description": "Indicazioni del cliente da applicare (opzionale)"}}},
        },
    },
    "modifica_post": {
        "type": "function",
        "function": {
            "name": "modifica_post",
            "description": "Modifica manualmente un campo di un post (caption, hashtag, orario o nota_grafica).",
            "parameters": {"type": "object", "properties": {
                "numero": {"type": "integer"},
                "campo": {"type": "string", "enum": ["caption", "hashtag", "orario", "nota_grafica"]},
                "valore": {"type": "string"}}, "required": ["numero", "campo", "valore"]},
        },
    },
    "invia_email": {
        "type": "function",
        "function": {
            "name": "invia_email",
            "description": "Invia al cliente via email il PDF del piano editoriale con i link Approva/Modifiche. AZIONE IRREVERSIBILE: richiede conferma.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    "pubblica_meta": {
        "type": "function",
        "function": {
            "name": "pubblica_meta",
            "description": "Programma/pubblica i post su Facebook e Instagram via Meta API. AZIONE IRREVERSIBILE: richiede conferma.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
}

_TOOLS_PER_MODALITA = {
    "assistente": ["stato_cliente", "leggi_post"],
    "sicure": ["stato_cliente", "leggi_post", "genera_contenuti", "genera_pdf",
               "rigenera_post", "rigenera_tutti", "modifica_post"],
    "tutto": ["stato_cliente", "leggi_post", "genera_contenuti", "genera_pdf",
              "rigenera_post", "rigenera_tutti", "modifica_post",
              "invia_email", "pubblica_meta"],
}


def _ctx_cliente(cliente):
    """Riassunto di contesto da iniettare nel system prompt."""
    try:
        s = carica_strategia(cliente)
        mesi, anno = s["mesi"], s["anno"]
        ped, stories = [], []
        try:
            with open(output_path(cliente, "ped", mesi, anno)) as f:
                ped = json.load(f)
        except Exception:
            pass
        try:
            with open(output_path(cliente, "stories", mesi, anno)) as f:
                stories = json.load(f)
        except Exception:
            pass
        sess = stato_sessione(cliente, mesi, anno)
        stato = (sess or {}).get("stato", "non_inviato")
        note = (sess or {}).get("note_modifiche", "")
        return (f"Cliente: {s['cliente']} | Periodo: {mesi[0]}-{mesi[-1]} {anno} | "
                f"Post: {len(ped)} | Storie: {len(stories)} | Stato approvazione: {stato}"
                + (f" | Note cliente: {note}" if note else ""))
    except Exception:
        return f"Cliente: {cliente}"


def _esegui_tool(cliente, nome, args):
    """Esegue un tool e restituisce una stringa di risultato leggibile."""
    s = carica_strategia(cliente)
    if nome == "stato_cliente":
        return _ctx_cliente(cliente)

    if nome == "leggi_post":
        path = output_path(cliente, "ped", s["mesi"], s["anno"])
        with open(path) as f:
            ped = json.load(f)
        p = next((x for x in ped if x["numero"] == args.get("numero")), None)
        if not p:
            return f"Post {args.get('numero')} non trovato."
        return json.dumps({k: p.get(k) for k in ("numero", "data", "orario", "argomento", "caption", "hashtag")}, ensure_ascii=False)

    if nome == "genera_contenuti":
        def run():
            import copywriter, stories as st
            copywriter.genera_ped_completo(cliente)
            st.genera_stories_completo(cliente)
        threading.Thread(target=run, daemon=True).start()
        return "Generazione contenuti avviata in background. Ci vorranno alcuni minuti."

    if nome == "genera_pdf":
        from genera_pdf import genera_pdf
        path = genera_pdf(cliente)
        return f"PDF generato: {os.path.basename(path)}"

    if nome == "rigenera_post":
        from copywriter import genera_post
        path = output_path(cliente, "ped", s["mesi"], s["anno"])
        with open(path) as f:
            ped = json.load(f)
        numero = args.get("numero")
        post = next((p for p in ped if p["numero"] == numero), None)
        if not post:
            return f"Post {numero} non trovato."
        data = datetime.strptime(post["data"], "%Y-%m-%d")
        nuovo = genera_post(s, data, numero, post["argomento"], post["orario"])
        for i, p in enumerate(ped):
            if p["numero"] == numero:
                ped[i] = nuovo
        with open(path, 'w') as f:
            json.dump(ped, f, ensure_ascii=False, indent=2)
        return f"Post {numero} rigenerato. Nuova caption: {nuovo.get('caption', '')[:120]}..."

    if nome == "rigenera_tutti":
        note = args.get("note", "") or ""
        if rigenera_tutti_stato.get(cliente, {}).get("in_corso"):
            return "Rigenerazione già in corso."
        def run():
            from copywriter import genera_post
            path = output_path(cliente, "ped", s["mesi"], s["anno"])
            with open(path) as f:
                ped = json.load(f)
            rigenera_tutti_stato[cliente] = {"in_corso": True, "fatti": 0, "totale": len(ped)}
            try:
                for i, post in enumerate(ped):
                    data = datetime.strptime(post["data"], "%Y-%m-%d")
                    ped[i] = genera_post(s, data, post["numero"], post["argomento"], post["orario"], note_cliente=note)
                    rigenera_tutti_stato[cliente]["fatti"] = i + 1
                    with open(path, 'w') as f:
                        json.dump(ped, f, ensure_ascii=False, indent=2)
            finally:
                rigenera_tutti_stato[cliente]["in_corso"] = False
        threading.Thread(target=run, daemon=True).start()
        return (f"Rigenerazione di tutti i post avviata in background"
                + (f" applicando le note: \"{note}\"." if note else "."))

    if nome == "modifica_post":
        path = output_path(cliente, "ped", s["mesi"], s["anno"])
        with open(path) as f:
            ped = json.load(f)
        numero, campo, valore = args.get("numero"), args.get("campo"), args.get("valore")
        post = next((p for p in ped if p["numero"] == numero), None)
        if not post:
            return f"Post {numero} non trovato."
        post[campo] = valore
        post["modificato_manualmente"] = True
        with open(path, 'w') as f:
            json.dump(ped, f, ensure_ascii=False, indent=2)
        return f"Post {numero}: campo '{campo}' aggiornato."

    if nome == "invia_email":
        import main
        threading.Thread(target=lambda: main.run(cliente=cliente, skip_genera=True), daemon=True).start()
        return "Invio email al cliente avviato."

    if nome == "pubblica_meta":
        from meta_poster import schedula_ped_completo
        risultati = schedula_ped_completo(cliente, dry_run=False)
        ok_fb = sum(1 for r in risultati if isinstance(r.get("fb"), dict) and r["fb"].get("ok"))
        ok_ig = sum(1 for r in risultati if isinstance(r.get("ig"), dict) and r["ig"].get("ok"))
        return f"Pubblicazione Meta completata: {ok_fb} su Facebook, {ok_ig} su Instagram."

    return f"Tool sconosciuto: {nome}"


@app.route("/api/chat/<cliente>", methods=["POST"])
def api_chat(cliente):
    if not os.getenv("GROQ_API_KEY"):
        return jsonify({"errore": "GROQ_API_KEY non configurata"}), 500

    body = request.json or {}
    messaggi = body.get("messaggi", [])
    modalita = body.get("modalita", "sicure")
    conferma = body.get("conferma")  # nome azione da eseguire dopo conferma utente

    # Conferma di un'azione irreversibile: esegui direttamente, salta il modello
    if conferma:
        if modalita != "tutto" or conferma not in TOOLS_CONFERMA:
            return jsonify({"risposta": "Azione non consentita in questa modalità.", "pending": None})
        try:
            risultato = _esegui_tool(cliente, conferma, body.get("args", {}))
            return jsonify({"risposta": f"✅ {risultato}", "pending": None})
        except Exception as e:
            return jsonify({"risposta": f"❌ Errore: {e}", "pending": None})

    nomi_tool = _TOOLS_PER_MODALITA.get(modalita, _TOOLS_PER_MODALITA["sicure"])
    tools = [_TOOL_CATALOGO[n] for n in nomi_tool]

    sys_prompt = (
        "Sei l'assistente operativo del 'PED Manager', un'app che gestisce i piani editoriali "
        "social (post e storie Instagram/Facebook) per i clienti dell'agenzia. "
        "Rispondi sempre in italiano, in modo conciso e concreto. "
        "Quando l'utente chiede di fare un'azione, usa gli strumenti disponibili. "
        "Se un'azione non è disponibile nella modalità corrente, spiega come farla manualmente dal pannello. "
        f"\n\nCONTESTO ATTUALE → {_ctx_cliente(cliente)}"
    )
    if modalita == "assistente":
        sys_prompt += ("\n\nMODALITÀ ASSISTENTE: puoi solo leggere e spiegare, NON eseguire azioni che modificano i dati. "
                       "Se l'utente chiede un'azione, spiega cosa fa e digli di passare alla modalità 'Azioni sicure' o 'Esegui tutto' nello switch in alto.")
    elif modalita == "sicure":
        sys_prompt += ("\n\nMODALITÀ AZIONI SICURE: puoi generare/rigenerare/modificare contenuti e creare il PDF, "
                       "ma NON puoi inviare email al cliente né pubblicare su Meta. Se l'utente lo chiede, spiega che "
                       "per quelle azioni deve passare alla modalità 'Esegui tutto' nello switch in alto della chat.")

    conversazione = [{"role": "system", "content": sys_prompt}] + messaggi

    try:
        for _ in range(5):  # max 5 cicli di tool
            resp = ai_module.chat_completion(
                messages=conversazione, tools=tools, tool_choice="auto",
                temperature=0.3, max_tokens=1024)
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return jsonify({"risposta": msg.content or "", "pending": None})

            # se chiede un'azione che richiede conferma → fermati e chiedi conferma
            for tc in msg.tool_calls:
                if tc.function.name in TOOLS_CONFERMA:
                    etichette = {"invia_email": "inviare l'email del piano editoriale al cliente",
                                 "pubblica_meta": "pubblicare i post su Facebook e Instagram"}
                    return jsonify({
                        "risposta": f"Sto per {etichette.get(tc.function.name, tc.function.name)}. Confermi?",
                        "pending": {"azione": tc.function.name, "label": etichette.get(tc.function.name, tc.function.name)},
                    })

            # esegui i tool non-critici e continua il ciclo
            conversazione.append({
                "role": "assistant", "content": msg.content or "",
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                               for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                try:
                    risultato = _esegui_tool(cliente, tc.function.name, args)
                except Exception as e:
                    risultato = f"Errore nell'esecuzione: {e}"
                conversazione.append({"role": "tool", "tool_call_id": tc.id,
                                      "name": tc.function.name, "content": str(risultato)})

        return jsonify({"risposta": "Ho raggiunto il limite di operazioni in un solo messaggio. Riprova a specificare meglio.", "pending": None})
    except Exception as e:
        return jsonify({"errore": str(e)}), 500


# ────────────────────────────── APPROVAZIONE CLIENTE ──────────────────────────────
# Pagine pubbliche raggiunte dal cliente tramite il link mandato via mail
# (in precedenza serviva un secondo server Flask su porta separata: ora gira
# nello stesso processo della webapp, un solo deploy, un solo URL pubblico)

SESSIONI_PATH = os.path.join(BASE, 'output', 'sessioni.json')

HTML_APPROVA = """
<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<title>Piano Editoriale Approvato</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f0f7ff;}
.box{background:white;padding:40px;border-radius:16px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.1);max-width:480px;}
h1{color:#2962ff;} p{color:#555;} .icon{font-size:64px;}</style></head>
<body><div class="box"><div class="icon">✅</div>
<h1>Piano Approvato!</h1>
<p>Grazie {{ nome }}. Il piano editoriale è stato approvato.<br>
Procederemo con la programmazione dei contenuti su Instagram e Facebook.</p>
<p style="color:#aaa;font-size:12px;">{{ data }}</p>
</div></body></html>
"""

HTML_MODIFICHE = """
<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<title>Richiedi Modifiche</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f0f7ff;}
.box{background:white;padding:40px;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.1);max-width:520px;width:90%;}
h1{color:#f97316;} textarea{width:100%;height:140px;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:14px;resize:vertical;}
button{background:#f97316;color:white;border:none;padding:12px 28px;border-radius:8px;font-size:16px;cursor:pointer;margin-top:12px;width:100%;}
button:hover{background:#ea6c10;}</style></head>
<body><div class="box">
<h1>Richiedi Modifiche</h1>
<p>Scrivi qui le modifiche che desideri per il piano editoriale <strong>{{ cliente }}</strong>:</p>
<form method="POST">
<textarea name="note" placeholder="Es: cambia il post del 15 giugno, tono troppo formale..."></textarea><br>
<button type="submit">Invia Modifiche</button>
</form></div></body></html>
"""

HTML_GRAZIE = """
<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><title>Grazie</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f0f7ff;}
.box{background:white;padding:40px;border-radius:16px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.1);}
h1{color:#f97316;} .icon{font-size:64px;}</style></head>
<body><div class="box"><div class="icon">📝</div>
<h1>Modifiche ricevute!</h1>
<p>Grazie. Elaboreremo le modifiche e ti invieremo un nuovo piano aggiornato a breve.</p>
</div></body></html>
"""


def carica_sessioni():
    if os.path.exists(SESSIONI_PATH):
        with open(SESSIONI_PATH) as f:
            return json.load(f)
    return {}


def salva_sessione(token, dati):
    sessioni = carica_sessioni()
    sessioni[token] = dati
    os.makedirs(os.path.dirname(SESSIONI_PATH), exist_ok=True)
    with open(SESSIONI_PATH, 'w') as f:
        json.dump(sessioni, f, ensure_ascii=False, indent=2)


@app.route("/approva")
def approva():
    token = request.args.get("token", "")
    sessioni = carica_sessioni()
    if token not in sessioni:
        return "Link non valido.", 404
    s = sessioni[token]
    salva_sessione(token, {**s, "stato": "approvato", "data_risposta": datetime.now().isoformat()})
    return render_template_string(HTML_APPROVA,
                                  nome=s.get("cliente", ""),
                                  data=datetime.now().strftime("%d/%m/%Y %H:%M"))


@app.route("/modifiche", methods=["GET", "POST"])
def modifiche():
    token = request.args.get("token", "")
    sessioni = carica_sessioni()
    if token not in sessioni:
        return "Link non valido.", 404
    s = sessioni[token]
    if request.method == "POST":
        note = request.form.get("note", "").strip()
        salva_sessione(token, {**s, "stato": "modifiche_richieste",
                               "note_modifiche": note,
                               "data_risposta": datetime.now().isoformat()})
        return render_template_string(HTML_GRAZIE)
    return render_template_string(HTML_MODIFICHE, cliente=s.get("cliente", ""))


@app.route("/stato/<token>")
def stato_token(token):
    sessioni = carica_sessioni()
    if token not in sessioni:
        return jsonify({"errore": "token non trovato"}), 404
    return jsonify(sessioni[token])


# ────────────────────────────── MISC ──────────────────────────────

@app.route("/ping")
def ping():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(port=7777, debug=True, use_reloader=False)
