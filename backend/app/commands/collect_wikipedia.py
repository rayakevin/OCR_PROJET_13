"""Corpus Wikipédia : collecte progressive, cache local et reprise sur erreur.

    uv run python -m backend.app.commands.collect_wikipedia
    uv run python -m backend.app.commands.collect_wikipedia --refresh
"""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import quote

import httpx

from backend.app.services.wikipedia_service import extract_wikipedia
from backend.app.services.chunking_service import chunk_documents
from backend.app.commands._common import WIKIPEDIA_DIR, ecrire_json


USER_AGENT = "ChessLearningBot/0.1 (kevinraya.kr@gmail.com)"
# Grandes familles ; les variantes pourront être ajoutées progressivement.
PAGES = [
    "Partie_italienne", "Partie_espagnole", "Défense_sicilienne",
    "Défense_française", "Défense_Caro-Kann", "Partie_écossaise",
    "Partie_viennoise", "Défense_Petrov", "Gambit_du_roi",
    "Partie_des_quatre_cavaliers", "Défense_Philidor", "Défense_scandinave",
    "Défense_Pirc", "Défense_Alekhine", "Défense_moderne", "Gambit_dame",
    "Gambit_dame_accepté", "Gambit_dame_refusé", "Défense_slave",
    "Défense_semi-slave", "Défense_est-indienne", "Défense_nimzo-indienne",
    "Défense_ouest-indienne", "Défense_Grünfeld", "Défense_hollandaise",
    "Défense_Benoni", "Ouverture_anglaise", "Début_Réti",
    "Système_de_Londres", "Partie_catalane",
]
ARTICLES = [f"https://fr.wikipedia.org/wiki/{quote(page)}" for page in PAGES]


def document_valide(document):
    if not isinstance(document, dict):
        return False

    champs = ("id", "title", "source_url", "language", "text")

    champs_valides = all(
        isinstance(document.get(champ), str)
        and bool(document[champ].strip())
        for champ in champs
    )

    blocs_valides = (
        isinstance(document.get("blocks"), list)
        and bool(document["blocks"])
    )

    return (
        champs_valides and blocs_valides
        and document["language"] == "fr"
        and document["source_url"].startswith("https://fr.wikipedia.org/wiki/")
        and all(
            isinstance(bloc, dict)
            and isinstance(bloc.get("text"), str) and bool(bloc["text"].strip())
            and isinstance(bloc.get("section_path"), list) and bool(bloc["section_path"])
            and all(isinstance(titre, str) for titre in bloc["section_path"])
            and bloc.get("type") in {"paragraph", "list_item", "definition_term", "definition"}
            for bloc in document["blocks"]
        )
    )


def collecter(dossier: Path, refresh=False, articles=None, delai=1.0):
    articles = ARTICLES if articles is None else articles
    documents = {}  # Identifiant canonique : évite les doublons après redirection.
    erreurs = []
    requete_precedente = False
    telecharges = 0
    caches = 0
    rapport = dossier / "wikipedia_errors.json"
    ecrire_json(rapport, erreurs)

    for url in articles:
        # Nom local basé sur l'URL demandée, même si Wikipédia la redirige.
        cache = dossier / "wikipedia_articles" / (url.rsplit("/", 1)[-1] + ".json")
        document = None
        if cache.exists():
            try:
                candidat = json.loads(cache.read_text(encoding="utf-8"))
                if document_valide(candidat):
                    document = candidat
            except (ValueError, UnicodeError):
                pass

        if document is not None and not refresh:
            caches += 1
            print(f"Cache : {document['title']}")
        else:
            # Garder l'ancienne copie si sa mise à jour échoue.
            ancien = document
            try:
                if requete_precedente:
                    time.sleep(delai)
                requete_precedente = True
                document = extract_wikipedia(url, USER_AGENT, language="fr")
                if not document_valide(document):
                    raise ValueError("Document extrait incomplet ou vide")
                ecrire_json(cache, document)
                telecharges += 1
                print(f"Téléchargé : {document['title']} ({len(document['text'])} caractères)")
            except (httpx.HTTPError, ValueError) as erreur:
                document = ancien
                erreurs.append({
                    "url": url,
                    "error_type": type(erreur).__name__,
                    "message": str(erreur),
                    "cached_version_kept": ancien is not None,
                })
                ecrire_json(rapport, erreurs)
                print(f"Échec : {url} — {erreur}")

        if document is not None:
            documents[document["id"]] = document
            # Actualiser aussi le corpus après chaque succès pour supporter une interruption.
            ecrire_json(dossier / "wikipedia.json", list(documents.values()))

    # Une collecte vide est représentée explicitement, sans ancien corpus trompeur.
    ecrire_json(dossier / "wikipedia.json", list(documents.values()))
    print(f"Bilan : {len(documents)} documents, {telecharges} téléchargements, "
          f"{caches} réutilisés, {len(erreurs)} erreurs.")
    return list(documents.values()), erreurs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Actualiser les copies locales")
    parser.add_argument("--data-dir", type=Path, default=WIKIPEDIA_DIR)
    args = parser.parse_args()
    dossier = args.data_dir
    documents, erreurs = collecter(dossier, refresh=args.refresh)
    if erreurs:
        raise SystemExit("Collecte incomplète : consulter wikipedia_errors.json avant le découpage.")
    chunks = chunk_documents(documents)
    ecrire_json(dossier / "wikipedia_chunks.json", chunks)
    print(f"{len(chunks)} chunks structurés enregistrés.")

if __name__ == "__main__":
    main()
