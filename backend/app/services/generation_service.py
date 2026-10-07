import os
import json
import logging
import time
from collections import OrderedDict
from threading import RLock

from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError
from pydantic import ValidationError
from backend.app.schemas import ExplanationResponse
from backend.app.services.generation_config import (
    MODEL,
    TEMPERATURE,
    REASONING_EFFORT,
    MAX_COMPLETION_TOKENS,
    CONSIGNES,
    SCHEMA_GENERATION,
)

def construire_contexte(documents: list[dict]) -> str:
    """Assemble les extraits numérotés à partir de 1 avec sections et URLs sources."""
    passages = []
    for numero, document in enumerate(documents, start=1):
        section = " > ".join(document.get("section_path") or [])
        passage = (
            f"[{numero}] {document['title']}\n"
            f"Section : {section or 'Non renseignée'}\n"
            f"{document['text']}\n"
            f"Source : {document['source_url']}"
        )
        passages.append(passage)

    return "\n\n".join(passages)

def verifier_citations(
    explication: ExplanationResponse,
    documents: list[dict],
) -> ExplanationResponse:
    """Écarte les affirmations sans source valide ou sans preuve textuelle retrouvée.

    Seuls les espaces et les apostrophes typographiques sont normalisés. Ce contrôle ne démontre ni la vérité
    du document ni la fidélité sémantique de la reformulation du modèle.
    """
    affirmations_valides = []

    for affirmation in explication.claims:
        numero = affirmation.source_id

        # Les sources sont numérotées à partir de 1.
        if not 1 <= numero <= len(documents):
            continue

        document = documents[numero - 1]

        # Tolérer les variantes typographiques sans modifier les mots.
        citation = " ".join(affirmation.evidence.replace("’", "'").split())
        texte_source = " ".join(document["text"].replace("’", "'").split())

        if not affirmation.claim.strip() or not citation:
            continue

        if citation not in texte_source:
            continue

        affirmations_valides.append(affirmation)

    limitation = explication.limitation

    if len(affirmations_valides) < len(explication.claims):
        limitation = "insufficient_context"

    if not affirmations_valides:
        limitation = "insufficient_context"

    return ExplanationResponse(
        claims=affirmations_valides,
        limitation=limitation,
    )


def _generate_explanation(
    question: str,
    documents: list[dict],
    position_context: dict | None = None,
) -> ExplanationResponse:
    # Sans documents, aucune génération n'est nécessaire.
    """Génère via Groq une réponse structurée, puis contrôle ses citations.

    Sans documents, renvoie une limitation sans appel externe. Lève RuntimeError
    si la clé manque ou si la génération est incomplète ; les erreurs du client
    et de validation Pydantic restent visibles pour la couche HTTP.
    """
    if not documents:
        return ExplanationResponse(
            claims=[],
            limitation="insufficient_context",
        )

    load_dotenv()
    cle_api = os.getenv("GROQ_API_KEY")

    if not cle_api:
        raise RuntimeError("La variable GROQ_API_KEY est absente.")

    contexte = construire_contexte(documents)

    with OpenAI(
        api_key=cle_api,
        base_url="https://api.groq.com/openai/v1",
        timeout=60.0,
        max_retries=0,
    ) as client:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            reasoning_effort=REASONING_EFFORT,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            messages=[
                {"role": "system", "content": CONSIGNES},
                {
                    "role": "user",
                    "content": (
                        f"Question : {question}\n\n"
                        f"Contexte de position (faits vérifiés) :\n{json.dumps(position_context, ensure_ascii=False)}\n\n"
                        f"Extraits documentaires :\n{contexte}"
                    ),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "grounded_chess_summary",
                    "strict": True,
                    "schema": SCHEMA_GENERATION,
                },
            },
        )

    choix = response.choices[0]

    if choix.finish_reason != "stop" or not choix.message.content:
        raise RuntimeError("La réponse de génération est incomplète.")

    explication = ExplanationResponse.model_validate_json(
    choix.message.content
)

    return verifier_citations(explication, documents)


class GenerationUnavailable(Exception):
    """Indisponibilité de l’explication ; les autres résultats restent utilisables."""


# Le contenu documentaire et le profil de génération font partie de la clé.
# Cache borné, local à chaque processus ; aucune erreur n’est mise en cache.
_explanation_cache = OrderedDict()
_generation_lock = RLock()
_retry_after = 0.0
_CACHE_TTL = 900
_CACHE_SIZE = 64
logger = logging.getLogger(__name__)


def generate_explanation(question: str, documents: list[dict], position_context: dict | None = None) -> ExplanationResponse:
    """Réutilise les succès 15 minutes et respecte le délai Groq après un 429.

    Les générations sont sérialisées dans ce processus pour éviter les appels
    identiques simultanés. Le cache est perdu au redémarrage et n’est pas partagé
    entre instances. Les réponses sont copiées pour éviter une mutation du cache.
    """
    global _retry_after
    if not documents:
        return ExplanationResponse(claims=[], limitation="insufficient_context")
    key = json.dumps([question, documents, position_context, MODEL, TEMPERATURE, REASONING_EFFORT,
                      MAX_COMPLETION_TOKENS, CONSIGNES, SCHEMA_GENERATION], sort_keys=True)
    with _generation_lock:
        now = time.monotonic()
        cached = _explanation_cache.get(key)
        if cached and cached[0] > now:
            _explanation_cache.move_to_end(key)
            return cached[1].model_copy(deep=True)
        if now < _retry_after:
            raise GenerationUnavailable("L’explication est temporairement indisponible : limite de débit Groq. Les autres résultats restent disponibles.")
        try:
            result = _generate_explanation(question, documents, position_context)
        except RateLimitError as error:
            try:
                delay = float(error.response.headers.get("retry-after", "30"))
            except (TypeError, ValueError):
                delay = 30
            _retry_after = time.monotonic() + max(1, delay)
            logger.warning("generation_unavailable provider=groq status=429")
            raise GenerationUnavailable("L’explication est temporairement indisponible : limite de débit Groq. Les autres résultats restent disponibles.") from None
        except (APIError, ValidationError, RuntimeError) as error:
            logger.warning("generation_unavailable provider=groq type=%s status=%s",
                           type(error).__name__, getattr(error, "status_code", None))
            raise GenerationUnavailable("L’explication est momentanément indisponible. Les autres résultats restent disponibles.") from None
        _explanation_cache[key] = (time.monotonic() + _CACHE_TTL, result.model_copy(deep=True))
        _explanation_cache.move_to_end(key)
        while len(_explanation_cache) > _CACHE_SIZE:
            _explanation_cache.popitem(last=False)
        return result
