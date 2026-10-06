"""Vérifier les deux bases distantes sans créer ni modifier de données.

Lancement : uv run --env-file .env.cloud python -m backend.app.commands.check_cloud
Les erreurs affichées ne contiennent ni chaîne de connexion ni clé d'accès.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient

from backend.app.services.milvus_connection import COLLECTION_NAME, create_milvus_client
from backend.app.services.hf_history_repository import connection


def main() -> int:
    """Retourne un code non nul si une connexion ou le corpus est indisponible."""
    load_dotenv()
    history = os.getenv("HISTORY_BACKEND", "mongodb")
    if history not in ("mongodb", "hf_dataset"):
        print("HISTORY_BACKEND doit être mongodb ou hf_dataset.")
        return 1
    storage_names = ("HF_HISTORY_REPO", "HF_HISTORY_TOKEN") if history == "hf_dataset" else ("MONGODB_URI",)
    missing = [name for name in (*storage_names, "MILVUS_URI", "MILVUS_TOKEN")
               if not os.getenv(name, "").strip()]
    if missing:
        print("Configuration manquante : " + ", ".join(missing))
        return 1

    ok = True
    try:
        if history == "hf_dataset":
            api, repo_id = connection()
            if not api.repo_info(repo_id=repo_id, repo_type="dataset").private:
                raise ValueError("Le Dataset doit être privé")
            api.list_repo_files(repo_id=repo_id, repo_type="dataset")
            print("Historique HF : Dataset privé accessible en lecture.")
        else:
            with MongoClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=5000) as client:
                client.admin.command("ping")
                client["chess_coach"]["analyses"].find_one({}, {"_id": 1})
            print("MongoDB : connexion et lecture autorisées.")
    except Exception:
        print("Historique indisponible : vérifier le secret, les accès et la confidentialité du Dataset HF."
              if history == "hf_dataset" else
              "MongoDB indisponible : vérifier la chaîne de connexion, les droits et les IP autorisées.")
        ok = False

    client = None
    try:
        client = create_milvus_client()
        if not client.has_collection(collection_name=COLLECTION_NAME):
            print("Zilliz : connexion réussie, corpus à importer.")
            ok = False
        else:
            result = client.query(
                collection_name=COLLECTION_NAME, filter="",
                output_fields=["count(*)"], consistency_level="Strong", timeout=15,
            )
            count = result[0]["count(*)"]
            print(f"Zilliz : collection accessible, {count} passages.")
            ok = ok and count > 0
    except Exception:
        print("Zilliz indisponible : vérifier endpoint HTTPS, clé et état de la collection.")
        ok = False
    finally:
        if client is not None:
            client.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
