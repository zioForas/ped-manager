"""
Server locale di approvazione PED.
Riceve i click dei clienti su Approva / Richiedi Modifiche
e salva lo stato nel file di sessione.
"""
import json
import os
import threading
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

SESSIONI_PATH = os.path.join(os.path.dirname(__file__), '..', 'output', 'sessioni.json')

HTML_APPROVA = """
<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<title>Piano Editoriale Approvato</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f0f7ff;}
.box{background:white;padding:40px;border-radius:16px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.1);max-width:480px;}
h1{color:#2962ff;} p{color:#555;} .icon{font-size:64px;}</style></head>
<body><div class="box"><div class="icon">✅</div>
<h1>Piano Approvato!</h1>
<p>Grazie {{ nome }}. Il piano editoriale è stato approvato.<br>
Procederemo con la programmazione dei contenuti su Instagram e Facebook.</p>
<p style="color:#aaa;font-size:12px;">{{ data }}</p>
</div></body></html>
"""

HTML_MODIFICHE = """
<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8">
<title>Richiedi Modifiche</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f0f7ff;}
.box{background:white;padding:40px;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.1);max-width:520px;width:90%;}
h1{color:#f97316;} textarea{width:100%;height:140px;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:14px;resize:vertical;}
button{background:#f97316;color:white;border:none;padding:12px 28px;border-radius:8px;font-size:16px;cursor:pointer;margin-top:12px;width:100%;}
button:hover{background:#ea6c10;}</style></head>
<body><div class="box">
<h1>Richiedi Modifiche</h1>
<p>Scrivi qui le modifiche che desideri per il piano editoriale <strong>{{ cliente }}</strong>:</p>
<form method="POST">
<textarea name="note" placeholder="Es: cambia il post del 15 giugno, tono troppo formale..."></textarea><br>
<button type="submit">Invia Modifiche</button>
</form></div></body></html>
"""

HTML_GRAZIE = """
<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><title>Grazie</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;background:#f0f7ff;}
.box{background:white;padding:40px;border-radius:16px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,0.1);}
h1{color:#f97316;} .icon{font-size:64px;}</style></head>
<body><div class="box"><div class="icon">📝</div>
<h1>Modifiche ricevute!</h1>
<p>Grazie. Elaboreremo le modifiche e ti invieremo un nuovo piano aggiornato a breve.</p>
</div></body></html>
"""

def carica_sessioni():
    if os.path.exists(SESSIONI_PATH):
        with open(SESSIONI_PATH) as f:
            return json.load(f)
    return {}

def salva_sessione(token, dati):
    sessioni = carica_sessioni()
    sessioni[token] = dati
    os.makedirs(os.path.dirname(SESSIONI_PATH), exist_ok=True)
    with open(SESSIONI_PATH, 'w') as f:
        json.dump(sessioni, f, ensure_ascii=False, indent=2)

@app.route("/approva")
def approva():
    token = request.args.get("token", "")
    sessioni = carica_sessioni()
    if token not in sessioni:
        return "Link non valido.", 404
    s = sessioni[token]
    salva_sessione(token, {**s, "stato": "approvato", "data_risposta": datetime.now().isoformat()})
    return render_template_string(HTML_APPROVA,
                                  nome=s.get("cliente", ""),
                                  data=datetime.now().strftime("%d/%m/%Y %H:%M"))

@app.route("/modifiche", methods=["GET", "POST"])
def modifiche():
    token = request.args.get("token", "")
    sessioni = carica_sessioni()
    if token not in sessioni:
        return "Link non valido.", 404
    s = sessioni[token]
    if request.method == "POST":
        note = request.form.get("note", "").strip()
        salva_sessione(token, {**s, "stato": "modifiche_richieste",
                               "note_modifiche": note,
                               "data_risposta": datetime.now().isoformat()})
        return render_template_string(HTML_GRAZIE)
    return render_template_string(HTML_MODIFICHE, cliente=s.get("cliente", ""))

@app.route("/stato/<token>")
def stato(token):
    sessioni = carica_sessioni()
    if token not in sessioni:
        return jsonify({"errore": "token non trovato"}), 404
    return jsonify(sessioni[token])

@app.route("/ping")
def ping():
    return jsonify({"ok": True})

def avvia_server(porta=5555):
    t = threading.Thread(target=lambda: app.run(port=porta, debug=False, use_reloader=False))
    t.daemon = True
    t.start()
    return t
