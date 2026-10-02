import os

from dotenv import load_dotenv
from openai import OpenAI
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

    Seuls les espaces sont normalisés. Ce contrôle ne démontre ni la vérité
    du document ni la fidélité sémantique de la reformulation du modèle.
    """
    affirmations_valides = []

    for affirmation in explication.claims:
        numero = affirmation.source_id

        # Les sources sont numérotées à partir de 1.
        if not 1 <= numero <= len(documents):
            continue

        document = documents[numero - 1]

        # Uniformiser les espaces et les retours à la ligne.
        citation = " ".join(affirmation.evidence.split())
        texte_source = " ".join(document["text"].split())

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


def generate_explanation(
    question: str,
    documents: list[dict],
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
