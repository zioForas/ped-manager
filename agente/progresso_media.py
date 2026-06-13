"""
Mostra lo stato di avanzamento della classificazione media (con progress bar).
Esegui: python3.11 agente/progresso_media.py [cliente]
"""
import json
import os
import sys

BASE = os.path.join(os.path.dirname(__file__), '..')


def progress_bar(done: int, totale: int, larghezza: int = 30) -> str:
    if totale == 0:
        return "[" + " " * larghezza + "] 0%"
    frac = done / totale
    pieni = int(frac * larghezza)
    barra = "█" * pieni + "░" * (larghezza - pieni)
    return f"[{barra}] {frac*100:.0f}%  ({done}/{totale})"


def main():
    cliente = sys.argv[1] if len(sys.argv) > 1 else "example"
    output_root = os.path.join(BASE, "output", "media", cliente)
    classif_path = os.path.join(output_root, "_classificazioni.json")

    raw_dir = os.path.join(output_root, "_raw")
    foto_dir = os.path.join(output_root, "foto")
    candidati = []
    for d in (raw_dir, foto_dir):
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                candidati.extend(f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
    totale = len(set(candidati))

    classificazioni = {}
    if os.path.exists(classif_path):
        with open(classif_path) as f:
            classificazioni = json.load(f)
    done = len(classificazioni)

    print(f"\nClassificazione media — {cliente}")
    print(progress_bar(done, totale))

    conteggi = {}
    for arg in classificazioni.values():
        conteggi[arg] = conteggi.get(arg, 0) + 1
    if conteggi:
        print("\nPer argomento:")
        for arg, n in sorted(conteggi.items(), key=lambda x: -x[1]):
            print(f"  {arg}: {n}")

    if done < totale:
        rimanenti = totale - done
        print(f"\n~{rimanenti} immagini rimanenti (~1/min con rate limit gratuito → ~{rimanenti} min residui)")
    else:
        print("\n✓ Classificazione completata!")
    print()


if __name__ == "__main__":
    main()
