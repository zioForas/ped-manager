"""
Invia il PDF del PED al cliente via Gmail
con link Approva / Richiedi Modifiche generati da ngrok.
"""
import json
import os
import secrets
import smtplib
import time
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

SESSIONI_PATH = os.path.join(os.path.dirname(__file__), '..', 'output', 'sessioni.json')

HTML_MAIL = """
<!DOCTYPE html>
<html lang="it">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">

  <div style="background: #2962ff; padding: 24px; border-radius: 12px 12px 0 0; text-align: center;">
    <h1 style="color: white; margin: 0; font-size: 22px;">Piano Editoriale</h1>
    <p style="color: rgba(255,255,255,0.8); margin: 6px 0 0;">
      {mese1} &ndash; {mese2} {anno} &bull; Instagram + Facebook
    </p>
  </div>

  <div style="background: #f8faff; padding: 28px; border: 1px solid #e0e8ff;">
    <p>Gentile <strong>{nome_cliente}</strong>,</p>
    <p>in allegato trovate il <strong>Piano Editoriale</strong> per i mesi di <strong>{mese1}&ndash;{mese2} {anno}</strong>.</p>
    <p>Il piano include:</p>
    <ul>
      <li><strong>{n_post} post</strong> (Instagram + Facebook) con copy, hashtag e orari</li>
      <li><strong>{n_stories} stories</strong> (originali + repost)</li>
    </ul>
    <p>Vi chiediamo di esaminarlo e comunicarci la vostra risposta cliccando uno dei pulsanti:</p>

    <div style="text-align: center; margin: 32px 0;">
      <a href="{url_approva}" style="background: #2962ff; color: white; padding: 14px 32px;
         border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold;
         margin-right: 12px; display: inline-block;">
        ✓ Approva
      </a>
      <a href="{url_modifiche}" style="background: #f97316; color: white; padding: 14px 32px;
         border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold;
         display: inline-block;">
        ✎ Richiedi modifiche
      </a>
    </div>

    <p style="color: #666; font-size: 13px;">
      I link sono personali e validi per questo piano editoriale.<br>
      Per qualsiasi dubbio potete rispondere a questa email.
    </p>
  </div>

  <div style="background: #2962ff; padding: 14px; border-radius: 0 0 12px 12px; text-align: center;">
    <p style="color: rgba(255,255,255,0.7); font-size: 11px; margin: 0;">
      Piano generato il {data_oggi}
    </p>
  </div>

</body>
</html>
"""

def genera_token():
    return secrets.token_urlsafe(24)

def crea_sessione(token, cliente, pdf_path, mesi, anno):
    os.makedirs(os.path.dirname(SESSIONI_PATH), exist_ok=True)
    sessioni = {}
    if os.path.exists(SESSIONI_PATH):
        with open(SESSIONI_PATH) as f:
            sessioni = json.load(f)
    sessioni[token] = {
        "cliente": cliente,
        "pdf_path": pdf_path,
        "mesi": mesi,
        "anno": anno,
        "stato": "in_attesa",
        "data_invio": datetime.now().isoformat(),
        "note_modifiche": ""
    }
    with open(SESSIONI_PATH, 'w') as f:
        json.dump(sessioni, f, ensure_ascii=False, indent=2)

def _invia_brevo(api_key, mittente, nome_mittente, email_cliente, oggetto, corpo, pdf_path):
    """Invio via Brevo HTTP API (https://api.brevo.com/v3/smtp/email).
    Usato in cloud dove le porte SMTP in uscita sono bloccate."""
    import base64
    import requests

    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "sender": {"email": mittente, "name": nome_mittente or "PED Manager"},
        "to": [{"email": email_cliente}],
        "subject": oggetto,
        "htmlContent": corpo,
        "attachment": [{"content": pdf_b64, "name": os.path.basename(pdf_path)}],
    }
    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": api_key, "content-type": "application/json",
                 "accept": "application/json"},
        json=payload, timeout=30,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Invio email Brevo fallito (HTTP {r.status_code}): {r.text}")


def _invia_smtp(gmail_user, gmail_pass, email_cliente, oggetto, corpo, pdf_path):
    """Invio via Gmail SMTP (porta 465). Funziona in locale; in cloud spesso
    la porta è bloccata — in quel caso usa Brevo (vedi BREVO_API_KEY)."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = oggetto
    msg["From"] = gmail_user
    msg["To"] = email_cliente
    msg.attach(MIMEText(corpo, "html"))
    with open(pdf_path, "rb") as f:
        pdf_allegato = MIMEApplication(f.read(), _subtype="pdf")
        pdf_allegato.add_header("Content-Disposition", "attachment",
                                filename=os.path.basename(pdf_path))
        msg.attach(pdf_allegato)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=25) as smtp:
            smtp.login(gmail_user, gmail_pass)
            smtp.sendmail(gmail_user, email_cliente, msg.as_string())
    except (smtplib.SMTPException, OSError) as e:
        raise RuntimeError(
            f"Invio email SMTP fallito ({type(e).__name__}: {e}). "
            "Se siamo in cloud, l'hosting blocca la porta SMTP 465: "
            "imposta BREVO_API_KEY per usare l'invio via HTTP."
        ) from e


def invia_pdf(pdf_path: str, cliente: str, email_cliente: str,
              mesi: list, anno: int, n_post: int, n_stories: int,
              base_url: str) -> str:
    brevo_key = os.getenv("BREVO_API_KEY", "")
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    # mittente: in cloud (Brevo) serve un sender verificato — usa BREVO_SENDER
    # se impostato, altrimenti ripiega su GMAIL_USER.
    mittente = os.getenv("BREVO_SENDER", "") or gmail_user

    if not brevo_key and (not gmail_user or not gmail_pass):
        raise ValueError("Configura BREVO_API_KEY (cloud) oppure GMAIL_USER + GMAIL_APP_PASSWORD (locale)")

    token = genera_token()
    crea_sessione(token, cliente, pdf_path, mesi, anno)

    url_approva = f"{base_url}/approva?token={token}"
    url_modifiche = f"{base_url}/modifiche?token={token}"

    corpo = HTML_MAIL.format(
        nome_cliente=cliente,
        mese1=mesi[0], mese2=mesi[-1], anno=anno,
        n_post=n_post, n_stories=n_stories,
        url_approva=url_approva,
        url_modifiche=url_modifiche,
        data_oggi=datetime.now().strftime("%d/%m/%Y")
    )
    oggetto = f"Piano Editoriale {mesi[0]}-{mesi[-1]} {anno} - {cliente}"

    if brevo_key:
        _invia_brevo(brevo_key, mittente, os.getenv("BREVO_SENDER_NAME", "PED Manager"),
                     email_cliente, oggetto, corpo, pdf_path)
    else:
        _invia_smtp(gmail_user, gmail_pass, email_cliente, oggetto, corpo, pdf_path)

    print(f"OK Mail inviata a {email_cliente}")
    print(f"   Token: {token}")
    print(f"   Approva: {url_approva}")
    print(f"   Modifiche: {url_modifiche}")
    return token

def attendi_risposta(token: str, timeout_minuti: int = 1440) -> dict:
    """Aspetta che il cliente risponda (polling ogni 30 secondi)."""
    print(f"In attesa risposta cliente (timeout {timeout_minuti} min)...")
    intervallo = 30
    tentativi = (timeout_minuti * 60) // intervallo

    for i in range(tentativi):
        with open(SESSIONI_PATH) as f:
            sessioni = json.load(f)
        s = sessioni.get(token, {})
        stato = s.get("stato", "in_attesa")

        if stato != "in_attesa":
            print(f"Risposta ricevuta: {stato}")
            return s

        if i % 20 == 0:
            print(f"  Attendo... ({i * intervallo // 60} min passati)")
        time.sleep(intervallo)

    return {"stato": "timeout"}
