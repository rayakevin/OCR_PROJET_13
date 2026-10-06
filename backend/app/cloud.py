"""Point d'entrée mono-conteneur : API et build Angular sur le même port."""

import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from backend.app.main import app


static_dir = Path(os.getenv("STATIC_DIR", "/app/static"))
if not (static_dir / "index.html").is_file():
    raise RuntimeError("Build Angular absent : construire l'image Dockerfile.cloud.")

# Les routes /api/v1 sont enregistrées avant ce montage. Angular conserve ses
# URL relatives : aucun secret ni adresse de base de données dans le navigateur.
app.mount("/", StaticFiles(directory=static_dir, html=True), name="angular")
