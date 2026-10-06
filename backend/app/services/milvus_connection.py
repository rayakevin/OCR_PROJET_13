"""Connexion commune au Milvus local ou à Zilliz Cloud."""

import os

from dotenv import load_dotenv
from pymilvus import MilvusClient


COLLECTION_NAME = "chess_openings_fr_v2"


def create_milvus_client() -> MilvusClient:
    """Lit la configuration à l'appel, sans journaliser le jeton d'accès.

    MILVUS_TOKEN est facultatif en local et contient une clé API Zilliz en cloud.
    L'endpoint HTTPS fourni par Zilliz conserve la vérification TLS du SDK.
    """
    load_dotenv()
    uri = os.getenv("MILVUS_URI", "http://127.0.0.1:19530").strip()
    token = os.getenv("MILVUS_TOKEN", "").strip()
    options = {"uri": uri, "timeout": 15}
    if token:
        options["token"] = token
    return MilvusClient(**options)
