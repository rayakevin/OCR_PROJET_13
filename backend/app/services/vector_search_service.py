from functools import lru_cache
import os

from pymilvus import MilvusClient
from sentence_transformers import SentenceTransformer

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
COLLECTION_NAME = "chess_openings_fr_v2"

MILVUS_URI = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cuda")

QUERY_PROMPT = (
    "Instruct: Given a question about chess openings, retrieve passages "
    "explaining the strategic ideas and plans of the specific opening "
    "or move sequence mentioned.\nQuery:"
)


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(
        MODEL_ID,
        device=EMBEDDING_DEVICE,
        local_files_only=True,
    )

def search_documents(question: str, limit: int = 3, opening_title: str | None = None,) -> list[dict]:
    question = question.strip()
    if not question:
        raise ValueError("La question ne doit pas être vide.")
    if not 1 <= limit <= 16384:
        raise ValueError("Le nombre de résultats doit être compris entre 1 et 16384.")

    model = get_embedding_model()
    vecteur_question = model.encode(
        [question],
        prompt=QUERY_PROMPT,
        normalize_embeddings=True,
    )

    client = MilvusClient(uri=MILVUS_URI, timeout=15)
    filtre = ""
    parametres_filtre = {}

    if opening_title is not None:
        filtre = "title == {opening_title}"
        parametres_filtre = {"opening_title": opening_title}

    try:
        resultats = client.search(
                 collection_name=COLLECTION_NAME,
                 data=vecteur_question.tolist(),
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

