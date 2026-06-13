"""
Crea design Canva via Playwright per ogni post del PED.
Formato: 1080x1350px (4:5) per Instagram e Facebook.

Flusso per ogni post:
  1. Apri Canva, login
  2. Crea nuovo design 1080x1350
  3. Carica immagine di sfondo dal Drive (output/media/)
  4. Aggiungi testo: titolo argomento + caption breve + hashtag
  5. Esporta PNG → output/designs/{cliente}/post_{numero}.png

Prerequisiti nel .env:
  CANVA_EMAIL=...
  CANVA_PASSWORD=...
"""
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE = os.path.join(os.path.dirname(__file__), '..')

ARGOMENTO_COLORI = {
    "Presentazione Studio": "#2962FF",
    "Igiene E Prevenzione": "#22C55E",
    "Team E Staff":         "#F97316",
    "Implantologia":        "#A855F7",
}

DESIGN_W = 1080
DESIGN_H = 1350


# ── FALLBACK LOCALE (Pillow) ────────────────────────────────────────────────

def crea_design_locale(post: dict, image_path: str | None, cliente: str) -> str:
    """
    Genera il design con Pillow (senza Canva).
    Usato come fallback se Canva non è configurato o come preview veloce.
    Output: output/designs/{cliente}/post_{numero}.png
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import textwrap

    output_dir = os.path.join(BASE, "output", "designs", cliente)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"post_{post['numero']:02d}.png")

    # Crea canvas
    canvas = Image.new("RGB", (DESIGN_W, DESIGN_H), "#FFFFFF")

    # Sfondo: immagine o gradiente colorato
    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path).convert("RGB")
            # crop center 4:5
            w, h = img.size
            target_ratio = DESIGN_W / DESIGN_H
            current_ratio = w / h
            if current_ratio > target_ratio:
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            else:
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                img = img.crop((0, top, w, top + new_h))
            img = img.resize((DESIGN_W, DESIGN_H), Image.LANCZOS)
            canvas.paste(img, (0, 0))

            # overlay scuro in basso per leggibilità testo
            overlay = Image.new("RGBA", (DESIGN_W, DESIGN_H), (0, 0, 0, 0))
            draw_ov = ImageDraw.Draw(overlay)
            for y in range(DESIGN_H // 2, DESIGN_H):
                alpha = int(180 * (y - DESIGN_H // 2) / (DESIGN_H // 2))
                draw_ov.line([(0, y), (DESIGN_W, y)], fill=(0, 0, 0, alpha))
            canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
        except Exception as e:
            print(f"    ⚠ Immagine non caricabile: {e}")
    else:
        # gradiente colorato come sfondo
        colore_hex = ARGOMENTO_COLORI.get(post.get("argomento", ""), "#2962FF")
        r = int(colore_hex[1:3], 16)
        g = int(colore_hex[3:5], 16)
        b = int(colore_hex[5:7], 16)
        draw_bg = ImageDraw.Draw(canvas)
        for y in range(DESIGN_H):
            factor = y / DESIGN_H
            rc = int(r * (1 - factor * 0.6))
            gc = int(g * (1 - factor * 0.6))
            bc = int(b * (1 - factor * 0.6))
            draw_bg.line([(0, y), (DESIGN_W, y)], fill=(rc, gc, bc))

    draw = ImageDraw.Draw(canvas)

    # Carica font (system font come fallback)
    def get_font(size: int, bold: bool = False):
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    from PIL import ImageFont
                    return ImageFont.truetype(fp, size)
                except Exception:
                    continue
        from PIL import ImageFont
        return ImageFont.load_default()

    # Badge argomento (pill colorata in alto)
    arg = post.get("argomento", "")
    colore_hex = ARGOMENTO_COLORI.get(arg, "#2962FF")
    badge_r = int(colore_hex[1:3], 16)
    badge_g = int(colore_hex[3:5], 16)
    badge_b = int(colore_hex[5:7], 16)
    badge_font = get_font(32, bold=True)
    badge_text = arg.upper()
    badge_padding = 24
    badge_h = 56

    # Misura testo badge
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w = bbox[2] - bbox[0] + badge_padding * 2

    badge_x = 60
    badge_y = 60
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h],
        radius=28,
        fill=(badge_r, badge_g, badge_b)
    )
    draw.text(
        (badge_x + badge_padding, badge_y + badge_h // 2),
        badge_text,
        font=badge_font,
        fill="white",
        anchor="lm"
    )

    # Numero post (in alto a destra)
    num_font = get_font(28)
    draw.text((DESIGN_W - 60, badge_y + badge_h // 2), f"#{post['numero']:02d}",
              font=num_font, fill=(255, 255, 255, 200), anchor="rm")

    # Caption (testo principale in basso)
    caption = post.get("caption", "")
    max_chars = 180
    if len(caption) > max_chars:
        caption = caption[:max_chars].rsplit(" ", 1)[0] + "…"

    caption_font = get_font(44)
    wrapped = textwrap.wrap(caption, width=30)
    line_height = 54
    total_text_h = len(wrapped) * line_height
    text_y = DESIGN_H - total_text_h - 160
    text_x = 60

    for line in wrapped:
        draw.text((text_x, text_y), line, font=caption_font, fill="white")
        text_y += line_height

    # Data e ora
    data_font = get_font(32)
    data_str = f"{post.get('data', '')}  {post.get('orario', '')}"
    draw.text((60, DESIGN_H - 100), data_str, font=data_font, fill=(200, 200, 200))

    # Hashtag (in basso a destra, piccolo)
    hashtag = post.get("hashtag", "")[:60] + "…" if len(post.get("hashtag", "")) > 60 else post.get("hashtag", "")
    hash_font = get_font(24)
    draw.text((60, DESIGN_H - 60), hashtag, font=hash_font, fill=(180, 220, 255))

    canvas.save(output_path, "PNG", quality=95)
    print(f"  ✓ Design locale: {output_path}")
    return output_path


# ── CANVA VIA PLAYWRIGHT ────────────────────────────────────────────────────

class CanvaDesigner:
    """Gestisce una sessione Canva via Playwright. Mantiene login tra più design."""

    def __init__(self, email: str, password: str, headless: bool = True):
        self.email = email
        self.password = password
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._page = None
        self._logged_in = False

    def avvia(self):
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=600,
            args=["--no-sandbox"]
        )
        ctx = self._browser.new_context(
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
            locale="it-IT"
        )
        self._page = ctx.new_page()

    def chiudi(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def login(self) -> bool:
        p = self._page
        print("  [Canva] Login...")
        p.goto("https://www.canva.com/login")
        time.sleep(2)

        # Accetta cookies se presenti
        try:
            p.locator('button:has-text("Accetta"), button:has-text("Accept")').first.click(timeout=3000)
            time.sleep(1)
        except Exception:
            pass

        # Click "Continua con email"
        try:
            p.locator('button:has-text("Continua con email"), button:has-text("Continue with email")').first.click(timeout=5000)
            time.sleep(1)
        except Exception:
            pass

        # Inserisce email
        email_input = p.locator('input[name="email"], input[type="email"]').first
        email_input.wait_for(timeout=10000)
        email_input.fill(self.email)

        try:
            p.locator('button[type="submit"]').first.click(timeout=3000)
            time.sleep(1)
        except Exception:
            email_input.press("Enter")
            time.sleep(1)

        # Password
        try:
            pwd_input = p.locator('input[type="password"]').first
            pwd_input.wait_for(timeout=8000)
            pwd_input.fill(self.password)
            p.locator('button[type="submit"]').first.click(timeout=3000)
        except Exception:
            pass

        time.sleep(4)

        # Verifica login
        if "canva.com/design" in p.url or "canva.com/home" in p.url or "canva.com/folders" in p.url:
            self._logged_in = True
            print("  [Canva] ✓ Login completato")
            return True

        # Fallback: controlla se c'è l'icona utente
        try:
            p.locator('[data-testid="user-menu"], [aria-label*="account"], [aria-label*="Account"]').first.wait_for(timeout=5000)
            self._logged_in = True
            print("  [Canva] ✓ Login completato")
            return True
        except Exception:
            print(f"  [Canva] ⚠ Login incerto — URL: {p.url}")
            return False

    def crea_design(self, post: dict, image_path: str | None, cliente: str,
                    download_dir: str) -> str | None:
        """
        Crea un design Canva 1080x1350 e lo scarica come PNG.
        Ritorna il path locale del PNG scaricato.
        """
        p = self._page

        output_dir = os.path.join(BASE, "output", "designs", cliente)
        os.makedirs(output_dir, exist_ok=True)
        filename = f"post_{post['numero']:02d}.png"
        output_path = os.path.join(output_dir, filename)

        if os.path.exists(output_path):
            print(f"  [Canva] Design già presente: {filename}")
            return output_path

        print(f"  [Canva] Creo design per post #{post['numero']} — {post['argomento']}")

        # Nuovo design con dimensioni custom
        p.goto("https://www.canva.com/design/create?type=custom")
        time.sleep(3)

        # Imposta dimensioni 1080x1350
        try:
            # Cerca "Dimensioni personalizzate" o campo larghezza
            w_input = p.locator('input[aria-label*="Width"], input[aria-label*="Larghezza"], input[placeholder*="1080"]').first
            w_input.wait_for(timeout=6000)
            w_input.triple_click()
            w_input.fill("1080")
            time.sleep(0.3)

            h_input = p.locator('input[aria-label*="Height"], input[aria-label*="Altezza"], input[placeholder*="1350"]').first
            h_input.triple_click()
            h_input.fill("1350")
            time.sleep(0.3)

            # Conferma creazione
            p.locator('button:has-text("Crea"), button:has-text("Create new design")').first.click(timeout=4000)
            time.sleep(5)
        except Exception as e:
            print(f"  [Canva] ⚠ Impostazione dimensioni: {e}")
            # Prova apertura diretta editor
            p.goto("https://www.canva.com/design/new?type=custom&w=1080&h=1350&units=px")
            time.sleep(5)

        # Carica immagine di sfondo
        if image_path and os.path.exists(image_path):
            try:
                self._carica_immagine(image_path)
            except Exception as e:
                print(f"  [Canva] ⚠ Upload immagine: {e}")

        # Aggiungi testo
        try:
            self._aggiungi_testo(post)
        except Exception as e:
            print(f"  [Canva] ⚠ Aggiunta testo: {e}")

        # Scarica come PNG
        try:
            return self._scarica_design(output_path, download_dir)
        except Exception as e:
            print(f"  [Canva] ⚠ Download: {e}")
            return None

    def _carica_immagine(self, image_path: str):
        p = self._page
        print(f"    Carico immagine: {Path(image_path).name}")

        # Click su "Carica" nel pannello sinistro
        try:
            p.locator('[data-testid="upload-button"], button:has-text("Carica"), button:has-text("Upload")').first.click(timeout=4000)
            time.sleep(1)
        except Exception:
            # Apri pannello upload tramite menu
            try:
                p.locator('button:has-text("Carica file"), button:has-text("Upload files")').first.click(timeout=4000)
                time.sleep(1)
            except Exception:
                pass

        # Upload file
        with p.expect_file_chooser() as fc_info:
            try:
                p.locator('[data-testid="upload-file-button"], input[type="file"]').first.click(timeout=4000)
            except Exception:
                p.locator('button:has-text("Carica")').last.click(timeout=4000)

        fc = fc_info.value
        fc.set_files(image_path)
        time.sleep(4)

        # Click sul file appena caricato per aggiungerlo al canvas
        try:
            uploaded = p.locator('[data-testid="uploaded-image"]').last
            uploaded.wait_for(timeout=10000)
            uploaded.dblclick()
            time.sleep(2)
        except Exception:
            # Prova click sull'ultima miniatura
            try:
                p.locator('[class*="thumbnail"]').last.dblclick(timeout=4000)
                time.sleep(2)
            except Exception:
                pass

        print("    ✓ Immagine caricata")

    def _aggiungi_testo(self, post: dict):
        p = self._page
        arg = post.get("argomento", "")
        caption = post.get("caption", "")
        if len(caption) > 150:
            caption = caption[:150].rsplit(" ", 1)[0] + "…"

        # Click "Testo" nel menu laterale
        try:
            p.locator('[data-testid="text-button"], button[aria-label*="Testo"], button[aria-label*="Text"]').first.click(timeout=4000)
            time.sleep(1)
        except Exception:
            pass

        # Aggiungi titolo (argomento)
        try:
            p.locator('button:has-text("Aggiungi testo"), button:has-text("Add a text box"), [data-testid="add-body-text"]').first.click(timeout=4000)
            time.sleep(0.5)
            p.keyboard.type(arg.upper())
            time.sleep(0.5)
            p.keyboard.press("Escape")
            time.sleep(0.5)
        except Exception:
            pass

        # Aggiungi caption
        try:
            p.locator('button:has-text("Aggiungi testo"), button:has-text("Add a text box")').first.click(timeout=4000)
            time.sleep(0.5)
            p.keyboard.type(caption)
            time.sleep(0.5)
            p.keyboard.press("Escape")
        except Exception:
            pass

        print("    ✓ Testo aggiunto")

    def _scarica_design(self, output_path: str, download_dir: str) -> str:
        p = self._page
        print("    Scarico PNG...")

        # Click bottone Download
        try:
            p.locator('button[aria-label*="Download"], button:has-text("Scarica"), button:has-text("Download")').first.click(timeout=6000)
            time.sleep(2)
        except Exception:
            # Prova via menu File
            p.keyboard.press("Control+Shift+E")
            time.sleep(2)

        # Seleziona formato PNG se non già selezionato
        try:
            format_select = p.locator('select[aria-label*="format"], [data-testid="format-select"]').first
            format_select.select_option("PNG")
            time.sleep(0.5)
        except Exception:
            try:
                p.locator('button:has-text("PNG")').first.click(timeout=3000)
                time.sleep(0.5)
            except Exception:
                pass

        # Click "Scarica" nel modal
        with p.expect_download(timeout=30000) as dl_info:
            try:
                p.locator('button:has-text("Scarica"), button:has-text("Download")').last.click(timeout=5000)
            except Exception:
                p.locator('[data-testid="download-button"]').click(timeout=5000)

        download = dl_info.value
        download.save_as(output_path)
        print(f"    ✓ Salvato: {Path(output_path).name}")
        return output_path


# ── PIPELINE COMPLETA ───────────────────────────────────────────────────────

def crea_tutti_designs(cliente: str, ped: list, usa_canva: bool = True,
                       headless: bool = True) -> dict:
    """
    Per ogni post nel PED:
      1. Trova l'immagine giusta da output/media/{cliente}/{argomento}/
      2. Crea il design (Canva o locale)
      3. Salva path in post['design_path']
      4. Aggiorna l'indice media

    Ritorna il PED aggiornato con 'design_path' per ogni post.
    """
    from media_finder import prossima_immagine, marca_usata

    canva_email = os.getenv("CANVA_EMAIL", "")
    canva_password = os.getenv("CANVA_PASSWORD", "")

    usa_canva_effettivo = usa_canva and bool(canva_email) and bool(canva_password)
    if usa_canva and not usa_canva_effettivo:
        print("[Canva] ⚠ CANVA_EMAIL/CANVA_PASSWORD mancanti nel .env → uso design locale (Pillow)")

    output_dir = os.path.join(BASE, "output", "designs", cliente)
    os.makedirs(output_dir, exist_ok=True)

    designer = None
    if usa_canva_effettivo:
        designer = CanvaDesigner(canva_email, canva_password, headless=headless)
        designer.avvia()
        ok = designer.login()
        if not ok:
            print("[Canva] Login fallito → fallback design locale")
            designer.chiudi()
            designer = None
            usa_canva_effettivo = False

    ped_aggiornato = []
    try:
        for post in ped:
            argomento = post.get("argomento", "")
            image_path = prossima_immagine(cliente, argomento)

            print(f"\n[{post['numero']}/{len(ped)}] {argomento}")
            if image_path:
                print(f"  Immagine: {Path(image_path).name}")
            else:
                print(f"  ⚠ Nessuna immagine trovata per '{argomento}' — design con colore")

            if usa_canva_effettivo and designer:
                design_path = designer.crea_design(post, image_path, cliente, output_dir)
                if not design_path:
                    print("  [Canva] Fallback design locale")
                    design_path = crea_design_locale(post, image_path, cliente)
            else:
                design_path = crea_design_locale(post, image_path, cliente)

            if design_path and image_path:
                marca_usata(cliente, argomento, Path(image_path).name, post["numero"])

            post_aggiornato = {**post, "design_path": design_path or ""}
            ped_aggiornato.append(post_aggiornato)

    finally:
        if designer:
            designer.chiudi()

    # Salva PED aggiornato con i path dei design
    mesi_map = {"Gennaio":1,"Febbraio":2,"Marzo":3,"Aprile":4,"Maggio":5,
                "Giugno":6,"Luglio":7,"Agosto":8,"Settembre":9,"Ottobre":10,
                "Novembre":11,"Dicembre":12}

    ped_path = os.path.join(BASE, "output",
        f"ped_{cliente}_con_design.json")
    with open(ped_path, 'w', encoding='utf-8') as f:
        json.dump(ped_aggiornato, f, ensure_ascii=False, indent=2)

    ok_count = sum(1 for p in ped_aggiornato if p.get("design_path"))
    print(f"\n✓ Design creati: {ok_count}/{len(ped_aggiornato)}")
    print(f"✓ PED aggiornato: {ped_path}")
    return ped_aggiornato


if __name__ == "__main__":
    import sys

    cliente = sys.argv[1] if len(sys.argv) > 1 else "example"
    usa_canva = "--canva" in sys.argv
    headless = "--headless" in sys.argv
    solo_locale = "--locale" in sys.argv or not usa_canva

    # Carica PED
    s_path = os.path.join(BASE, 'clienti', cliente, 'strategia.json')
    with open(s_path) as f:
        strategia = json.load(f)

    mesi = strategia["mesi"]
    anno = strategia["anno"]
    ped_path = os.path.join(BASE, 'output',
        f'ped_{cliente}_{mesi[0].lower()}_{mesi[-1].lower()}_{anno}.json')

    with open(ped_path) as f:
        ped = json.load(f)

    if solo_locale:
        print("=== DESIGN LOCALE (Pillow) ===")
        from media_finder import prossima_immagine, marca_usata
        for post in ped:
            image_path = prossima_immagine(cliente, post["argomento"])
            design = crea_design_locale(post, image_path, cliente)
            print(f"  Post #{post['numero']}: {design}")
    else:
        crea_tutti_designs(cliente, ped, usa_canva=usa_canva, headless=headless)
