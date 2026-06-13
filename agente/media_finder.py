"""
Trova e scarica media da Google Drive per il PED.

Struttura cartelle Drive attesa (sotto la root del cliente):
  {root_folder}/
    presentazione_studio/   → studio, logo, esterni/interni
    igiene_prevenzione/     → spazzolini, pulizie, prevenzione
    team_staff/             → foto team e staff
    implantologia/          → impianti, procedure

Usa Google Drive API v3 con OAuth (prima volta apre browser per autorizzazione,
poi salva token in clienti/{cliente}/drive_token.json per le volte successive).

Alternativa senza API: gdown per cartelle Drive condivise pubblicamente.
"""
import json
import os
import re
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE = os.path.join(os.path.dirname(__file__), '..')

ARGOMENTO_FOLDER_MAP = {
    "Presentazione Studio": "presentazione_studio",
    "Igiene E Prevenzione": "igiene_prevenzione",
    "Team E Staff": "team_staff",
    "Implantologia": "implantologia",
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov"}


# ── INDICE MEDIA (traccia usate/non usate) ─────────────────────────────────

def _indice_path(cliente: str) -> str:
    return os.path.join(BASE, "clienti", cliente, "media_index.json")

def carica_indice(cliente: str) -> dict:
    path = _indice_path(cliente)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def salva_indice(cliente: str, indice: dict):
    with open(_indice_path(cliente), 'w') as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)

def marca_usata(cliente: str, argomento: str, filename: str, post_numero: int):
    indice = carica_indice(cliente)
    key = f"{argomento}/{filename}"
    indice[key] = {"usata_nel_post": post_numero, "argomento": argomento, "filename": filename}
    salva_indice(cliente, indice)

def prossima_immagine(cliente: str, argomento: str) -> str | None:
    """Restituisce il path locale della prossima immagine non ancora usata per l'argomento."""
    folder_name = ARGOMENTO_FOLDER_MAP.get(argomento)
    if not folder_name:
        return None

    media_dir = os.path.join(BASE, "output", "media", cliente, folder_name)
    if not os.path.exists(media_dir):
        return None

    indice = carica_indice(cliente)
    files = sorted([
        f for f in os.listdir(media_dir)
        if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
    ])

    for filename in files:
        key = f"{argomento}/{filename}"
        if key not in indice:
            return os.path.join(media_dir, filename)

    # tutte usate: ricomincia dal primo
    if files:
        return os.path.join(media_dir, files[0])
    return None


# ── DOWNLOAD VIA gdown (per cartelle Drive pubbliche) ─────────────────────

def scarica_cartella_gdown(folder_url: str, dest_dir: str) -> list:
    """
    Scarica tutti i file di una cartella Drive condivisa pubblicamente.
    Restituisce lista dei file scaricati.
    """
    import gdown
    os.makedirs(dest_dir, exist_ok=True)
    print(f"  Scarico da Drive → {dest_dir}")

    existing = set(os.listdir(dest_dir)) if os.path.exists(dest_dir) else set()

    try:
        gdown.download_folder(folder_url, output=dest_dir, quiet=False, use_cookies=False)
    except Exception as e:
        print(f"  ⚠ gdown errore: {e}")
        return []

    new_files = [
        os.path.join(dest_dir, f)
        for f in os.listdir(dest_dir)
        if f not in existing and Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return new_files


def _classifica_immagine_ai(image_path: str, argomenti: list) -> str:
    """
    Classifica l'immagine con vision AI.
    Prova in ordine: Gemini → Groq vision → euristica nome file.
    """
    # 1. Prova Groq vision (llama-4 multimodale)
    groq_result = _classifica_groq_vision(image_path, argomenti)
    if groq_result:
        return groq_result

    # 2. Prova Gemini (con retry per rate limit)
    gemini_result = _classifica_gemini(image_path, argomenti)
    if gemini_result:
        return gemini_result

    # 3. Euristica sul nome file
    return _classifica_per_nome(image_path, argomenti)


def _classifica_groq_vision(image_path: str, argomenti: list) -> str | None:
    """Classifica con Groq llama-4 vision (multimodale)."""
    import base64
    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        return None

    try:
        from PIL import Image as PILImage
        import io as _io

        # Resize a max 800px per lato prima di inviare
        img = PILImage.open(image_path).convert("RGB")
        img.thumbnail((800, 800), PILImage.LANCZOS)
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode()
        mime = "image/jpeg"

        argomenti_str = "\n".join(f"- {a}" for a in argomenti)
        prompt = f"""Look at this dental studio image and classify it into ONE of these categories:
{argomenti_str}

Reply with ONLY the exact category name, nothing else.
If unsure, choose "Presentazione Studio"."""

        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}}
                ]
            }],
            max_tokens=50,
        )
        testo = resp.choices[0].message.content.strip()
        for arg in argomenti:
            if arg.lower() in testo.lower():
                return arg
        return None
    except Exception as e:
        print(f"    ⚠ Groq vision: {e}")
        return None


def _classifica_gemini(image_path: str, argomenti: list) -> str | None:
    """Classifica con Gemini Vision (con retry su 429)."""
    from google import genai
    from PIL import Image as PILImage

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    argomenti_str = "\n".join(f"- {a}" for a in argomenti)
    prompt = f"""Guarda questa immagine di uno studio dentistico.
Classifica in UNO di questi argomenti:
{argomenti_str}
Rispondi con SOLO il nome esatto. Se non sei sicuro: "Presentazione Studio"."""

    for attempt in range(2):
        try:
            client = genai.Client(api_key=api_key)
            img = PILImage.open(image_path)
            risposta = client.models.generate_content(
                model="gemini-2.0-flash", contents=[prompt, img]
            )
            testo = risposta.text.strip()
            for arg in argomenti:
                if arg.lower() in testo.lower():
                    return arg
            return argomenti[0]
        except Exception as e:
            err = str(e)
            if "429" in err and attempt == 0:
                import re as _re
                delay = _re.search(r'retry.*?(\d+)s', err)
                wait = int(delay.group(1)) + 2 if delay else 16
                print(f"    ⚠ Gemini rate limit, riprovo tra {wait}s...")
                time.sleep(wait)
            else:
                return None
    return None


def _smista_con_ai(cliente: str, file_paths: list, argomenti: list) -> dict:
    """
    Classifica una lista di immagini con vision AI e le copia nelle cartelle
    locali per argomento (output/media/{cliente}/{slug}/).
    Usa una cache su disco (_classificazioni.json) per non riclassificare due volte.
    Ritorna: { argomento: [percorsi_locali_copiati] }
    """
    import shutil

    output_root = os.path.join(BASE, "output", "media", cliente)
    for arg in argomenti:
        os.makedirs(os.path.join(output_root, ARGOMENTO_FOLDER_MAP[arg]), exist_ok=True)

    classif_path = os.path.join(output_root, "_classificazioni.json")
    classificazioni = {}
    if os.path.exists(classif_path):
        with open(classif_path) as f:
            classificazioni = json.load(f)

    risultati = {arg: [] for arg in argomenti}
    for i, fpath in enumerate(file_paths):
        fname = Path(fpath).name
        print(f"  [{i+1}/{len(file_paths)}] {fname[:40]}...", end=" ", flush=True)

        if fname in classificazioni:
            arg = classificazioni[fname]
            print(f"(cached: {arg})")
        else:
            arg = _classifica_immagine_ai(fpath, argomenti)
            classificazioni[fname] = arg
            with open(classif_path, 'w') as f:
                json.dump(classificazioni, f, ensure_ascii=False, indent=2)
            print(f"→ {arg}")

        slug = ARGOMENTO_FOLDER_MAP.get(arg, ARGOMENTO_FOLDER_MAP[argomenti[0]])
        dst = os.path.join(output_root, slug, fname)
        if not os.path.exists(dst):
            shutil.copy2(fpath, dst)
        risultati.setdefault(arg, []).append(dst)

    return risultati


def _classifica_per_nome(image_path: str, argomenti: list) -> str:
    """Euristica: indovina l'argomento dal nome del file."""
    nome = Path(image_path).stem.lower()
    parole = nome.replace("-", " ").replace("_", " ").split()
    keywords = {
        "Team E Staff": ["team", "staff", "dott", "dr", "dottor", "equipe", "persona"],
        "Igiene E Prevenzione": ["igiene", "pulizia", "spazzol", "filo", "preventivo"],
        "Implantologia": ["impianto", "implant", "chirurgia", "radiograf", "rx"],
    }
    for arg, words in keywords.items():
        for w in words:
            if any(w in p for p in parole):
                return arg
    return argomenti[0]  # default: Presentazione Studio


def scarica_tutti_media_gdown(cliente: str, root_folder_url: str,
                              classifica_con_ai: bool = True) -> dict:
    """
    Scarica tutti i media dalla cartella Drive del cliente.

    Se le sub-cartelle si chiamano come gli argomenti → usa quella struttura.
    Altrimenti → scarica tutto e classifica con Gemini Vision.

    Ritorna: { argomento: [lista_path_locali] }
    """
    import gdown, shutil

    output_root = os.path.join(BASE, "output", "media", cliente)
    raw_dir = os.path.join(output_root, "_raw")
    os.makedirs(raw_dir, exist_ok=True)

    folder_id = _estrai_folder_id(root_folder_url)
    print(f"[Drive] Scarico da folder: {folder_id}")

    # Scarica tutta la cartella root in _raw/
    try:
        gdown.download_folder(
            f"https://drive.google.com/drive/folders/{folder_id}",
            output=raw_dir,
            quiet=True,
            use_cookies=False
        )
    except Exception as e:
        print(f"[Drive] Errore download: {e}")
        return {}

    # Raccoglie tutti i file immagine scaricati (anche nelle sub-cartelle)
    tutti_file = []
    for root, dirs, files in os.walk(raw_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            if Path(fname).suffix.lower() in SUPPORTED_EXTENSIONS:
                tutti_file.append(fpath)

    print(f"[Drive] {len(tutti_file)} file trovati")

    if not tutti_file:
        return {}

    # Controlla se le sub-cartelle esistono già per argomento
    argomenti = list(ARGOMENTO_FOLDER_MAP.keys())
    folder_slugs = list(ARGOMENTO_FOLDER_MAP.values())

    # Cerca se i file sono già in cartelle con nome argomento
    struttura_argomento = {}
    for fpath in tutti_file:
        parent = Path(fpath).parent.name.lower().replace(" ", "_")
        for arg, slug in ARGOMENTO_FOLDER_MAP.items():
            if slug in parent or parent in slug:
                struttura_argomento.setdefault(arg, []).append(fpath)
                break

    risultati = {}

    if struttura_argomento and len(struttura_argomento) >= 2:
        # Drive già organizzato per argomento
        print("[Drive] Struttura per argomento trovata — copio nelle cartelle locali")
        for arg, files in struttura_argomento.items():
            slug = ARGOMENTO_FOLDER_MAP[arg]
            dest_dir = os.path.join(output_root, slug)
            os.makedirs(dest_dir, exist_ok=True)
            moved = []
            for src in files:
                dst = os.path.join(dest_dir, Path(src).name)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                moved.append(dst)
            risultati[arg] = moved
            print(f"  {arg}: {len(moved)} immagini")

    elif classifica_con_ai:
        # Classifica con Gemini Vision
        print(f"[Drive] Classificazione AI di {len(tutti_file)} immagini con Gemini...")
        for arg in argomenti:
            slug = ARGOMENTO_FOLDER_MAP[arg]
            os.makedirs(os.path.join(output_root, slug), exist_ok=True)
            risultati[arg] = []

        # Carica indice classificazioni (evita di riclassificare)
        classif_path = os.path.join(output_root, "_classificazioni.json")
        classificazioni = {}
        if os.path.exists(classif_path):
            with open(classif_path) as f:
                classificazioni = json.load(f)

        for i, fpath in enumerate(tutti_file):
            fname = Path(fpath).name
            print(f"  [{i+1}/{len(tutti_file)}] {fname[:40]}...", end=" ", flush=True)

            if fname in classificazioni:
                arg = classificazioni[fname]
                print(f"(cached: {arg})")
            else:
                arg = _classifica_immagine_ai(fpath, argomenti)
                classificazioni[fname] = arg
                # Salva subito
                with open(classif_path, 'w') as f:
                    json.dump(classificazioni, f, ensure_ascii=False, indent=2)
                print(f"→ {arg}")

            slug = ARGOMENTO_FOLDER_MAP.get(arg, ARGOMENTO_FOLDER_MAP[argomenti[0]])
            dest_dir = os.path.join(output_root, slug)
            dst = os.path.join(dest_dir, fname)
            if not os.path.exists(dst):
                import shutil
                shutil.copy2(fpath, dst)
            if dst not in risultati.get(arg, []):
                risultati.setdefault(arg, []).append(dst)

    else:
        # Fallback: distribuisce round-robin tra argomenti
        print("[Drive] Nessuna classificazione AI — distribuzione round-robin")
        for j, fpath in enumerate(tutti_file):
            arg = argomenti[j % len(argomenti)]
            slug = ARGOMENTO_FOLDER_MAP[arg]
            dest_dir = os.path.join(output_root, slug)
            os.makedirs(dest_dir, exist_ok=True)
            dst = os.path.join(dest_dir, Path(fpath).name)
            if not os.path.exists(dst):
                import shutil
                shutil.copy2(fpath, dst)
            risultati.setdefault(arg, []).append(dst)

    return risultati


# ── DOWNLOAD VIA Google Drive API v3 (con service account o OAuth) ─────────

def scarica_tutti_media_api(cliente: str, root_folder_id: str,
                             credentials_path: str, classifica_con_ai: bool = True) -> dict:
    """
    Scarica media dal Drive usando le API ufficiali Google.
    credentials_path = path al file JSON del service account o OAuth.
    """
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials
    import io

    output_root = os.path.join(BASE, "output", "media", cliente)
    os.makedirs(output_root, exist_ok=True)

    # Carica credenziali
    with open(credentials_path) as f:
        cred_data = json.load(f)

    if cred_data.get("type") == "service_account":
        creds = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
    else:
        creds = Credentials.from_authorized_user_file(credentials_path)

    service = build("drive", "v3", credentials=creds)

    def lista_file(folder_id: str) -> list:
        risultati = []
        page_token = None
        while True:
            resp = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType)",
                pageToken=page_token
            ).execute()
            risultati.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return risultati

    def scarica_file(file_id: str, dest_path: str):
        req = service.files().get_media(fileId=file_id)
        with open(dest_path, "wb") as fh:
            dl = MediaIoBaseDownload(fh, req)
            done = False
            while not done:
                _, done = dl.next_chunk()

    # Lista sub-cartelle
    sub_folders = [f for f in lista_file(root_folder_id) if "folder" in f["mimeType"]]
    print(f"[Drive API] Trovate {len(sub_folders)} cartelle")

    risultati = {}
    for folder in sub_folders:
        folder_name_raw = folder["name"].lower().replace(" ", "_")
        # mappa al nome argomento
        matched_arg = None
        for argomento, folder_slug in ARGOMENTO_FOLDER_MAP.items():
            if folder_slug in folder_name_raw or folder_name_raw in folder_slug:
                matched_arg = argomento
                break
        if not matched_arg:
            matched_arg = folder["name"]

        dest_dir = os.path.join(output_root, ARGOMENTO_FOLDER_MAP.get(matched_arg, folder_name_raw))
        os.makedirs(dest_dir, exist_ok=True)

        files = [f for f in lista_file(folder["id"]) if "folder" not in f["mimeType"]]
        print(f"  {folder['name']}: {len(files)} file")

        scaricati = []
        for file in files:
            if Path(file["name"]).suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            dest_path = os.path.join(dest_dir, file["name"])
            if not os.path.exists(dest_path):
                print(f"    ↓ {file['name']}")
                scarica_file(file["id"], dest_path)
            scaricati.append(dest_path)

        risultati[matched_arg] = scaricati

    # Se nessuna cartella corrisponde a un argomento (es. struttura "FOTO"/"STORIES"
    # invece di "presentazione_studio"/"igiene_prevenzione"/...) classifica con AI vision
    argomenti = list(ARGOMENTO_FOLDER_MAP.keys())
    if classifica_con_ai and not any(arg in risultati for arg in argomenti):
        immagini = [
            f for files in risultati.values() for f in files
            if Path(f).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        if immagini:
            print(f"[Drive API] Struttura non per argomento — classificazione AI di {len(immagini)} immagini...")
            return _smista_con_ai(cliente, immagini, argomenti)

    return risultati


# ── ENTRYPOINT ─────────────────────────────────────────────────────────────

def _estrai_folder_id(url_or_id: str) -> str:
    m = re.search(r'/folders/([a-zA-Z0-9_-]{25,})', url_or_id)
    return m.group(1) if m else url_or_id


def scarica_media(cliente: str, force_redownload: bool = False) -> dict:
    """
    Scarica i media del cliente da Drive.
    Legge GOOGLE_DRIVE_FOLDER_ID e GOOGLE_CREDENTIALS_PATH dal .env.

    Se GOOGLE_CREDENTIALS_PATH è configurato → usa Drive API.
    Altrimenti → usa gdown (per cartelle Drive pubbliche).

    Ritorna: { argomento: [lista_path_locali] }
    """
    drive_url = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    if not drive_url:
        raise ValueError("Configura GOOGLE_DRIVE_FOLDER_ID nel .env (URL o ID cartella Drive)")

    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "")

    # Controlla se i media sono già stati scaricati
    output_root = os.path.join(BASE, "output", "media", cliente)
    if os.path.exists(output_root) and not force_redownload:
        existing = {}
        for arg, folder_slug in ARGOMENTO_FOLDER_MAP.items():
            folder_path = os.path.join(output_root, folder_slug)
            if os.path.exists(folder_path):
                files = [
                    os.path.join(folder_path, f)
                    for f in sorted(os.listdir(folder_path))
                    if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS
                ]
                if files:
                    existing[arg] = files
        if existing:
            totale = sum(len(v) for v in existing.values())
            print(f"[Drive] Media già presenti ({totale} file). Usa force_redownload=True per aggiornare.")
            return existing

    if credentials_path and os.path.exists(credentials_path):
        folder_id = _estrai_folder_id(drive_url)
        return scarica_tutti_media_api(cliente, folder_id, credentials_path)
    else:
        print("[Drive] Nessuna GOOGLE_CREDENTIALS_PATH configurata → uso gdown (cartella pubblica)")
        return scarica_tutti_media_gdown(cliente, drive_url)


def stampa_stato(cliente: str):
    """Mostra quante immagini ci sono per argomento e quali sono già state usate."""
    output_root = os.path.join(BASE, "output", "media", cliente)
    indice = carica_indice(cliente)

    print(f"\n{'='*50}")
    print(f"MEDIA — {cliente}")
    print(f"{'='*50}")
    for arg, folder_slug in ARGOMENTO_FOLDER_MAP.items():
        folder_path = os.path.join(output_root, folder_slug)
        if not os.path.exists(folder_path):
            print(f"  {arg}: ❌ cartella mancante ({folder_path})")
            continue
        files = [f for f in os.listdir(folder_path) if Path(f).suffix.lower() in SUPPORTED_EXTENSIONS]
        used = [f for f in files if f"{arg}/{f}" in indice]
        print(f"  {arg}: {len(files)} file ({len(used)} usate)")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    import sys
    cliente = sys.argv[1] if len(sys.argv) > 1 else "example"
    force = "--force" in sys.argv

    if "--stato" in sys.argv:
        stampa_stato(cliente)
    else:
        risultati = scarica_media(cliente, force_redownload=force)
        print(f"\n✓ Media pronti:")
        for arg, files in risultati.items():
            print(f"  {arg}: {len(files)} immagini")
