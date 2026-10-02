import os

from pymilvus import MilvusClient
# Réexportés pour les commandes locales d'évaluation existantes.
from backend.app.services.embedding_service import MODEL_ID, QUERY_PROMPT, embed_question
COLLECTION_NAME = "chess_openings_fr_v2"

MILVUS_URI = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")

def search_documents(question: str, limit: int = 3, opening_title: str | None = None,) -> list[dict]:
    """Encode la question puis recherche les passages proches par similarité cosinus.

    opening_title limite la recherche au titre exact via un filtre paramétré.
    Renvoie les textes et métadonnées, avec un score qui n'est pas une probabilité.
    HF_TOKEN doit être configuré et la collection déjà indexée ; le client Milvus
    est fermé après la recherche. Une question vide ou une limite invalide lève ValueError.
    """
    question = question.strip()
    if not question:
        raise ValueError("La question ne doit pas être vide.")
    if not 1 <= limit <= 16384:
        raise ValueError("Le nombre de résultats doit être compris entre 1 et 16384.")

    vecteur_question = embed_question(question)

    client = MilvusClient(uri=MILVUS_URI, timeout=15)
    filtre = ""
    parametres_filtre = {}

    if opening_title is not None:
        filtre = "title == {opening_title}"
        parametres_filtre = {"opening_title": opening_title}

    try:
        resultats = client.search(
                 collection_name=COLLECTION_NAME,
                 data=[vecteur_question],
                 anns_field="vector",
                 limit=limit,
                 search_params={"metric_type": "COSINE"},
                 output_fields=["title", "section_path", "text", "source_url"],
                 timeout=30,
                 filter= filtre,
                 filter_params= parametres_filtre,
             )
             
        passages = []
        for resultat in resultats[0]:
            document = resultat["entity"]
            passages.append({
                "id": resultat["id"],
                "title": document["title"],
                "section_path": document["section_path"],
                "text": document["text"],
                "source_url": document["source_url"],
                "score": resultat["distance"],
            })

        return passages
    finally:
        client.close()
