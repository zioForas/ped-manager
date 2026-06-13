"""
Schedula post su IG + FB via Publer API.
Gratis fino a 3 account social, nessuna app Meta da configurare.

Uso: python agente/publer_poster.py example
"""
import json
import os
import sys
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE = os.path.join(os.path.dirname(__file__), '..')
PUBLER_API = "https://publer.io/api/v1"


def headers():
    token = os.getenv("PUBLER_API_KEY", "")
    if not token:
        raise RuntimeError("PUBLER_API_KEY mancante nel .env")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def get_accounts() -> list:
    """Ritorna tutti gli account social collegati a Publer."""
    r = requests.get(f"{PUBLER_API}/accounts", headers=headers())
    r.raise_for_status()
    return r.json().get("data", [])


def verifica_credenziali() -> dict:
    try:
        accounts = get_accounts()
        return {
            "ok": True,
            "account_count": len(accounts),
            "accounts": [{"id": a["id"], "name": a["name"], "type": a["type"]} for a in accounts]
        }
    except Exception as e:
        return {"ok": False, "errore": str(e)}


def schedula_post(account_ids: list, testo: str, data_ora: datetime,
                  image_url: str = None) -> dict:
    """
    Schedula un post su Publer.
    data_ora deve essere timezone-aware (UTC o locale).
    """
    # converti in ISO 8601 UTC
    if data_ora.tzinfo is None:
        # assume fuso orario locale Europa/Roma (UTC+2 in estate)
        import calendar
        ts = calendar.timegm(data_ora.timetuple())
        data_ora_utc = datetime.utcfromtimestamp(ts).replace(tzinfo=timezone.utc)
    else:
        data_ora_utc = data_ora.astimezone(timezone.utc)

    scheduled_at = data_ora_utc.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    payload = {
        "account_ids": account_ids,
        "text": testo,
        "scheduled_at": scheduled_at,
        "post_type": "post",
    }
    if image_url:
        payload["media"] = [{"url": image_url}]

    r = requests.post(f"{PUBLER_API}/post", headers=headers(), json=payload)
    data = r.json()

    if r.ok and data.get("data"):
        post_id = data["data"][0].get("id") if isinstance(data["data"], list) else data["data"].get("id")
        return {"ok": True, "post_id": post_id, "scheduled_at": scheduled_at}
    else:
        return {"ok": False, "errore": data.get("message") or data.get("error") or str(data)}


def schedula_ped_completo(cliente: str, account_ids: list = None) -> list:
    """Legge il PED e schedula tutti i post su Publer."""
    s_path = os.path.join(BASE, 'clienti', cliente, 'strategia.json')
    with open(s_path) as f:
        strategia = json.load(f)

    mesi = strategia["mesi"]
    anno = strategia["anno"]
    m1, m2 = mesi[0].lower(), mesi[-1].lower()

    with open(os.path.join(BASE, 'output', f'ped_{cliente}_{m1}_{m2}_{anno}.json')) as f:
        ped = json.load(f)

    # se non specificati, usa tutti gli account collegati
    if not account_ids:
        accounts = get_accounts()
        account_ids = [a["id"] for a in accounts]
        print(f"Account trovati: {[a['name'] for a in accounts]}")

    risultati = []
    errori = []

    print(f"\nSchedulo {len(ped)} post su Publer...")
    for post in ped:
        try:
            data_str = post["data"]
            orario_str = post.get("orario", "09:00")
            data_ora = datetime.strptime(f"{data_str} {orario_str}", "%Y-%m-%d %H:%M")

            if data_ora < datetime.now():
                print(f"  SKIP [{post['numero']}] data passata: {data_str}")
                continue

            testo = post["caption"]
            if post.get("hashtag"):
                testo += f"\n\n{post['hashtag']}"

            print(f"  [{post['numero']}/{len(ped)}] {data_ora.strftime('%d/%m %H:%M')} — {post['argomento'][:30]}...", end=" ")

            res = schedula_post(account_ids, testo, data_ora)

            if res["ok"]:
                print(f"✓ (ID: {res['post_id']})")
                risultati.append({**res, "numero": post["numero"], "data_ora": data_ora.isoformat()})
            else:
                print(f"✗ {res['errore']}")
                errori.append({"numero": post["numero"], "errore": res["errore"]})

            time.sleep(1)  # rispetta rate limit

        except Exception as e:
            print(f"✗ Errore: {e}")
            errori.append({"numero": post.get("numero"), "errore": str(e)})

    # salva report
    report_path = os.path.join(BASE, 'output', f'publer_report_{cliente}_{m1}_{m2}_{anno}.json')
    with open(report_path, 'w') as f:
        json.dump({"schedulati": risultati, "errori": errori}, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✓ Schedulati: {len(risultati)}/{len(ped)}")
    if errori:
        print(f"✗ Errori: {len(errori)}")
    print(f"Report: {report_path}")
    return risultati


if __name__ == "__main__":
    cliente = sys.argv[1] if len(sys.argv) > 1 else "example"
    if "--verifica" in sys.argv:
        print(json.dumps(verifica_credenziali(), indent=2))
    else:
        schedula_ped_completo(cliente)
