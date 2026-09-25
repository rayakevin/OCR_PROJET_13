"""Importer les chunks français et leurs embeddings dans Milvus.

Lancement : uv run python -m backend.app.commands.index_milvus
Le script ne recalcule aucun embedding et ne supprime aucune collection.
Un nouvel import remplace les entrées portant les mêmes identifiants.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from pymilvus import DataType, MilvusClient
from backend.app.commands._common import WIKIPEDIA_DIR


MILVUS_URI = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
COLLECTION_NAME = "chess_openings_fr_v2"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
DIMENSION = 1024
TEXT_FIELDS = {
    "id": 512,
    "document_id": 512,
    "title": 1024,
    "source_url": 2048,
    "language": 8,
    "text": 8192,
    "embedding_text": 16384,
}


def charger_entrees(dossier: Path) -> list[dict]:
    """Contrôler les fichiers et associer chaque chunk au bon vecteur."""
    chemin_chunks = dossier / "wikipedia_chunks.json"
    chemin_vecteurs = dossier / "wikipedia_embeddings.npy"
    manifeste = json.loads(
        (dossier / "wikipedia_embeddings_manifest.json").read_text(encoding="utf-8")
    )
    contenu_chunks = chemin_chunks.read_bytes()
    if hashlib.sha256(contenu_chunks).hexdigest() != manifeste["chunks_sha256"]:
        raise ValueError("Les chunks ont changé : recalculer les embeddings avant l'import.")
    if hashlib.sha256(chemin_vecteurs.read_bytes()).hexdigest() != manifeste["vectors_sha256"]:
        raise ValueError("Le fichier de vecteurs ne correspond pas au manifeste.")
    if manifeste["model"] != MODEL_ID or manifeste["text_field"] != "embedding_text":
        raise ValueError("Le modèle ou le texte encodé ne correspond pas à cet import.")

    chunks = json.loads(contenu_chunks)
    vecteurs = np.load(chemin_vecteurs, allow_pickle=False)
    identifiants = [chunk["id"] for chunk in chunks]
    if not chunks or len(set(identifiants)) != len(identifiants):
        raise ValueError("Corpus vide ou identifiants dupliqués.")
    if identifiants != manifeste["chunk_ids"]:
        raise ValueError("L'ordre des chunks ne correspond pas à celui des vecteurs.")
    if vecteurs.shape != (len(chunks), DIMENSION):
        raise ValueError(f"Dimensions incorrectes : {vecteurs.shape}.")
    if not np.isfinite(vecteurs).all():
        raise ValueError("Les embeddings contiennent des valeurs non finies.")
    if not np.allclose(np.linalg.norm(vecteurs, axis=1), 1, atol=1e-4):
        raise ValueError("Les embeddings ne sont pas normalisés comme prévu.")

    entrees = []
    for chunk, vecteur in zip(chunks, vecteurs, strict=True):
        entree = {}
        for champ, limite in TEXT_FIELDS.items():
            valeur = chunk[champ]
            if not isinstance(valeur, str) or len(valeur.encode("utf-8")) > limite:
                raise ValueError(f"Champ {champ} invalide ou trop long : {chunk['id']}.")
            entree[champ] = valeur
        if not isinstance(chunk["section_path"], list) or not all(
            isinstance(titre, str) for titre in chunk["section_path"]
        ):
            raise ValueError(f"Chemin de section invalide : {chunk['id']}.")
        entree["section_path"] = chunk["section_path"]
        entree["vector"] = vecteur.tolist()
        entrees.append(entree)
    return entrees


def preparer_collection(client: MilvusClient) -> None:
    """Créer la collection si nécessaire, sinon vérifier son schéma."""
    if not client.has_collection(collection_name=COLLECTION_NAME):
        schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
        for champ, limite in TEXT_FIELDS.items():
            schema.add_field(
                field_name=champ, datatype=DataType.VARCHAR,
                max_length=limite, is_primary=(champ == "id"),
            )
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=DIMENSION)
        schema.add_field(field_name="section_path", datatype=DataType.JSON)
        index_params = client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")
        client.create_collection(
            collection_name=COLLECTION_NAME, schema=schema, index_params=index_params,
        )
        print("Collection créée :", COLLECTION_NAME)

    description = client.describe_collection(collection_name=COLLECTION_NAME)
    champs = {champ["name"]: champ for champ in description["fields"]}
    if set(champs) != set(TEXT_FIELDS) | {"vector", "section_path"}:
        raise ValueError("La collection existante ne possède pas les champs attendus.")
    for nom, limite in TEXT_FIELDS.items():
        champ = champs[nom]
        if champ["type"] != DataType.VARCHAR or int(champ["params"]["max_length"]) < limite:
            raise ValueError(f"Schéma incompatible pour le champ {nom}.")
    if description.get("auto_id") or not champs["id"].get("is_primary"):
        raise ValueError("La collection doit utiliser nos identifiants comme clé primaire.")
    if (champs["vector"]["type"] != DataType.FLOAT_VECTOR
            or int(champs["vector"]["params"]["dim"]) != DIMENSION
            or champs["section_path"]["type"] != DataType.JSON):
        raise ValueError("Type de vecteur, dimension ou champ JSON incompatible.")
    client.load_collection(collection_name=COLLECTION_NAME)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=WIKIPEDIA_DIR)
    parser.add_argument("--check-only", action="store_true", help="Vérifier les fichiers sans contacter Milvus")
    args = parser.parse_args()
    # Valider les fichiers avant toute connexion ou écriture dans Milvus.
    entrees = charger_entrees(args.data_dir)
    print(f"Fichiers vérifiés : {len(entrees)} entrées, dimension {DIMENSION}.")
    if args.check_only:
        return
    client = MilvusClient(uri=MILVUS_URI)
    try:
        preparer_collection(client)
        resultat = client.upsert(collection_name=COLLECTION_NAME, data=entrees)
        print("Entrées importées :", resultat["upsert_count"])
        if resultat["upsert_count"] != len(entrees):
            raise RuntimeError("Le nombre d'entrées importées est inattendu.")
        comptage = client.query(
            collection_name=COLLECTION_NAME, filter="",
            output_fields=["count(*)"], consistency_level="Strong",
        )
        total = comptage[0]["count(*)"]
        print(f"Entrées visibles dans {COLLECTION_NAME} : {total}")
        if total != len(entrees):
            print("Attention : le total diffère du corpus. Les anciens identifiants absents "
                  "de cet import ne sont pas supprimés par upsert.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
