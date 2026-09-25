"""Redécouper le corpus Wikipédia local sans le télécharger.

uv run python -m backend.app.commands.chunk_wikipedia
Recalculer ensuite les embeddings si les chunks ont changé.
"""

import argparse
import json
from pathlib import Path

from backend.app.commands._common import WIKIPEDIA_DIR, ecrire_json
from backend.app.services.chunking_service import chunk_documents


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=WIKIPEDIA_DIR)
    args = parser.parse_args()
    documents = json.loads((args.data_dir / "wikipedia.json").read_text(encoding="utf-8"))
    chunks = chunk_documents(documents)
    ecrire_json(args.data_dir / "wikipedia_chunks.json", chunks)
    print(f"{len(documents)} documents ; {len(chunks)} chunks enregistrés.")


if __name__ == "__main__":
    main()
