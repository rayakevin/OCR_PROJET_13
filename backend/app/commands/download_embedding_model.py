"""Télécharge le modèle d'embedding dans le cache Hugging Face."""

from huggingface_hub import snapshot_download

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"


def main():
    chemin = snapshot_download(repo_id=MODEL_ID)
    print(f"Modèle disponible dans : {chemin}")


if __name__ == "__main__":
    main()