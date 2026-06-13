"""
Livello AI centralizzato: registry dei modelli, modello selezionato,
chat_completion con FALLBACK automatico tra i modelli gratuiti, e tracking
della disponibilità (per mostrare nello switch quali modelli sono pronti
o hanno esaurito il limite giornaliero).

Provider supportati per la generazione testi: Groq e Google (Gemini, via REST).
La chat con tool/function-calling usa solo i modelli Groq che li supportano.
I modelli premium sono elencati ma disabilitati (compaiono "grigi" nello switch).
"""
import collections
import json
import os
import re
import time

import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# ─ log attività AI (mostrato nella UI) ─
LOG = collections.deque(maxlen=60)
LAST_MODEL = None


def _log(msg, kind="info"):
    LOG.append({"t": time.strftime("%H:%M:%S"), "m": msg, "k": kind})


def get_log():
    return list(LOG)

_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
_HAS_GEMINI = bool(os.getenv("GEMINI_API_KEY"))

# Provider OpenAI-compatibili (stessa forma di risposta di Groq → tools compatibili).
# Si attivano impostando la relativa API key (Cerebras e OpenRouter hanno free tier).
_HAS_CEREBRAS = bool(os.getenv("CEREBRAS_API_KEY"))
_HAS_OPENROUTER = bool(os.getenv("OPENROUTER_API_KEY"))
try:
    from openai import OpenAI as _OpenAI
    _cerebras = _OpenAI(base_url="https://api.cerebras.ai/v1", api_key=os.getenv("CEREBRAS_API_KEY")) if _HAS_CEREBRAS else None
    _openrouter = _OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY")) if _HAS_OPENROUTER else None
except Exception:
    _cerebras = _openrouter = None

_OAI_CLIENTS = {"Groq": _client, "Cerebras": _cerebras, "OpenRouter": _openrouter}

# Registry modelli. tools = supporta function-calling (serve alla chat).
# L'ordine conta: il primo gratuito disponibile è il default. Cerebras è primo
# perché è affidabile e velocissimo; Groq/Gemini hanno limiti giornalieri.
MODELS = [
    # ── GRATUITI (Cerebras — inferenza velocissima, free tier generoso) ──
    {"id": "gpt-oss-120b", "label": "GPT-OSS 120B — Cerebras ⚡",
     "provider": "Cerebras", "tier": "free", "enabled": _HAS_CEREBRAS, "tools": True, "reasoning": True},
    {"id": "zai-glm-4.7", "label": "GLM 4.7 — Cerebras ⚡",
     "provider": "Cerebras", "tier": "free", "enabled": _HAS_CEREBRAS, "tools": True, "reasoning": True},
    # ── GRATUITI (Groq — velocissimi ma con limite giornaliero) ──
    {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B — Groq",
     "provider": "Groq", "tier": "free", "enabled": True, "tools": True},
    {"id": "llama-3.1-8b-instant", "label": "Llama 3.1 8B — Groq",
     "provider": "Groq", "tier": "free", "enabled": True, "tools": True},
    {"id": "gemma2-9b-it", "label": "Gemma 2 9B — Groq",
     "provider": "Groq", "tier": "free", "enabled": True, "tools": False},
    {"id": "llama3-70b-8192", "label": "Llama 3 70B — Groq",
     "provider": "Groq", "tier": "free", "enabled": True, "tools": False},
    # ── GRATUITI (OpenRouter — solo modelli :free; spesso congestionati, usati come bonus) ──
    {"id": "meta-llama/llama-3.3-70b-instruct:free", "label": "Llama 3.3 70B — OpenRouter (free)",
     "provider": "OpenRouter", "tier": "free", "enabled": _HAS_OPENROUTER, "tools": False},
    {"id": "google/gemma-4-31b-it:free", "label": "Gemma 4 31B — OpenRouter (free)",
     "provider": "OpenRouter", "tier": "free", "enabled": _HAS_OPENROUTER, "tools": False},
    # ── GRATUITI (Google Gemini) ──
    {"id": "gemini-2.0-flash", "label": "Gemini 2.0 Flash — Google",
     "provider": "Google", "tier": "free", "enabled": _HAS_GEMINI, "tools": False},
    {"id": "gemini-2.0-flash-lite", "label": "Gemini 2.0 Flash Lite — Google",
     "provider": "Google", "tier": "free", "enabled": _HAS_GEMINI, "tools": False},
    # ── PREMIUM (disabilitati per ora, compaiono grigi nello switch) ──
    {"id": "gpt-4o", "label": "OpenAI GPT-4o — premium",
     "provider": "OpenAI", "tier": "premium", "enabled": False, "tools": True},
    {"id": "claude-sonnet-4-5", "label": "Claude Sonnet 4.5 — premium",
     "provider": "Anthropic", "tier": "premium", "enabled": False, "tools": True},
    {"id": "gemini-2.5-pro", "label": "Gemini 2.5 Pro — premium",
     "provider": "Google", "tier": "premium", "enabled": False, "tools": True},
]

FREE_IDS = [m["id"] for m in MODELS if m["tier"] == "free" and m["enabled"]]
FREE_TOOL_IDS = [m["id"] for m in MODELS if m["tier"] == "free" and m["enabled"] and m["tools"]]
_BY_ID = {m["id"]: m for m in MODELS}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'output', 'ai_config.json')

# stato disponibilità: id -> {"state": ok|limited|error, "until": ts, "checked": ts}
_model_status = {}


# ─────────────────── selezione modello ───────────────────
def get_selected_model() -> str:
    try:
        with open(CONFIG_PATH) as f:
            mid = json.load(f).get("model")
        if mid in FREE_IDS:
            return mid
    except Exception:
        pass
    return FREE_IDS[0]


def set_selected_model(mid: str) -> str:
    if mid not in FREE_IDS:
        raise ValueError("Modello non disponibile o non abilitato")
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump({"model": mid}, f)
    return mid


# ─────────────────── stato / disponibilità ───────────────────
def _retryable(e: Exception) -> bool:
    s = str(e).lower()
    return any(t in s for t in (
        "rate_limit", "rate limit", "429", "tokens per day", "tpd", "quota",
        "decommission", "model_not_found", "does not exist", "no longer",
        "over capacity", "503", "service unavailable", "temporarily", "resource_exhausted"))


def is_rate_limit(e: Exception) -> bool:
    s = str(e).lower()
    return any(t in s for t in ("rate_limit", "rate limit", "429", "tokens per day", "tpd", "quota", "resource_exhausted"))


def _mark_ok(mid):
    _model_status[mid] = {"state": "ok", "until": 0, "checked": time.time()}


def _mark_limited(mid, e):
    s = str(e)
    secs = 900  # default 15 min
    m = re.search(r"try again in ([\d.]+)s", s)
    if m:
        secs = int(float(m.group(1))) + 2
    else:
        mm = re.search(r"in (\d+)m", s)
        if mm:
            secs = int(mm.group(1)) * 60
    _model_status[mid] = {"state": "limited", "until": time.time() + secs, "checked": time.time()}


def model_status() -> dict:
    now = time.time()
    out = {}
    for mid in FREE_IDS:
        st = _model_status.get(mid)
        if not st:
            out[mid] = {"state": "unknown"}
        elif st["state"] == "limited" and st["until"] > now:
            out[mid] = {"state": "limited", "retry_in": int(st["until"] - now)}
        elif st["state"] == "error":
            out[mid] = {"state": "error"}
        else:
            out[mid] = {"state": "ok"}
    return out


def check_availability() -> dict:
    """Prova ogni modello gratuito con una micro-richiesta per sapere quali
    sono realmente disponibili adesso (aggiorna lo stato)."""
    for mid in FREE_IDS:
        m = _BY_ID[mid]
        try:
            if m["provider"] == "Google":
                _gemini_call([{"role": "user", "content": "ping"}], 0.0, 5, mid)
            else:
                cli = _OAI_CLIENTS.get(m["provider"])
                if cli is None:
                    raise RuntimeError("client non configurato")
                cli.chat.completions.create(
                    model=mid, messages=[{"role": "user", "content": "ping"}], max_tokens=1)
            _mark_ok(mid)
        except Exception as e:
            if _retryable(e):
                _mark_limited(mid, e)
            else:
                _model_status[mid] = {"state": "error", "until": 0, "checked": time.time()}
    return model_status()


# ─────────────────── chiamata Gemini (REST) ───────────────────
class _Msg:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]


def _gemini_call(messages, temperature, max_tokens, model_id):
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY non configurata")
    sys_txt, contents = "", []
    for m in messages:
        role, txt = m.get("role"), m.get("content", "")
        if role == "system":
            sys_txt += txt + "\n"
        else:
            contents.append({"role": "model" if role == "assistant" else "user",
                             "parts": [{"text": txt}]})
    if not contents:
        contents = [{"role": "user", "parts": [{"text": sys_txt or "..."}]}]
    body = {"contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    if sys_txt:
        body["systemInstruction"] = {"parts": [{"text": sys_txt}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={key}"
    r = requests.post(url, json=body, timeout=40)
    if r.status_code != 200:
        raise RuntimeError(f"gemini {r.status_code}: {r.text[:200]}")
    data = r.json()
    try:
        txt = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        raise RuntimeError(f"gemini risposta vuota: {str(data)[:200]}")
    return _Resp(txt)


# ─────────────────── entry point unico ───────────────────
def chat_completion(messages, temperature=0.7, max_tokens=600, tools=None, tool_choice=None):
    """Chiama il modello selezionato; su errore recuperabile passa al successivo
    modello gratuito. Se servono i tools usa solo i modelli che li supportano.
    Restituisce un oggetto con .choices[0].message.content (e .tool_calls per Groq)."""
    if not FREE_IDS:
        raise RuntimeError("Nessun provider AI configurato (imposta GROQ/GEMINI/CEREBRAS/OPENROUTER_API_KEY)")

    pool = FREE_TOOL_IDS if tools else FREE_IDS
    primary = get_selected_model()
    if primary not in pool:
        primary = pool[0]
    ordine = [primary] + [m for m in pool if m != primary]

    global LAST_MODEL
    ultimo_err = None
    for mid in ordine:
        m = _BY_ID[mid]
        try:
            if m["provider"] == "Google":
                resp = _gemini_call(messages, temperature, max_tokens, mid)
            else:
                cli = _OAI_CLIENTS.get(m["provider"])
                if cli is None:
                    raise RuntimeError(f"client {m['provider']} non configurato")
                kwargs = {"model": mid, "messages": messages,
                          "temperature": temperature, "max_tokens": max_tokens}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = tool_choice or "auto"
                # modelli "reasoning": riduci il ragionamento per non sprecare token
                if m.get("reasoning"):
                    kwargs["extra_body"] = {"reasoning_effort": "low"}
                resp = cli.chat.completions.create(**kwargs)
            _mark_ok(mid)
            LAST_MODEL = mid
            _log(f"✓ {m['label']}", "ok")
            return resp
        except Exception as e:
            ultimo_err = e
            if _retryable(e):
                _mark_limited(mid, e)
                _log(f"⏳ {m['label']}: limite, passo al successivo", "warn")
                print(f"[AI] '{mid}' non disponibile ({type(e).__name__}); provo il prossimo…")
                continue
            _log(f"✗ {m['label']}: {type(e).__name__}", "err")
            raise
    _log("✗ nessun modello gratuito disponibile", "err")
    raise ultimo_err
