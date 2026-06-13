"""
Meta API — schedula post su Facebook Page e Instagram Business.
Workflow:
  FB:  POST /{page-id}/feed  con scheduled_publish_time (nativo Meta)
  IG:  crea container → pubblica al momento giusto tramite scheduler locale
"""
import json
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE = os.path.join(os.path.dirname(__file__), '..')
GRAPH = "https://graph.facebook.com/v19.0"


def _token():
    t = os.getenv("META_ACCESS_TOKEN", "")
    if not t:
        raise RuntimeError("META_ACCESS_TOKEN mancante nel .env")
    return t


def verifica_credenziali() -> dict:
    """Controlla che token, page e IG account siano validi."""
    token = _token()
    page_id = os.getenv("META_PAGE_ID_FB", "")
    ig_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID", "")
    risultato = {"token": False, "pagina_fb": False, "ig": False, "errori": []}

    # verifica token
    r = requests.get(f"{GRAPH}/me", params={"access_token": token})
    if r.ok and "name" in r.json():
        risultato["token"] = True
        risultato["nome_account"] = r.json().get("name")
    else:
        risultato["errori"].append(f"Token non valido: {r.text[:100]}")
        return risultato

    # verifica pagina FB
    if page_id:
        r = requests.get(f"{GRAPH}/{page_id}", params={
            "fields": "name,access_token", "access_token": token
        })
        if r.ok and "name" in r.json():
            risultato["pagina_fb"] = True
            risultato["nome_pagina"] = r.json().get("name")
            risultato["page_token"] = r.json().get("access_token", token)
        else:
            risultato["errori"].append(f"Pagina FB non trovata: {r.text[:100]}")
    else:
        risultato["errori"].append("META_PAGE_ID_FB non configurato")

    # verifica IG
    if ig_id:
        r = requests.get(f"{GRAPH}/{ig_id}", params={
            "fields": "name,username", "access_token": token
        })
        if r.ok:
            risultato["ig"] = True
            risultato["ig_username"] = r.json().get("username", ig_id)
        else:
            risultato["errori"].append(f"IG account non trovato: {r.text[:100]}")
    else:
        risultato["errori"].append("META_INSTAGRAM_ACCOUNT_ID non configurato")

    return risultato


def _page_token(page_id: str) -> str:
    """Ritorna il Page Access Token (più permessi del user token per scheduling)."""
    r = requests.get(f"{GRAPH}/{page_id}", params={
        "fields": "access_token", "access_token": _token()
    })
    data = r.json()
    return data.get("access_token", _token())


def schedula_fb(page_id: str, caption: str, data_ora: datetime,
                image_url: str = None) -> dict:
    """Schedula un post su Facebook Page."""
    page_tok = _page_token(page_id)
    ts = int(data_ora.timestamp())
    now_ts = int(time.time())

    # Meta richiede che scheduled_publish_time sia nel futuro (min 10 min)
    if ts <= now_ts + 600:
        # pubblica subito se la data è passata o troppo vicina
        pubblicato = True
        params = {"message": caption, "published": "true", "access_token": page_tok}
        if image_url:
            # per immagini usa photos endpoint
            endpoint = f"{GRAPH}/{page_id}/photos"
            params["url"] = image_url
            params["caption"] = caption
            del params["message"]
        else:
            endpoint = f"{GRAPH}/{page_id}/feed"
    else:
        pubblicato = False
        params = {
            "message": caption,
            "published": "false",
            "scheduled_publish_time": str(ts),
            "access_token": page_tok
        }
        if image_url:
            endpoint = f"{GRAPH}/{page_id}/photos"
            params["url"] = image_url
            params["caption"] = caption
            del params["message"]
        else:
            endpoint = f"{GRAPH}/{page_id}/feed"

    r = requests.post(endpoint, data=params)
    risultato = r.json()
    return {
        "piattaforma": "facebook",
        "post_id": risultato.get("id") or risultato.get("post_id"),
        "schedulato": not pubblicato,
        "data_ora": data_ora.isoformat(),
        "ok": "id" in risultato or "post_id" in risultato,
        "errore": risultato.get("error", {}).get("message") if "error" in risultato else None
    }


def schedula_ig(ig_id: str, caption: str, data_ora: datetime,
                image_url: str = None, video_url: str = None) -> dict:
    """
    Crea container IG e lo pubblica.
    IG non supporta scheduled_publish_time via API pubblica —
    salviamo il job in una coda locale e un thread lo esegue al momento giusto.
    """
    if not image_url and not video_url:
        return {"piattaforma": "instagram", "ok": False,
                "errore": "IG richiede un'immagine o video — URL mancante"}

    coda_path = os.path.join(BASE, 'output', 'ig_queue.json')
    coda = []
    if os.path.exists(coda_path):
        with open(coda_path) as f:
            coda = json.load(f)

    job = {
        "ig_id": ig_id,
        "caption": caption,
        "data_ora": data_ora.isoformat(),
        "timestamp": int(data_ora.timestamp()),
        "image_url": image_url,
        "video_url": video_url,
        "stato": "in_attesa",
        "token": _token()
    }
    coda.append(job)
    with open(coda_path, 'w') as f:
        json.dump(coda, f, ensure_ascii=False, indent=2)

    return {
        "piattaforma": "instagram",
        "ok": True,
        "schedulato": True,
        "data_ora": data_ora.isoformat(),
        "nota": "Job aggiunto alla coda locale — verrà pubblicato automaticamente"
    }


def pubblica_ig_ora(ig_id: str, caption: str, token: str,
                    image_url: str = None, video_url: str = None) -> dict:
    """Pubblica subito su IG (usato dal worker della coda)."""
    params_container = {"caption": caption, "access_token": token}
    if video_url:
        params_container["media_type"] = "REELS"
        params_container["video_url"] = video_url
    else:
        params_container["image_url"] = image_url

    r1 = requests.post(f"{GRAPH}/{ig_id}/media", data=params_container)
    d1 = r1.json()
    if "id" not in d1:
        return {"ok": False, "errore": d1.get("error", {}).get("message", str(d1))}

    container_id = d1["id"]
    time.sleep(5)  # attendi elaborazione

    r2 = requests.post(f"{GRAPH}/{ig_id}/media_publish", data={
        "creation_id": container_id, "access_token": token
    })
    d2 = r2.json()
    return {
        "ok": "id" in d2,
        "post_id": d2.get("id"),
        "errore": d2.get("error", {}).get("message") if "error" in d2 else None
    }


def schedula_ped_completo(cliente: str, dry_run: bool = False) -> list:
    """
    Legge il PED approvato e schedula tutti i post su FB e IG.
    dry_run=True mostra cosa farebbe senza pubblicare nulla.
    """
    s_path = os.path.join(BASE, 'clienti', cliente, 'strategia.json')
    with open(s_path) as f:
        strategia = json.load(f)

    mesi = strategia["mesi"]
    anno = strategia["anno"]
    m1, m2 = mesi[0].lower(), mesi[-1].lower()

    ped_path = os.path.join(BASE, 'output', f'ped_{cliente}_{m1}_{m2}_{anno}.json')
    with open(ped_path) as f:
        ped = json.load(f)

    page_id = os.getenv("META_PAGE_ID_FB", "")
    ig_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID", "")

    risultati = []
    for post in ped:
        data_str = post["data"]
        orario_str = post.get("orario", "09:00")
        try:
            data_ora = datetime.strptime(f"{data_str} {orario_str}", "%Y-%m-%d %H:%M")
        except Exception:
            data_ora = datetime.strptime(data_str, "%Y-%m-%d").replace(hour=9)

        caption = post["caption"]
        if post.get("hashtag"):
            caption += f"\n\n{post['hashtag']}"

        print(f"  [{post['numero']}/{len(ped)}] {data_ora.strftime('%d/%m %H:%M')} — {post['argomento'][:30]}")

        if dry_run:
            risultati.append({
                "numero": post["numero"], "data_ora": data_ora.isoformat(),
                "dry_run": True, "fb": "skippato", "ig": "skippato"
            })
            continue

        res_fb = schedula_fb(page_id, caption, data_ora) if page_id else {"ok": False, "errore": "page_id mancante"}
        time.sleep(1)
        res_ig = schedula_ig(ig_id, caption, data_ora) if ig_id else {"ok": False, "errore": "ig_id mancante"}

        risultati.append({
            "numero": post["numero"],
            "data_ora": data_ora.isoformat(),
            "fb": res_fb,
            "ig": res_ig
        })
        time.sleep(2)

    # salva report
    report_path = os.path.join(BASE, 'output', f'meta_report_{cliente}_{m1}_{m2}_{anno}.json')
    with open(report_path, 'w') as f:
        json.dump(risultati, f, ensure_ascii=False, indent=2)

    ok_fb = sum(1 for r in risultati if isinstance(r.get("fb"), dict) and r["fb"].get("ok"))
    ok_ig = sum(1 for r in risultati if isinstance(r.get("ig"), dict) and r["ig"].get("ok"))
    print(f"\nFB: {ok_fb}/{len(ped)} schedulati | IG: {ok_ig}/{len(ped)} in coda")
    print(f"Report: {report_path}")
    return risultati


if __name__ == "__main__":
    import sys
    cliente = sys.argv[1] if len(sys.argv) > 1 else "example"
    dry = "--dry" in sys.argv
    if dry:
        print("=== DRY RUN — nessuna pubblicazione ===")
    cred = verifica_credenziali()
    print("Credenziali:", cred)
    if cred["token"] or dry:
        schedula_ped_completo(cliente, dry_run=dry)
