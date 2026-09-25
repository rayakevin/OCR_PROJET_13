"""Correspondances entre les noms Lichess et les titres du corpus français.

Source des noms anglais : https://github.com/lichess-org/chess-openings
Catalogue vérifié le 25 septembre 2026 (a.tsv à e.tsv).
Les valeurs correspondent aux titres de data/wikipedia_fr/wikipedia_chunks.json.
Ce mapping sélectionne une famille documentaire, sans analyser la position.
"""


OPENING_TITLES = {
    # Les 30 ouvertures présentes dans le corpus.
    "Alekhine Defense": "Défense Alekhine",
    "Benoni Defense": "Défense Benoni",
    "Caro-Kann Defense": "Défense Caro-Kann",
    "Catalan Opening": "Partie catalane",
    "Dutch Defense": "Défense hollandaise",
    "English Opening": "Ouverture anglaise",
    "Four Knights Game": "Partie des quatre cavaliers",
    "French Defense": "Défense française",
    "Grünfeld Defense": "Défense Grünfeld",
    "Italian Game": "Partie italienne",
    "King's Gambit": "Gambit du roi",
    "King's Indian Defense": "Défense est-indienne",
    "London System": "Système de Londres",
    "Modern Defense": "Défense moderne",
    "Nimzo-Indian Defense": "Défense nimzo-indienne",
    "Petrov's Defense": "Défense russe",
    "Philidor Defense": "Défense Philidor",
    "Pirc Defense": "Défense Pirc",
    "Queen's Gambit": "Gambit dame",
    "Queen's Gambit Accepted": "Gambit dame accepté",
    "Queen's Gambit Declined": "Gambit dame refusé",
    "Queen's Indian Defense": "Défense ouest-indienne",
    "Réti Opening": "Début Réti",
    "Ruy Lopez": "Partie espagnole",
    "Scandinavian Defense": "Défense scandinave",
    "Scotch Game": "Partie écossaise",
    "Semi-Slav Defense": "Défense semi-slave",
    "Sicilian Defense": "Défense sicilienne",
    "Slav Defense": "Défense slave",
    "Vienna Game": "Partie viennoise",

    # Noms supplémentaires du catalogue rattachés à un article existant.
    "King's Gambit Accepted": "Gambit du roi",
    "King's Gambit Declined": "Gambit du roi",
    "Semi-Slav Defense Accepted": "Défense semi-slave",
    "Vienna Gambit, with Max Lange Defense": "Partie viennoise",

    # Ces noms précis doivent être reconnus avant de retirer la variante.
    "Indian Defense: London System": "Système de Londres",
    "Indian Defense: Accelerated London System": "Système de Londres",
    "Queen's Pawn Game: London System": "Système de Londres",
    "Queen's Pawn Game: Accelerated London System": "Système de Londres",
    "Rubinstein Opening: Semi-Slav Defense": "Défense semi-slave",
}


def get_opening_title(opening: dict[str, str] | None) -> str | None:
    """Cherche le nom complet, puis ses parents ; None si aucun n'est couvert.

    Exemple : « Queen's Pawn Game: London System, with e6 » est ramené
    à « Queen's Pawn Game: London System », puis associé au titre français.
    On ne cherche pas des mots isolés : « French Attack » dans une autre
    ouverture ne doit pas conduire automatiquement à la défense française.
    """
    if not opening:
        return None

    nom = opening.get("name")
    if not isinstance(nom, str):
        return None
    nom = nom.strip()

    while nom:
        titre = OPENING_TITLES.get(nom)
        if titre is not None:
            return titre

        # Retirer la dernière sous-variante, puis la variante si nécessaire.
        separateur = max(nom.rfind(","), nom.rfind(":"))
        if separateur == -1:
            return None
        nom = nom[:separateur].strip()

    return None
