"""Vérifie si l'ouverture attendue figure parmi les trois premiers passages.

Lancement : uv run python -m backend.app.commands.evaluate_retrieval
Milvus doit être démarré. Le modèle est réutilisé entre les questions.
Ce test mesure l'identification de l'ouverture, pas la qualité de l'explication.
"""

import argparse

from backend.app.services.vector_search_service import search_documents


LIMIT = 3

cas_de_test = [
    {
        "question": "Quels sont les principes de la défense française ?",
        "expected_title": "Défense française",
    },
    {
        "question": "Quels sont les principes d'une ouverture à la française ?",
        "expected_title": "Défense française",
    },
    {
        "question": "Quels sont les plans des Noirs après 1. e4 e6 2. d4 d5 ?",
        "expected_title": "Défense française",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    reussites = 0
    erreurs = 0

    for numero, cas in enumerate(cas_de_test, start=1):
        print(f"\n{numero}. {cas['question']}", flush=True)
        print(f"Ouverture attendue : {cas['expected_title']}")

        try:
            passages = search_documents(cas["question"], limit=LIMIT)
        except Exception as erreur:
            # Dans cet outil d'évaluation, distinguer une panne d'un mauvais résultat.
            erreurs += 1
            print(f"ERREUR TECHNIQUE — {type(erreur).__name__} : {erreur}")
            continue

        titres = [passage["title"] for passage in passages]
        trouve = cas["expected_title"] in titres
        if trouve:
            reussites += 1

        for rang, passage in enumerate(passages, start=1):
            section = " > ".join(passage["section_path"])
            print(f"  {rang}. {passage['title']} — {section} — score {passage['score']:.3f}")
        if not passages:
            print("  Aucun passage retourné.")

        if trouve:
            rang_attendu = titres.index(cas["expected_title"]) + 1
            print(f"TROUVÉ — première apparition au rang {rang_attendu}")
        else:
            print(f"NON TROUVÉ — ouverture absente des {LIMIT} premiers résultats")

    total = len(cas_de_test)
    recherches_abouties = total - erreurs
    print("\n--- Bilan ---")
    print(f"Cas prévus : {total} ; recherches abouties : {recherches_abouties}")
    print(f"Erreurs techniques : {erreurs}")
    if recherches_abouties:
        taux = reussites / recherches_abouties
        print(f"Ouverture trouvée dans le top {LIMIT} : {reussites}/{recherches_abouties} ({taux:.1%})")
    else:
        print("Aucune recherche aboutie : qualité non mesurable.")
    print("Ce bilan porte uniquement sur ces cas, pas sur toutes les ouvertures.")
    if erreurs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
