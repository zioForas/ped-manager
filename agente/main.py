"""
Orchestratore principale del workflow PED.
Esegui: python agente/main.py
"""
import json
import os
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def carica_strategia(cliente):
    path = os.path.join(os.path.dirname(__file__), '..', 'clienti', cliente, 'strategia.json')
    with open(path) as f:
        return json.load(f)

def step1_genera_contenuti(cliente):
    from copywriter import genera_ped_completo
    from stories import genera_stories_completo
    print("\n[STEP 1] Generazione contenuti...")
    ped = genera_ped_completo(cliente)
    stories = genera_stories_completo(cliente)
    return ped, stories

def step1b_genera_pdf(cliente):
    from genera_pdf import genera_pdf
    print("\n[STEP 1b] Generazione PDF...")
    return genera_pdf(cliente)

def step1c_crea_designs(cliente, ped):
    from media_finder import scarica_media
    from canva_designer import crea_tutti_designs
    print("\n[STEP 1c] Preparazione media e creazione design...")
    scarica_media(cliente)
    return crea_tutti_designs(cliente, ped, usa_canva=False)

def step2_invia_e_attendi(cliente, pdf_path, ped, stories):
    from server import avvia_server
    from mailer import invia_pdf, attendi_risposta

    strategia = carica_strategia(cliente)
    email_cliente = os.getenv("CLIENTE_EMAIL")
    if not email_cliente:
        raise ValueError("Configura CLIENTE_EMAIL nel file .env")

    base_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if base_url:
        # In cloud (Railway/Render) la webapp è già pubblica: le route
        # /approva, /modifiche, /stato sono servite dallo stesso processo.
        print(f"\n[STEP 2] Uso URL pubblico esistente: {base_url}")
    else:
        print("\n[STEP 2] Avvio server locale...")
        avvia_server(porta=5555)
        time.sleep(1)

        print("[STEP 2] Avvio tunnel ngrok...")
        from pyngrok import ngrok
        ngrok_token = os.getenv("NGROK_AUTH_TOKEN", "")
        if ngrok_token:
            ngrok.set_auth_token(ngrok_token)
        tunnel = ngrok.connect(5555)
        base_url = tunnel.public_url
        print(f"   URL pubblico: {base_url}")

    print("[STEP 2] Invio email al cliente...")
    token = invia_pdf(
        pdf_path=pdf_path,
        cliente=strategia["cliente"],
        email_cliente=email_cliente,
        mesi=strategia["mesi"],
        anno=strategia["anno"],
        n_post=len(ped),
        n_stories=len(stories),
        base_url=base_url
    )

    print("[STEP 2] Email inviata. Attendo risposta cliente...")
    risposta = attendi_risposta(token)
    return risposta, token

def step3_gestisci_risposta(risposta, cliente, pdf_path, ped, stories):
    stato = risposta.get("stato")

    if stato == "approvato":
        print("\n[STEP 3] Cliente ha APPROVATO. Avvio programmazione Meta...")
        step3_posta_su_meta(cliente, ped, stories)

    elif stato == "modifiche_richieste":
        note = risposta.get("note_modifiche", "")
        print(f"\n[STEP 3] Cliente ha richiesto MODIFICHE:\n  {note}")
        print("[STEP 3] Rigenerazione contenuti con le note del cliente...")
        step3_applica_modifiche(cliente, note, ped)

    elif stato == "timeout":
        print("\n[STEP 3] Nessuna risposta ricevuta. Riprova manualmente.")

def step3_posta_su_meta(cliente, ped, stories):
    # TODO: Meta API scheduling (Step 4)
    print("  [META] Programmazione su Instagram e Facebook...")
    print("  [META] (Meta API - step successivo)")
    # from meta_poster import programma_ped
    # programma_ped(ped, stories)

def step3_applica_modifiche(cliente, note, ped):
    # TODO: rigenerazione selettiva con le note
    print(f"  [MODIFICA] Note ricevute: {note}")
    print("  [MODIFICA] Rigenerazione e reinvio (step successivo)")

def run(cliente="example", skip_genera=False):
    strategia = carica_strategia(cliente)
    mesi = strategia["mesi"]
    anno = strategia["anno"]

    print(f"\n{'='*50}")
    print(f"WORKFLOW PED - {strategia['cliente']}")
    print(f"Periodo: {mesi[0]} - {mesi[-1]} {anno}")
    print(f"{'='*50}")

    # Step 1 - genera contenuti (o skip se già fatti)
    if skip_genera:
        print("\n[STEP 1] Skip - contenuti gia generati.")
        ped_path = os.path.join(os.path.dirname(__file__), '..', 'output',
                                f'ped_{cliente}_{mesi[0].lower()}_{mesi[-1].lower()}_{anno}.json')
        stories_path = os.path.join(os.path.dirname(__file__), '..', 'output',
                                    f'stories_{cliente}_{mesi[0].lower()}_{mesi[-1].lower()}_{anno}.json')
        with open(ped_path) as f:
            ped = json.load(f)
        with open(stories_path) as f:
            stories = json.load(f)
    else:
        ped, stories = step1_genera_contenuti(cliente)

    # Step 1c - prepara media e crea i design (foto giusta per argomento + copy)
    ped = step1c_crea_designs(cliente, ped)

    # Step 1b - genera PDF
    pdf_path = step1b_genera_pdf(cliente)

    # Step 2 - invia mail e attendi risposta
    risposta, token = step2_invia_e_attendi(cliente, pdf_path, ped, stories)

    # Step 3 - gestisci risposta
    step3_gestisci_risposta(risposta, cliente, pdf_path, ped, stories)

    print("\nWorkflow completato.")

if __name__ == "__main__":
    # Usa skip_genera=True se hai gia generato i contenuti oggi
    run(cliente="example", skip_genera=True)
