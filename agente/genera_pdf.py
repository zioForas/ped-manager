import json
import os
from datetime import datetime
from dotenv import load_dotenv
from fpdf import FPDF

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def san(testo: str) -> str:
    if not isinstance(testo, str):
        return str(testo)
    return testo.encode("latin-1", errors="ignore").decode("latin-1")

COLORI = {
    "blu": (41, 98, 255),
    "blu_chiaro": (235, 240, 255),
    "grigio": (100, 100, 100),
    "grigio_chiaro": (245, 245, 245),
    "bianco": (255, 255, 255),
    "nero": (30, 30, 30),
}

ARGOMENTO_COLORI = {
    "Presentazione Studio": (41, 98, 255),
    "Igiene E Prevenzione": (34, 197, 94),
    "Team E Staff": (249, 115, 22),
    "Implantologia": (168, 85, 247),
}

class PedPDF(FPDF):
    def __init__(self, cliente, periodo):
        super().__init__()
        self.cliente = san(cliente)
        self.periodo = san(periodo)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*COLORI["blu"])
        self.rect(0, 0, 210, 12, 'F')
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*COLORI["bianco"])
        self.set_xy(10, 3)
        self.cell(0, 6, f"Piano Editoriale - {self.cliente} - {self.periodo}", align="L")
        self.set_xy(0, 3)
        self.cell(200, 6, f"Pag. {self.page_no()}", align="R")
        self.ln(14)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*COLORI["grigio"])
        self.cell(0, 5, "Documento riservato - uso interno e cliente", align="C")

    def copertina(self, mesi, anno):
        self.set_fill_color(*COLORI["blu"])
        self.rect(0, 0, 210, 297, 'F')
        self.set_font("Helvetica", "B", 32)
        self.set_text_color(*COLORI["bianco"])
        self.set_xy(0, 80)
        self.cell(210, 20, "PIANO EDITORIALE", align="C")
        self.set_font("Helvetica", "", 18)
        self.set_xy(0, 105)
        self.cell(210, 12, f"{san(mesi[0]).upper()} - {san(mesi[-1]).upper()} {anno}", align="C")
        self.set_fill_color(*COLORI["bianco"])
        self.rect(30, 140, 150, 2, 'F')
        self.set_font("Helvetica", "B", 16)
        self.set_xy(0, 155)
        self.cell(210, 10, self.cliente, align="C")
        self.set_font("Helvetica", "", 11)
        self.set_xy(0, 170)
        self.cell(210, 8, "Instagram + Facebook", align="C")
        self.set_font("Helvetica", "", 9)
        self.set_xy(0, 260)
        self.cell(210, 6, f"Generato il {datetime.now().strftime('%d/%m/%Y')}", align="C")

    def sezione_titolo(self, titolo, sottotitolo=""):
        self.set_fill_color(*COLORI["blu_chiaro"])
        self.set_draw_color(*COLORI["blu"])
        self.rect(10, self.get_y(), 190, 14, 'FD')
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*COLORI["blu"])
        self.set_x(14)
        self.cell(0, 14, san(titolo), ln=True)
        if sottotitolo:
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*COLORI["grigio"])
            self.set_x(14)
            self.cell(0, 6, san(sottotitolo), ln=True)
        self.ln(4)

    def card_post(self, post, index):
        y_start = self.get_y()
        arg = post.get("argomento", "")
        colore = ARGOMENTO_COLORI.get(arg, COLORI["blu"])

        self.set_fill_color(*COLORI["grigio_chiaro"])
        self.rect(10, y_start, 190, 52, 'F')
        self.set_fill_color(*colore)
        self.rect(10, y_start, 4, 52, 'F')

        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*colore)
        self.set_xy(17, y_start + 3)
        self.cell(40, 5, f"POST #{post['numero']}", ln=False)

        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLORI["grigio"])
        self.set_xy(60, y_start + 3)
        self.cell(80, 5, san(arg), ln=False)

        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*COLORI["nero"])
        self.set_xy(150, y_start + 3)
        try:
            dt = datetime.strptime(post["data"], "%Y-%m-%d")
            data_str = dt.strftime("%a %d %b %Y").capitalize()
        except Exception:
            data_str = post.get("data", "")
        self.cell(48, 5, san(f"{data_str}  {post.get('orario','')}"), align="R")

        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*COLORI["nero"])
        self.set_xy(17, y_start + 11)
        caption = san(post.get("caption", ""))
        if len(caption) > 220:
            caption = caption[:217] + "..."
        self.multi_cell(181, 4.5, caption)

        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*COLORI["blu"])
        self.set_xy(17, y_start + 40)
        hashtag = san(post.get("hashtag", ""))
        if len(hashtag) > 130:
            hashtag = hashtag[:127] + "..."
        self.cell(181, 4, hashtag)

        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*COLORI["grigio"])
        self.set_xy(17, y_start + 46)
        self.cell(181, 4, san(f"Grafica: {post.get('nota_grafica','')[:90]}"))

        self.set_y(y_start + 55)

    def card_story(self, story, index):
        y_start = self.get_y()
        tipo = story.get("tipo", "originale")
        colore = (34, 197, 94) if tipo == "originale" else (249, 115, 22)

        self.set_fill_color(*COLORI["grigio_chiaro"])
        self.rect(10, y_start, 190, 36, 'F')
        self.set_fill_color(*colore)
        self.rect(10, y_start, 4, 36, 'F')

        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*colore)
        self.set_xy(17, y_start + 3)
        label = "STORY ORIGINALE" if tipo == "originale" else "STORY REPOST"
        self.cell(60, 5, f"#{story['numero']} - {label}")

        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLORI["grigio"])
        self.set_xy(150, y_start + 3)
        try:
            dt = datetime.strptime(story["data"], "%Y-%m-%d")
            data_str = dt.strftime("%d %b")
        except Exception:
            data_str = story.get("data", "")
        self.cell(48, 5, san(f"{data_str}  {story.get('orario','')}"), align="R")

        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*COLORI["nero"])
        self.set_xy(17, y_start + 11)

        if tipo == "originale":
            testo = san(story.get("testo", ""))
            if len(testo) > 150:
                testo = testo[:147] + "..."
            self.multi_cell(181, 4.5, testo)
            self.set_font("Helvetica", "I", 7.5)
            self.set_text_color(*COLORI["grigio"])
            self.set_xy(17, y_start + 27)
            musica = san(story.get("musica_suggerita", ""))
            sticker = san(", ".join(story.get("sticker_suggeriti", [])))
            self.cell(181, 4, f"Musica: {musica}  |  Sticker: {sticker}")
        else:
            self.cell(181, 5, san(story.get("riferimento_post", "")))
            self.set_font("Helvetica", "I", 7.5)
            self.set_text_color(*COLORI["grigio"])
            self.set_xy(17, y_start + 18)
            self.cell(181, 4, san(story.get("nota", "")))

        self.set_y(y_start + 39)


def genera_pdf(cliente: str = "example"):
    strategia_path = os.path.join(os.path.dirname(__file__), '..', 'clienti', cliente, 'strategia.json')
    with open(strategia_path) as f:
        strategia = json.load(f)

    mesi = strategia["mesi"]
    anno = strategia["anno"]

    with open(os.path.join(os.path.dirname(__file__), '..', 'output',
              f'ped_{cliente}_{mesi[0].lower()}_{mesi[-1].lower()}_{anno}.json')) as f:
        ped = json.load(f)
    with open(os.path.join(os.path.dirname(__file__), '..', 'output',
              f'stories_{cliente}_{mesi[0].lower()}_{mesi[-1].lower()}_{anno}.json')) as f:
        stories = json.load(f)

    periodo = f"{mesi[0]} - {mesi[-1]} {anno}"
    pdf = PedPDF(strategia["cliente"], periodo)
    pdf.set_margins(10, 10, 10)

    # Copertina
    pdf.add_page()
    pdf.copertina(mesi, anno)

    # Sezione POST
    pdf.add_page()
    pdf.sezione_titolo("POST - IG & FB", f"{len(ped)} post | Lunedi e Giovedi | {periodo}")
    pdf.ln(2)
    for i, post in enumerate(ped):
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.card_post(post, i)
        pdf.ln(2)

    # Sezione STORIES
    pdf.add_page()
    originali = [s for s in stories if s["tipo"] == "originale"]
    repost = [s for s in stories if s["tipo"] == "repost"]
    pdf.sezione_titolo("STORIES - IG & FB",
                       f"{len(stories)} stories | {len(originali)} originali + {len(repost)} repost | {periodo}")
    pdf.ln(2)
    for i, story in enumerate(stories):
        if pdf.get_y() > 248:
            pdf.add_page()
        pdf.card_story(story, i)
        pdf.ln(2)

    output_path = os.path.join(os.path.dirname(__file__), '..', 'output',
                               f'PED_{cliente}_{mesi[0]}_{mesi[-1]}_{anno}.pdf')
    pdf.output(output_path)
    print(f"OK PDF: {output_path}")
    return output_path

if __name__ == "__main__":
    genera_pdf("example")
