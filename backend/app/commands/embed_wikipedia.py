"""Encode le corpus français ; vérifie les fichiers existants avec --reuse.

uv run python -m backend.app.commands.embed_wikipedia
uv run python -m backend.app.commands.embed_wikipedia --reuse
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from backend.app.commands._common import WIKIPEDIA_DIR

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse", action="store_true", help="Recharger les vecteurs après vérification du corpus")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--data-dir", type=Path, default=WIKIPEDIA_DIR)
    args = parser.parse_args()

    dossier = args.data_dir
    chemin_chunks = dossier / "wikipedia_chunks.json"
    chemin_vecteurs = dossier / "wikipedia_embeddings.npy"
    chemin_manifest = dossier / "wikipedia_embeddings_manifest.json"
    contenu = chemin_chunks.read_bytes()
    empreinte = hashlib.sha256(contenu).hexdigest()
    chunks = json.loads(contenu)
    textes = [chunk["embedding_text"] for chunk in chunks]
    ids = [chunk["id"] for chunk in chunks]
    if not textes or len(ids) != len(set(ids)):
        raise ValueError("Corpus vide ou identifiants dupliqués")

    # Le modèle est déjà téléchargé : utiliser le cache local sans accès réseau.
    model = SentenceTransformer(MODEL_ID, device=args.device, local_files_only=True)

    if args.reuse:
        manifest = json.loads(chemin_manifest.read_text(encoding="utf-8"))
        if (manifest["chunks_sha256"] != empreinte
                or manifest["chunk_ids"] != ids
                or manifest["model"] != MODEL_ID
                or manifest["text_field"] != "embedding_text"):
            raise ValueError("Le corpus ou le modèle a changé : relancer sans --reuse")
        if hashlib.sha256(chemin_vecteurs.read_bytes()).hexdigest() != manifest["vectors_sha256"]:
            raise ValueError("Le fichier de vecteurs ne correspond pas au manifeste")
        vecteurs = np.load(chemin_vecteurs, allow_pickle=False)
    else:
        # Vérifier que le tokenizer ne tronquera aucun passage.
        longueurs = [len(model.tokenizer.encode(t)) for t in textes]
        if max(longueurs) > model.max_seq_length:
            raise ValueError("Un passage dépasse la capacité du modèle : revoir le découpage")
        vecteurs = model.encode(
            textes, batch_size=8, show_progress_bar=True,
            normalize_embeddings=True, convert_to_numpy=True,
        )
        # Le modèle peut calculer en précision réduite sur GPU. Stocker en float32
        # et renormaliser pour éviter les écarts d'arrondi de cette précision.
        vecteurs = np.asarray(vecteurs, dtype=np.float32)
        normes = np.linalg.norm(vecteurs, axis=1, keepdims=True)
        if not np.isfinite(normes).all() or np.any(normes == 0):
            raise ValueError("Le modèle a produit un vecteur nul ou non fini")
        vecteurs = vecteurs / normes

    dimension = model.get_embedding_dimension()
    assert vecteurs.shape == (len(chunks), dimension)
    assert np.isfinite(vecteurs).all()
    assert np.allclose(np.linalg.norm(vecteurs, axis=1), 1, atol=1e-4)

    if not args.reuse:
        temporaire = chemin_vecteurs.with_suffix(".tmp")
        with temporaire.open("wb") as fichier:
            np.save(fichier, vecteurs, allow_pickle=False)
        temporaire.replace(chemin_vecteurs)
        manifest = {
            "model": MODEL_ID,
            "model_revision": getattr(model[0].auto_model.config, "_commit_hash", None),
            "text_field": "embedding_text",
            "normalized": True,
            "shape": list(vecteurs.shape),
            "max_input_tokens": max(longueurs),
            "chunks_sha256": empreinte,
            "vectors_sha256": hashlib.sha256(chemin_vecteurs.read_bytes()).hexdigest(),
            "chunk_ids": ids,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        temporaire = chemin_manifest.with_suffix(".tmp")
        temporaire.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporaire.replace(chemin_manifest)

    print("Forme des vecteurs :", vecteurs.shape)


if __name__ == "__main__":
    main()
