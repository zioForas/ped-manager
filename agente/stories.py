import json
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

import ai

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def carica_strategia(cliente: str) -> dict:
    path = os.path.join(os.path.dirname(__file__), '..', 'clienti', cliente, 'strategia.json')
    with open(path) as f:
        return json.load(f)

def carica_ped(cliente: str, mese1: str, mese2: str, anno: int) -> list:
    path = os.path.join(os.path.dirname(__file__), '..', 'output',
                        f'ped_{cliente}_{mese1.lower()}_{mese2.lower()}_{anno}.json')
    with open(path) as f:
        return json.load(f)

def genera_settimane(mesi: list, anno: int) -> list:
    """Restituisce lista di lunedì (inizio settimana) per i 2 mesi."""
    mesi_map = {"Gennaio":1,"Febbraio":2,"Marzo":3,"Aprile":4,"Maggio":5,
                "Giugno":6,"Luglio":7,"Agosto":8,"Settembre":9,"Ottobre":10,
                "Novembre":11,"Dicembre":12}
    inizio = datetime(anno, mesi_map[mesi[0]], 1)
    fine_mese = mesi_map[mesi[-1]]
    fine_anno = anno if fine_mese < 12 else anno
    if fine_mese == 12:
        fine = datetime(anno + 1, 1, 1) - timedelta(days=1)
    else:
        fine = datetime(anno, fine_mese + 1, 1) - timedelta(days=1)

    settimane = []
    lunedi = inizio - timedelta(days=inizio.weekday())
    while lunedi <= fine:
        if lunedi.month >= mesi_map[mesi[0]] or lunedi + timedelta(days=6) >= inizio:
            settimane.append(lunedi)
        lunedi += timedelta(days=7)
    return settimane

def genera_story_originale(strategia: dict, settimana: datetime, numero: int, argomento: str) -> dict:
    prompt = f"""Sei un esperto di Instagram Stories per studi dentistici italiani.

Cliente: {strategia['cliente']}
Tono: {strategia['tono']}
Argomento: {argomento}
Settimana del: {settimana.strftime('%d/%m/%Y')}

Crea una Instagram Story coinvolgente. Rispondi SOLO con JSON valido:

{{
  "testo": "testo breve per la story (max 3 righe, diretto, con emoji)",
  "tipo": "domanda | curiosità | offerta | consiglio",
  "musica_suggerita": "genere o mood musicale adatto (es: pop italiano, acustico rilassante)",
  "tag_suggeriti": ["@account1", "@account2"],
  "sticker_suggeriti": ["tipo sticker es: sondaggio, domanda, countdown"],
  "nota_grafica": "descrizione visiva per il designer in una riga"
}}"""

    risposta = ai.chat_completion(
        [{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=1200,  # alto: alcuni modelli (reasoning) usano token per ragionare
    )
    testo = (risposta.choices[0].message.content or "").strip()

    if "```" in testo:
        testo = testo.split("```")[1]
        if testo.startswith("json"):
            testo = testo[4:]

    testo = testo.strip()
    if not testo.startswith("{") and "{" in testo:
        testo = testo[testo.index("{"):]
    if "}" in testo:
        testo = testo[:testo.rfind("}") + 1]
    try:
        dati = json.loads(testo)
    except Exception:
        dati = {"testo": testo, "tipo": "consiglio", "musica_suggerita": "", "tag_suggeriti": [], "sticker_suggeriti": [], "nota_grafica": ""}

    # pubblica mercoledì e venerdì
    data_pub = settimana + timedelta(days=2)  # mercoledì
    if numero % 2 == 0:
        data_pub = settimana + timedelta(days=4)  # venerdì

    return {
        "numero": numero,
        "tipo": "originale",
        "data": data_pub.strftime("%Y-%m-%d"),
        "orario": "10:00",
        "data_ora_pubblicazione": f"{data_pub.strftime('%Y-%m-%d')} 10:00",
        "argomento": argomento,
        "testo": dati.get("testo", ""),
        "formato_story": dati.get("tipo", ""),
        "musica_suggerita": dati.get("musica_suggerita", ""),
        "tag_suggeriti": dati.get("tag_suggeriti", []),
        "sticker_suggeriti": dati.get("sticker_suggeriti", []),
        "nota_grafica": dati.get("nota_grafica", ""),
        "stato": "da_approvare"
    }

def genera_story_repost(post_ped: dict, settimana: datetime, numero: int, giorno_offset: int) -> dict:
    data_pub = settimana + timedelta(days=giorno_offset)
    return {
        "numero": numero,
        "tipo": "repost",
        "data": data_pub.strftime("%Y-%m-%d"),
        "orario": "19:00",
        "data_ora_pubblicazione": f"{data_pub.strftime('%Y-%m-%d')} 19:00",
        "argomento": post_ped["argomento"],
        "riferimento_post": f"POST #{post_ped['numero']} del {post_ped['data']}",
        "testo": "Condividi il post del feed nelle storie",
        "nota": "Condividi il post uscito questa settimana, aggiungi sticker 'Nuovo post' o GIF",
        "stato": "da_approvare"
    }

def genera_stories_completo(cliente: str = "example", on_progress=None):
    strategia = carica_strategia(cliente)
    mesi = strategia["mesi"]
    anno = strategia["anno"]
    ped = carica_ped(cliente, mesi[0], mesi[-1], anno)

    settimane = genera_settimane(mesi, anno)
    argomenti = strategia["argomenti"]
    stories = []
    post_per_settimana = {}
    totale_stimato = len(settimane) * 4  # 2 originali + 2 repost a settimana

    # mappa post del PED per settimana
    for post in ped:
        data_post = datetime.strptime(post["data"], "%Y-%m-%d")
        lun = data_post - timedelta(days=data_post.weekday())
        chiave = lun.strftime("%Y-%m-%d")
        if chiave not in post_per_settimana:
            post_per_settimana[chiave] = []
        post_per_settimana[chiave].append(post)

    num_story = 1
    for i, settimana in enumerate(settimane):
        argomento = argomenti[i % len(argomenti)]
        chiave = settimana.strftime("%Y-%m-%d")
        post_questa_settimana = post_per_settimana.get(chiave, [])

        print(f"Settimana {i+1}/{len(settimane)}: {settimana.strftime('%d/%m/%Y')} — {argomento}")

        # story originale 1
        print(f"  Story originale {num_story}...")
        s1 = genera_story_originale(strategia, settimana, num_story, argomento)
        stories.append(s1)
        num_story += 1
        if on_progress:
            on_progress(len(stories), totale_stimato)
        time.sleep(2)

        # story originale 2
        argomento2 = argomenti[(i + 1) % len(argomenti)]
        print(f"  Story originale {num_story}...")
        s2 = genera_story_originale(strategia, settimana, num_story, argomento2)
        stories.append(s2)
        num_story += 1
        if on_progress:
            on_progress(len(stories), totale_stimato)
        time.sleep(2)

        # 2 repost dei post della settimana
        for j, post in enumerate(post_questa_settimana[:2]):
            giorno = 1 if j == 0 else 3  # martedì e giovedì
            print(f"  Repost #{post['numero']}...")
            sr = genera_story_repost(post, settimana, num_story, giorno)
            stories.append(sr)
            num_story += 1
            if on_progress:
                on_progress(len(stories), totale_stimato)

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    output_path = os.path.join(output_dir, f'stories_{cliente}_{mesi[0].lower()}_{mesi[-1].lower()}_{anno}.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Stories complete: {len(stories)} stories generate")
    print(f"✓ File: {output_path}")
    return stories

if __name__ == "__main__":
    genera_stories_completo("example")
