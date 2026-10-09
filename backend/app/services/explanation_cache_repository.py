"""Cache permanent des explications Groq dans chess_coach.explanation_cache.

Le corpus est figé : une même clé produit la même explication, conservée sans
expiration. Le cache est facultatif : toute panne MongoDB est journalisée puis
ignorée, et l'appelant régénère normalement. Actif uniquement avec MongoDB.
"""

import logging
import os
import time
from datetime import datetime, timezone
from threading import Lock

from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)

# Client réutilisé entre les appels : une connexion Atlas par appel serait coûteuse.
_client = None
_client_lock = Lock()
# Après une panne, MongoDB n'est plus sollicité pendant ce délai pour ne pas
# ajouter l'attente de connexion à chaque génération.
_PAUSE_AFTER_FAILURE = 60
_unavailable_until = 0.0


def _collection():
    """Renvoie la collection du cache, ou None si le cache MongoDB est inactif."""
    global _client
    if os.getenv("HISTORY_BACKEND", "mongodb") != "mongodb":
        return None
    if time.monotonic() < _unavailable_until:
        return None
    with _client_lock:
        if _client is None:
            _client = MongoClient(
                os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017"),
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=5000,
            )
    return _client["chess_coach"]["explanation_cache"]


def _mark_unavailable(operation: str, error: Exception) -> None:
    global _unavailable_until
    _unavailable_until = time.monotonic() + _PAUSE_AFTER_FAILURE
    logger.warning("explanation_cache_unavailable operation=%s type=%s", operation, type(error).__name__)


def load_explanation(key: str) -> dict | None:
    """Renvoie l'explication enregistrée pour cette empreinte, ou None."""
    try:
        collection = _collection()
        if collection is None:
            return None
        document = collection.find_one({"_id": key}, {"explanation": 1})
    except PyMongoError as error:
        _mark_unavailable("read", error)
        return None
    return document.get("explanation") if document else None


def store_explanation(key: str, explanation: dict, model: str) -> None:
    """Enregistre ou remplace l'explication ; une erreur n'interrompt pas l'analyse."""
    try:
        collection = _collection()
        if collection is None:
            return
        collection.replace_one(
            {"_id": key},
            {"explanation": explanation, "model": model, "created_at": datetime.now(timezone.utc)},
            upsert=True,
        )
    except PyMongoError as error:
        _mark_unavailable("write", error)
