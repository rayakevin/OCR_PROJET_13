import os
from datetime import datetime, timezone

from pymongo import MongoClient

from bson import ObjectId
from bson.errors import InvalidId


def save_analysis(fen: str, result: dict) -> str:
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
                {"fen": 1, "created_at": 1},
            )
            .sort([("created_at", -1), ("_id", -1)])
            .limit(limit)
        )

        analyses = []

        for document in cursor:
            document["_id"] = str(document["_id"])
            analyses.append(document)

        return analyses