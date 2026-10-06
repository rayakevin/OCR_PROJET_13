"""Historique de démonstration persistant dans un Dataset privé Hugging Face.

Un fichier JSON immuable par analyse évite d'écraser un index partagé lors de
deux sauvegardes concurrentes. Le Hub est contacté en HTTPS. Ce stockage est
destiné au faible trafic du Space, pas à remplacer MongoDB à grande échelle.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from bson import ObjectId
from huggingface_hub import HfApi
from huggingface_hub.errors import RemoteEntryNotFoundError


class HistoryError(Exception):
    """Erreur maîtrisée de stockage, sans détail d'authentification."""


def connection() -> tuple[HfApi, str]:
    """Utilise un jeton distinct, limité au Dataset d'historique."""
    repo_id = os.getenv("HF_HISTORY_REPO", "").strip()
    token = os.getenv("HF_HISTORY_TOKEN", "").strip()
    if not repo_id or not token:
        raise HistoryError("Le stockage de l’historique n’est pas configuré.")
    return HfApi(token=token), repo_id


def save_analysis(fen: str, result: dict) -> str:
    """Ne confirme l'enregistrement qu'après le commit distant réussi."""
    api, repo_id = connection()
    analysis_id = str(ObjectId())
    document = {
        "_id": analysis_id, "fen": fen,
        "created_at": datetime.now(timezone.utc).isoformat(), "result": result,
    }
    try:
        if not api.repo_info(repo_id=repo_id, repo_type="dataset").private:
            raise HistoryError("Le dépôt d’historique doit être privé.")
        api.upload_file(
            path_or_fileobj=json.dumps(document, ensure_ascii=False).encode("utf-8"),
            path_in_repo=f"analyses/{analysis_id}.json", repo_id=repo_id,
            repo_type="dataset", commit_message="Enregistrer une analyse Chess Coach",
        )
    except HistoryError:
        raise
    except Exception:
        raise HistoryError("Impossible d’enregistrer l’analyse dans l’historique.") from None
    return analysis_id


def get_analysis(analysis_id: str) -> dict | None:
    """Relit un fichier validé par son identifiant ; distingue absent et panne."""
    if not ObjectId.is_valid(analysis_id):
        raise ValueError("Identifiant d’analyse invalide.")
    analysis_id = str(ObjectId(analysis_id))
    api, repo_id = connection()
    try:
        path = api.hf_hub_download(
            repo_id=repo_id, repo_type="dataset", filename=f"analyses/{analysis_id}.json",
        )
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        if document["_id"] != analysis_id or not all(
            key in document for key in ("fen", "created_at", "result")
        ):
            raise ValueError("Document invalide")
        return document
    except RemoteEntryNotFoundError:
        return None
    except Exception:
        raise HistoryError("Impossible de relire cette analyse.") from None


def list_analyses(limit: int = 10) -> list[dict]:
    """Liste les derniers identifiants ; aucun état local requis après redémarrage.

    Les ObjectId suivent l'ordre de création du processus unique du Space.
    Des producteurs multiples peuvent différer dans l'ordre à la seconde près.
    """
    if not 1 <= limit <= 50:
        raise ValueError("La limite doit être comprise entre 1 et 50.")
    api, repo_id = connection()
    try:
        paths = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
        ids = sorted((Path(path).stem for path in paths
                      if path.startswith("analyses/") and path.endswith(".json")
                      and ObjectId.is_valid(Path(path).stem)), reverse=True)
        documents = [get_analysis(value) for value in ids[:limit]]
        return [{key: doc[key] for key in ("_id", "fen", "created_at")}
                for doc in documents if doc is not None]
    except HistoryError:
        raise
    except Exception:
        raise HistoryError("L’historique est temporairement indisponible.") from None
