"""Chemins et écriture JSON communs aux commandes de préparation du corpus."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
WIKIPEDIA_DIR = DATA_DIR / "wikipedia_fr"


def ecrire_json(chemin: Path, valeur) -> None:
    """Remplacer le fichier seulement une fois l'écriture terminée."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
    temporaire.write_text(
        json.dumps(valeur, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporaire.replace(chemin)
