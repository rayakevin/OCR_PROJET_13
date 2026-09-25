"""Collecter les cinq articles Wikichess de référence dans data/wikichess.json.

uv run python -m backend.app.commands.collect_wikichess
Ce corpus anglais reste séparé du corpus Wikipédia français indexé dans Milvus.
"""

import argparse
import time
from pathlib import Path

from backend.app.commands._common import DATA_DIR, ecrire_json
from backend.app.services.wikichess_service import extract_wikichess


ARTICLES = [
    {"url": "https://ficgs.com/wikichess_45.html", "title": "Italian Game"},
    {"url": "https://ficgs.com/wikichess_12.html", "title": "Ruy Lopez"},
    {"url": "https://ficgs.com/wikichess_3.html", "title": "Sicilian Defense"},
    {"url": "https://ficgs.com/wikichess_21.html", "title": "French Defense"},
    {"url": "https://ficgs.com/wikichess_22.html", "title": "Caro-Kann Defense"},
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DATA_DIR / "wikichess.json")
    args = parser.parse_args()
    documents = []
    for numero, article in enumerate(ARTICLES):
        if numero:
            time.sleep(1)
        document = extract_wikichess(article["url"], article["title"])
        documents.append(document)
        print(document["title"], len(document["text"]))
    # Ne remplacer l'ancien corpus que lorsque toute la collecte a réussi.
    ecrire_json(args.output, documents)
    print(f"{len(documents)} documents enregistrés dans {args.output}")


if __name__ == "__main__":
    main()
