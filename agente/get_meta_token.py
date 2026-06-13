"""
Genera un Facebook Page Access Token (non-expiring) con pages_manage_posts
tramite OAuth flow locale. Apre il browser, tu autorizzi,
lo script salva il token nel .env automaticamente.

Uso: python agente/get_meta_token.py
"""
import os
import sys
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv, set_key
import requests

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

BASE       = os.path.join(os.path.dirname(__file__), '..')
ENV_PATH   = os.path.join(BASE, '.env')
PORT       = 8765
REDIRECT   = f"http://localhost:{PORT}/callback"
SCOPES     = "pages_manage_posts,pages_read_engagement,pages_show_list"

APP_ID     = os.getenv("META_APP_ID", "")
APP_SECRET = os.getenv("META_APP_SECRET", "")

token_result = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            error = params.get("error_description", ["Errore sconosciuto"])[0]

            if code:
                # Step 1: scambia code per short-lived user token
                r = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
                    "client_id": APP_ID,
                    "redirect_uri": REDIRECT,
                    "client_secret": APP_SECRET,
                    "code": code
                })
                data = r.json()
                if "access_token" in data:
                    short_token = data["access_token"]

                    # Step 2: scambia short-lived → long-lived user token (60 giorni)
                    r2 = requests.get("https://graph.facebook.com/v19.0/oauth/access_token", params={
                        "grant_type": "fb_exchange_token",
                        "client_id": APP_ID,
                        "client_secret": APP_SECRET,
                        "fb_exchange_token": short_token
                    })
                    data2 = r2.json()
                    long_token = data2.get("access_token", short_token)
                    token_result["token"] = long_token
                    msg = b"<h2>Autorizzazione completata! Torna al terminale.</h2>"
                else:
                    token_result["errore"] = str(data)
                    msg = f"<h2>Errore: {data}</h2>".encode()
            else:
                token_result["errore"] = error
                msg = f"<h2>Errore: {error}</h2>".encode()

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(msg)
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, *args):
        pass


def main():
    if not APP_ID or not APP_SECRET:
        print("Aggiungi nel .env:")
        print("  META_APP_ID=il tuo App ID (es: 1548263906973159)")
        print("  META_APP_SECRET=il tuo App Secret")
        print("\nTrovi entrambi su developers.facebook.com → PED → Impostazioni → Di base")
        sys.exit(1)

    auth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT}"
        f"&scope={SCOPES}"
        f"&response_type=code"
        f"&auth_type=rerequest"
    )

    print("Apro il browser per l'autorizzazione Facebook...")
    print(f"Se il browser non si apre, vai su:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", PORT), Handler)
    print(f"Attendo autorizzazione su http://localhost:{PORT}...")
    server.serve_forever()

    if "token" in token_result:
        long_token = token_result["token"]
        print(f"\n✓ Long-lived user token ottenuto (60 giorni)")

        set_key(ENV_PATH, "META_ACCESS_TOKEN", long_token)

        # Step 3: ottieni Page Access Token (NON SCADE MAI)
        r = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={
            "fields": "id,name,access_token,instagram_business_account",
            "access_token": long_token
        })
        accounts = r.json().get("data", [])

        if accounts:
            print("\nPagine trovate:")
            for i, acc in enumerate(accounts):
                ig = acc.get("instagram_business_account", {}).get("id", "—")
                print(f"  [{i}] {acc['name']} | FB: {acc['id']} | IG: {ig} | Token: {acc.get('access_token','')[:20]}...")

            # verifica permessi del page token
            page_token = accounts[0].get("access_token", long_token)
            r_debug = requests.get("https://graph.facebook.com/debug_token", params={
                "input_token": page_token,
                "access_token": f"{APP_ID}|{APP_SECRET}"
            })
            debug = r_debug.json().get("data", {})
            scopes = debug.get("scopes", [])
            expires = debug.get("expires_at", 0)
            print(f"\n  Permessi page token: {scopes}")
            print(f"  Scade il: {'MAI (0)' if expires == 0 else expires}")
            print(f"  pages_manage_posts: {'✓ SI' if 'pages_manage_posts' in scopes else '✗ NO'}")

            set_key(ENV_PATH, "META_PAGE_ID_FB", accounts[0]["id"])
            set_key(ENV_PATH, "META_PAGE_ACCESS_TOKEN", page_token)

            if accounts[0].get("instagram_business_account"):
                ig_id = accounts[0]["instagram_business_account"]["id"]
                set_key(ENV_PATH, "META_INSTAGRAM_ACCOUNT_ID", ig_id)
                print(f"\n  Instagram Business Account ID: {ig_id}")

            print(f"\n✓ Tutto salvato nel .env!")
            print("Ora puoi eseguire: python agente/meta_poster.py example --dry")

            if "pages_manage_posts" not in scopes:
                print("\n⚠️  ATTENZIONE: pages_manage_posts mancante.")
                print("   Vai su developers.facebook.com → PED → Aggiungi prodotto → Facebook Login")
                print("   Poi: Permissions and Features → cerca 'pages_manage_posts' → Add")
                print("   Poi ri-esegui questo script.")
        else:
            print("Nessuna pagina trovata. Assicurati di avere admin su almeno una pagina FB.")
    else:
        print(f"\n✗ Errore: {token_result.get('errore')}")


if __name__ == "__main__":
    main()
