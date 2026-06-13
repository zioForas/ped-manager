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

def genera_calendario(mesi: list, anno: int) -> list:
    date = []
    giorni_post = [0, 3]  # lunedì, giovedì
    mesi_map = {"Gennaio":1,"Febbraio":2,"Marzo":3,"Aprile":4,"Maggio":5,
                "Giugno":6,"Luglio":7,"Agosto":8,"Settembre":9,"Ottobre":10,
                "Novembre":11,"Dicembre":12}
    for mese_nome in mesi:
        mese_num = mesi_map[mese_nome]
        giorno = datetime(anno, mese_num, 1)
        while giorno.month == mese_num:
            if giorno.weekday() in giorni_post:
                date.append(giorno)
            giorno += timedelta(days=1)
    return date

def genera_post(strategia: dict, data: datetime, numero: int, argomento: str, orario: str, note_cliente: str = "") -> dict:
    hashtag_key = argomento.lower().replace(" e ", "_").replace(" ", "_")
    hashtag_argomento = strategia["hashtag_per_argomento"].get(hashtag_key, [])
    hashtag_tutti = strategia["hashtag_fissi"] + hashtag_argomento
    hashtag_str = " ".join(hashtag_tutti)

    blocco_sedi = "\n".join(
        f"🏥 {s['citta']} · {s['indirizzo']}\n📞 {s['telefono']}"
        for s in strategia.get("sedi", [])
    )

    prompt = f"""Sei il social media manager dello {strategia['cliente']} e scrivi seguendo ESATTAMENTE lo stile reale già usato sui loro profili Instagram/Facebook.

CONTESTO DEL CLIENTE:
{strategia.get('team', '')}
Tono: {strategia['tono']}

Qui sotto trovi QUATTRO ESEMPI REALI già pubblicati dallo studio. Ti servono per capire il REGISTRO e la VARIETÀ di formati che usano — non copiarli e non riusarne le frasi: per ogni post scrivi un testo NUOVO e originale, scegliendo lo STILE/FORMATO più adatto al taglio specifico che vuoi dare all'argomento di oggi (lo studio stesso varia il formato da un post all'altro, anche sullo stesso argomento).

STILE A — Storytelling/heritage (narrativo, racconta storia/valori/persone):
"Esperienza, innovazione e attenzione al cliente. ✨\\nLa nostra realtà nasce dalla passione dei suoi fondatori e continua a crescere di generazione in generazione.\\nUna sola visione: offrire un servizio di qualità in un ambiente professionale, moderno e accogliente.\\nOgni giorno mettiamo al centro il benessere e la salute orale dei nostri pazienti, attraverso tecnologie all'avanguardia, aggiornamento costante e un approccio basato su ascolto, fiducia e attenzione."

STILE B — Educativo "Lo sapevi?" (hook a domanda/curiosità + spiegazione + chiusura ispirazionale):
"🪥 Lo sapevi?\\nL'igiene dentale professionale non serve solo ad avere denti più puliti e luminosi, ma è fondamentale per prevenire carie, gengiviti e problemi parodontali.\\nAnche con una corretta igiene quotidiana, placca e tartaro possono accumularsi nelle zone più difficili da raggiungere.\\nPer questo è importante sottoporsi a una seduta di igiene professionale ogni 6 mesi: un'abitudine semplice che aiuta a mantenere nel tempo la salute di denti e gengive.\\nLa prevenzione è il primo passo per un sorriso sano e duraturo. ✨"

STILE C — Protocollo numerato (per spiegare un trattamento/processo passo-passo):
"🦷 L'implantologia è la soluzione definitiva per i denti mancanti.\\nUn impianto dentale è una radice artificiale in titanio biocompatibile che si integra con l'osso, permettendo di ripristinare funzione masticatoria ed estetica in modo stabile e duraturo.\\nScorri per scoprire il nostro protocollo 👉\\n1️⃣ Diagnostica CBCT 3D: analisi accurata di osso, nervi e strutture anatomiche\\n2️⃣ Pianificazione digitale: chirurgia guidata per un approccio preciso e minimamente invasivo\\n3️⃣ Inserimento implantare: massima precisione operativa e tempi ottimizzati\\n4️⃣ Protesi definitiva: ripristino completo di estetica e funzione"

STILE D — Presentazione struttura/ambiente (descrive lo spazio fisico, la tecnologia, l'esperienza del paziente):
"🎥 Benvenuti nello Studio Example\\nUn ambiente moderno, tecnologico e pensato per garantire ai nostri pazienti il massimo comfort e la migliore qualità di cura.\\nNel nostro studio l'innovazione si unisce all'esperienza: utilizziamo tecnologie all'avanguardia e protocolli aggiornati per offrire trattamenti odontoiatrici precisi, sicuri e minimamente invasivi.\\nOgni spazio è progettato per accogliere il paziente con professionalità, attenzione e serenità, perché la qualità delle cure passa anche dall'ambiente in cui vengono eseguite."

COME SCEGLIERE LO STILE: valuta l'argomento di oggi e scegli liberamente lo stile (A, B, C o D) che racconta meglio quel taglio specifico — es. Implantologia/Igiene possono usare sia lo stile C (protocollo) sia lo stile B (educativo "Lo sapevi?") a seconda dell'angolo che vuoi dare; Presentazione Studio/Team possono usare sia lo stile A (storytelling) sia lo stile D (ambiente/struttura). Varia la scelta nel tempo: non ripetere sempre lo stesso formato per lo stesso argomento.

REGOLE DI STILE da applicare al NUOVO testo che scriverai:
- LUNGHEZZA: il corpo deve essere di almeno 70-90 parole (mai sotto le 65), in linea con gli esempi reali — sviluppa il concetto su 3-4 frasi/paragrafi pieni, non limitarti a 2 frasi brevi; resta comunque conciso, senza frasi di riempimento o ripetizioni
- Apertura con un hook breve e d'impatto, spesso con emoji a tema (🦷 🌟 👨‍⚕️ 🪥 🎥 ✨)
- Paragrafi BREVI separati da "\\n" (a capo); se usi lo stile C, ogni punto numerato (1️⃣ 2️⃣ 3️⃣ 4️⃣) sta su una riga propria
- Tono caldo, professionale, mai eccessivamente promozionale — usa le informazioni di contesto sopra (storia e valori del cliente) quando rilevante, ma con parole tue, NON ripetendo le frasi degli esempi
- Una call to action naturale (es. "Prenota la tua visita.", "Prenota il tuo controllo 📲") è benvenuta MA OPZIONALE — alcuni post reali non ce l'hanno, altri la inseriscono dentro il corpo, altri come riga finale: decidi tu se e come inserirla in modo che suoni naturale, oppure ometterla
- NON scrivere TU il blocco sedi (📍 Le nostre sedi: ...) e NON includere gli hashtag: vengono aggiunti automaticamente dopo il tuo testo, nell'ordine corretto
- Il tuo testo deve terminare subito dopo l'ultimo paragrafo del corpo (inclusa l'eventuale CTA, se scegli di metterla)
- Usa "\\n" per ogni a capo nel JSON

Argomento di oggi: {argomento}
Data: {data.strftime('%A %d %B %Y')}
{f'''
NOTE DI REVISIONE DAL CLIENTE — hanno PRIORITÀ ASSOLUTA su tutte le regole sopra, applicale sempre nello scrivere il nuovo testo:
"{note_cliente}"
''' if note_cliente else ''}
Scrivi un post NUOVO e originale (mai visto prima) per questo argomento, scegliendo lo stile più adatto. Rispondi SOLO con JSON valido, nessun testo fuori dal JSON:

{{
  "caption": "SOLO hook + corpo (+ eventuale CTA naturale) del post nuovo e originale, con \\\\n tra i paragrafi, nello stile scelto tra A/B/C/D — termina subito dopo l'ultimo paragrafo, SENZA blocco sedi, SENZA hashtag",
  "hashtag": "{hashtag_str}",
  "luogo": "{strategia.get('localita', 'Italia')}",
  "nota_grafica": "descrizione visiva per il designer in una riga"
}}"""

    risposta = ai.chat_completion(
        [{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1400,  # alto: alcuni modelli (reasoning) usano token per ragionare
    )
    testo = (risposta.choices[0].message.content or "").strip()

    # pulizia JSON
    if "```" in testo:
        testo = testo.split("```")[1]
        if testo.startswith("json"):
            testo = testo[4:]
    testo = testo.strip()
    # estrai l'oggetto JSON anche se c'è testo intorno
    if not testo.startswith("{") and "{" in testo:
        testo = testo[testo.index("{"):]
    if "}" in testo:
        testo = testo[:testo.rfind("}") + 1]

    try:
        dati = json.loads(testo)
    except Exception:
        dati = {"caption": testo, "hashtag": hashtag_str, "luogo": "", "nota_grafica": ""}

    caption = dati.get("caption", "").rstrip()
    if strategia.get("sedi"):
        caption += f"\n📍 Le nostre sedi:\n{blocco_sedi}"
    dati["caption"] = caption

    return {
        "numero": numero,
        "data": data.strftime("%Y-%m-%d"),
        "orario": orario,
        "data_ora_pubblicazione": f"{data.strftime('%Y-%m-%d')} {orario}",
        "argomento": argomento,
        "caption": dati.get("caption", ""),
        # gli hashtag sono FISSI (da strategia), mai lasciati all'AI: alcuni modelli
        # li restituivano vuoti o inventati — qui forziamo sempre quelli corretti
        "hashtag": hashtag_str,
        "luogo": dati.get("luogo", ""),
        "nota_grafica": dati.get("nota_grafica", ""),
        "stato": "da_approvare"
    }

def genera_ped_completo(cliente: str = "example", on_progress=None):
    strategia = carica_strategia(cliente)
    date_post = genera_calendario(strategia["mesi"], strategia["anno"])
    argomenti = strategia["argomenti"]
    orari = strategia["orari_post"]

    ped = []
    totale = len(date_post)
    for i, data in enumerate(date_post):
        argomento = argomenti[i % len(argomenti)]
        orario = orari[i % len(orari)]
        print(f"[{i+1}/{totale}] {argomento} — {data.strftime('%d/%m/%Y')} ore {orario}...")
        post = genera_post(strategia, data, i+1, argomento, orario)
        print(f"  ✓ {post['caption'][:60]}...")
        ped.append(post)
        if on_progress:
            on_progress(i + 1, totale)
        time.sleep(2)

    output_dir = os.path.join(os.path.dirname(__file__), '..', 'output')
    os.makedirs(output_dir, exist_ok=True)
    mesi = strategia["mesi"]
    output_path = os.path.join(output_dir, f'ped_{cliente}_{mesi[0].lower()}_{mesi[-1].lower()}_{strategia["anno"]}.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ped, f, ensure_ascii=False, indent=2)

    print(f"\n✓ PED completo: {len(ped)} post generati")
    print(f"✓ File: {output_path}")
    return ped

if __name__ == "__main__":
    genera_ped_completo("example")
