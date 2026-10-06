import os
from datetime import datetime, timezone

from pymongo import MongoClient

from bson import ObjectId
from bson.errors import InvalidId


def save_analysis(fen: str, result: dict) -> str:
    """Insère une analyse dans chess_coach.analyses et renvoie son ObjectId en texte.

    Le résultat doit déjà être validé par l'appelant. La date est produite en UTC
    et chaque appel crée un nouveau document. Les erreurs PyMongo remontent
    à la couche HTTP ; le client est fermé à la sortie du bloc with.
    """
    uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")

    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        collection = client["chess_coach"]["analyses"]

        document = {
            "fen": fen,
            "created_at": datetime.now(timezone.utc),
            "result": result,
        }

        insertion = collection.insert_one(document)

        return str(insertion.inserted_id)

def get_analysis(analysis_id: str) -> dict | None:
    """Retrouve un document par identifiant, ou renvoie None s'il est absent.

    Lève ValueError pour un identifiant texte mal formé. Convertit _id en str,
    mais conserve created_at comme datetime (UTC sans tzinfo avec ce client).
    FastAPI assure ensuite la sérialisation de la date.
    """
    try:
        mongo_id = ObjectId(analysis_id)
    except InvalidId as erreur:
        raise ValueError("Identifiant d’analyse invalide.") from erreur

    uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")

    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        collection = client["chess_coach"]["analyses"]

        document = collection.find_one({"_id": mongo_id})

        if document is None:
            return None

        document["_id"] = str(document["_id"])
        return document


def list_analyses(limit: int = 10) -> list[dict]:
    """Liste les résumés et les métadonnées utiles, sans les contenus détaillés.

    L'appelant doit fournir une limite positive ; la route la borne à 1..50.
    _id départage les dates égales. Les dates restent des datetime UTC avec
    fuseau et les identifiants sont convertis en texte.
    """
    uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")

    with MongoClient(
        uri,
        serverSelectionTimeoutMS=5000,
        tz_aware=True,
    ) as client:
        collection = client["chess_coach"]["analyses"]

        cursor = (
            collection.find(
                {},
                {"fen": 1, "created_at": 1, "result.opening": 1,
                 "result.source": 1, "result.game_over": 1},
            )
            .sort([("created_at", -1), ("_id", -1)])
            .limit(limit)
        )

        analyses = []

        for document in cursor:
            analyses.append(analysis_summary(document))

        return analyses


def analysis_summary(document: dict) -> dict:
    """Expose un résumé lisible, compatible avec les anciennes analyses."""
    result = document.get("result") or {}
    opening = result.get("opening") or {}
    return {
        "_id": str(document["_id"]),
        "fen": document["fen"],
        "created_at": document["created_at"],
        "opening_name": opening.get("name"),
        "source": result.get("source"),
        "game_over": result.get("game_over"),
    }
