"""Encode les questions avec Qwen hébergé par DeepInfra via Hugging Face."""

import os

import httpx
import numpy as np
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
EMBEDDING_DIMENSION = 1024
QUERY_PROMPT = (
    "Instruct: Given a question about chess openings, retrieve passages "
    "explaining the strategic ideas and plans of the specific opening "
    "or move sequence mentioned.\nQuery:"
)


class EmbeddingError(Exception):
    """Erreur publique maîtrisée, indépendante des détails et secrets du fournisseur."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def embed_question(question: str) -> list[float]:
    """Renvoie un vecteur normalisé compatible avec le corpus Qwen à 1024 dimensions.

    Ajoute exactement l'instruction utilisée lors de l'évaluation local/distant.
    Aucun poids n'est téléchargé ou chargé par cette fonction. Les pannes sont
    converties en EmbeddingError pour éviter de les attribuer à Lichess ou à la FEN.
    """
    question = question.strip()
    if not question:
        raise ValueError("La question ne doit pas être vide.")
    load_dotenv()
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise EmbeddingError("Le service d’embeddings n’est pas configuré (HF_TOKEN).", 500)

    try:
        client = InferenceClient(provider="deepinfra", api_key=token, timeout=60)
        resultat = client.feature_extraction([QUERY_PROMPT + question], model=MODEL_ID)
    except (InferenceTimeoutError, httpx.TimeoutException):
        raise EmbeddingError("Le service d’embeddings ne répond pas à temps.", 504) from None
    except (HfHubHTTPError, httpx.HTTPStatusError) as erreur:
        statut = erreur.response.status_code
        if statut in (401, 403):
            raise EmbeddingError("L’accès au service d’embeddings est mal configuré.", 500) from None
        if statut in (402, 429):
            raise EmbeddingError("Le quota ou les crédits du service d’embeddings sont indisponibles.", 503) from None
        raise EmbeddingError("Le fournisseur d’embeddings a renvoyé une erreur.") from None
    except httpx.RequestError:
        raise EmbeddingError("Impossible de contacter le service d’embeddings.") from None
    except (ValueError, TypeError, KeyError):
        raise EmbeddingError("Le fournisseur d’embeddings a renvoyé une réponse inexploitable.") from None

    try:
        vecteurs = np.asarray(resultat, dtype=np.float32)
        if vecteurs.shape != (1, EMBEDDING_DIMENSION) or not np.isfinite(vecteurs).all():
            raise ValueError("Vecteur incompatible")
        norme = float(np.linalg.norm(vecteurs[0]))
        if not np.isfinite(norme) or norme <= 0:
            raise ValueError("Norme invalide")
    except (ValueError, TypeError, OverflowError):
        raise EmbeddingError("Le fournisseur d’embeddings a renvoyé un vecteur incompatible.") from None

    return (vecteurs[0] / norme).tolist()
