"""
Schedula post su Meta Business Suite via Playwright (browser automation).
Completamente gratuito — nessuna API key richiesta.

Uso: python agente/meta_browser.py example
"""
import json
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE = os.path.join(os.path.dirname(__file__), '..')

MESI_IT = {
    "January": "Gennaio", "February": "Febbraio", "March": "Marzo",
    "April": "Aprile", "May": "Maggio", "June": "Giugno",
    "July": "Luglio", "August": "Agosto", "September": "Settembre",
    "October": "Ottobre", "November": "Novembre", "December": "Dicembre"
}


def carica_ped(cliente: str) -> list:
    s_path = os.path.join(BASE, 'clienti', cliente, 'strategia.json')
    with open(s_path) as f:
        s = json.load(f)
    mesi = s["mesi"]
    anno = s["anno"]
    m1, m2 = mesi[0].lower(), mesi[-1].lower()
    ped_path = os.path.join(BASE, 'output', f'ped_{cliente}_{m1}_{m2}_{anno}.json')
    with open(ped_path) as f:
        return json.load(f)


def schedula_con_browser(cliente: str, fb_email: str, fb_password: str,
                          page_name: str, headless: bool = False):
    """
    Apre Meta Business Suite nel browser e schedula tutti i post del PED.
    headless=False = vedi il browser mentre lavora (utile per debug/primo test).
    """
    from playwright.sync_api import sync_playwright

    ped = carica_ped(cliente)
    print(f"Caricati {len(ped)} post da schedulare.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=800)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        # ── LOGIN FB CON REDIRECT DIRETTO A BUSINESS SUITE ──
        print("\n[1/3] Login Facebook...")
        dest = "https%3A%2F%2Fbusiness.facebook.com%2Flatest%2Fposts%2Fcreate"
        page.goto(f"https://www.facebook.com/login/?next={dest}")
        time.sleep(2)

        # accetta cookies
        try:
            btn = page.get_by_role("button", name="Allow all cookies")
            if not btn.is_visible(timeout=2000):
                btn = page.get_by_role("button", name="Consenti tutti i cookie")
            btn.click(timeout=4000)
            print("  ✓ Cookie accettati")
            time.sleep(1)
            if "login" not in page.url:
                page.goto(f"https://www.facebook.com/login/?next={dest}")
                time.sleep(2)
        except Exception:
            pass

        # compila e invia
        page.locator('input[name="email"]').wait_for(timeout=10000)
        page.locator('input[name="email"]').fill(fb_email)
        time.sleep(0.5)
        page.locator('input[name="pass"]').fill(fb_password)
        time.sleep(0.5)
        page.locator('input[name="pass"]').press("Enter")
        print("  Attendo redirect a Business Suite...")
        time.sleep(10)
        page.screenshot(path=os.path.join(BASE, 'output', 'debug_after_login.png'))
        print(f"  URL: {page.url}")
        print("  ✓ Login completato")

        # ── NAVIGA A CREA POST se non ci siamo già ──
        print("\n[2/3] Apertura editor post...")
        if "posts/create" not in page.url:
            page.goto("https://business.facebook.com/latest/posts/create")
            time.sleep(5)
        page.screenshot(path=os.path.join(BASE, 'output', 'debug_business.png'))
        print(f"  URL editor: {page.url}")
        print("  ✓ Meta Business Suite aperto")

        risultati = []
        errori = []

        # ── CREA OGNI POST ──
        print(f"\n[3/3] Schedulazione {len(ped)} post...")
        for i, post in enumerate(ped):
            try:
                data_str = post["data"]
                orario_str = post.get("orario", "09:00")
                data_ora = datetime.strptime(f"{data_str} {orario_str}", "%Y-%m-%d %H:%M")

                # salta post nel passato
                if data_ora < datetime.now():
                    print(f"  [{i+1}/{len(ped)}] SKIP — data passata: {data_str}")
                    continue

                caption = post["caption"]
                if post.get("hashtag"):
                    caption += f"\n\n{post['hashtag']}"

                print(f"  [{i+1}/{len(ped)}] {data_ora.strftime('%d/%m %H:%M')} — {post['argomento'][:30]}...")

                # Crea post
                page.goto("https://business.facebook.com/latest/posts/create")
                time.sleep(3)

                # Cerca area testo e scrivi caption
                text_area = page.locator('[contenteditable="true"]').first
                text_area.wait_for(timeout=10000)
                text_area.click()
                text_area.fill(caption)
                time.sleep(1)

                # Cerca il pulsante per schedulare
                # (Meta Business Suite ha "Pubblica" e una freccia per "Pianifica")
                schedule_btn = page.locator('text=Pianifica').first
                if not schedule_btn.is_visible():
                    schedule_btn = page.locator('[aria-label*="chedulat"], [aria-label*="ianifica"]').first

                if schedule_btn.is_visible():
                    schedule_btn.click()
                    time.sleep(1)

                    # Imposta data
                    ore, minuti = orario_str.split(":")
                    giorno = data_ora.strftime("%-d")
                    mese = MESI_IT.get(data_ora.strftime("%B"), data_ora.strftime("%B"))
                    anno = data_ora.strftime("%Y")

                    # Cerca input data
                    date_input = page.locator('input[placeholder*="data"], input[type="date"]').first
                    if date_input.is_visible():
                        date_input.fill(data_ora.strftime("%d/%m/%Y"))

                    # Cerca input ora
                    time_input = page.locator('input[placeholder*="ora"], input[type="time"]').first
                    if time_input.is_visible():
                        time_input.fill(orario_str)

                    time.sleep(1)

                    # Conferma pianificazione
                    confirm = page.locator('button:has-text("Pianifica"), button:has-text("Schedule")').last
                    if confirm.is_visible():
                        confirm.click()
                        time.sleep(3)
                        print(f"    ✓ Schedulato per {data_ora.strftime('%d/%m/%Y %H:%M')}")
                        risultati.append({"numero": post["numero"], "stato": "schedulato", "data_ora": data_ora.isoformat()})
                    else:
                        print(f"    ⚠ Bottone conferma non trovato — screenshot salvato")
                        page.screenshot(path=os.path.join(BASE, 'output', f'debug_{i}.png'))
                        errori.append(post["numero"])
                else:
                    print(f"    ⚠ Bottone pianifica non trovato — salvo screenshot")
                    page.screenshot(path=os.path.join(BASE, 'output', f'debug_{i}.png'))
                    errori.append(post["numero"])

                time.sleep(2)

            except Exception as e:
                print(f"    ✗ Errore post {post['numero']}: {e}")
                errori.append(post["numero"])
                try:
                    page.screenshot(path=os.path.join(BASE, 'output', f'debug_err_{i}.png'))
                except Exception:
                    pass

        browser.close()

        # Report finale
        report_path = os.path.join(BASE, 'output', f'browser_report_{cliente}.json')
        with open(report_path, 'w') as f:
            json.dump({"schedulati": risultati, "errori": errori}, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*50}")
        print(f"✓ Schedulati: {len(risultati)}/{len(ped)}")
        if errori:
            print(f"✗ Errori su post: {errori}")
        print(f"Report: {report_path}")
        return risultati


if __name__ == "__main__":
    cliente = sys.argv[1] if len(sys.argv) > 1 else "example"

    fb_email = os.getenv("FB_EMAIL", "")
    fb_password = os.getenv("FB_PASSWORD", "")
    page_name = os.getenv("FB_PAGE_NAME", "")

    if not fb_email or not fb_password:
        print("Aggiungi nel .env:")
        print("  FB_EMAIL=tuaemail@esempio.com")
        print("  FB_PASSWORD=tuapassword")
        print("  FB_PAGE_NAME=nome della pagina")
        sys.exit(1)

    # Prima esecuzione: headless=False per vedere cosa fa e verificare
    schedula_con_browser(cliente, fb_email, fb_password, page_name, headless=False)
