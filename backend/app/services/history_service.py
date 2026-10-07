"""Sélection du stockage : MongoDB local ou Dataset HF privé pour le Space."""

import os

from backend.app.services import analysis_repository, hf_history_repository


def repository():
    """Refuse une configuration inconnue plutôt que sauvegarder au mauvais endroit."""
    backend = os.getenv("HISTORY_BACKEND", "mongodb")
    if backend == "mongodb":
        return analysis_repository
    if backend == "hf_dataset":
        return hf_history_repository
    raise hf_history_repository.HistoryError("Le stockage de l’historique est mal configuré.")


def save_analysis(fen: str, result: dict) -> str:
    return repository().save_analysis(fen, result)


def get_analysis(analysis_id: str) -> dict | None:
    return repository().get_analysis(analysis_id)


def list_analyses(limit: int | None = None) -> list[dict]:
    return repository().list_analyses(limit)
