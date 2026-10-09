"""Point d'entrée mono-conteneur : API et build Angular sur le même port."""

import os
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from backend.app.main import app


# Fichiers aux noms fixes : sans revalidation, un visiteur garderait une version
# périmée après un déploiement. Les bundles Angular ont un nom haché et restent
# mis en cache normalement.
NO_CACHE_FILES = {"index.html", "projet.html", "projet.js", "projet.css"}


class StaticPages(StaticFiles):
    """Sert le build Angular ; les pages à nom fixe sont revalidées à chaque visite."""

    def file_response(self, full_path, stat_result, scope, status_code=200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        if Path(full_path).name in NO_CACHE_FILES:
            response.headers["Cache-Control"] = "no-cache"
        return response


static_dir = Path(os.getenv("STATIC_DIR", "/app/static"))
if not (static_dir / "index.html").is_file():
    raise RuntimeError("Build Angular absent : construire l'image Dockerfile.cloud.")

# Les routes /api/v1 sont enregistrées avant ce montage. Angular conserve ses
# URL relatives : aucun secret ni adresse de base de données dans le navigateur.
app.mount("/", StaticPages(directory=static_dir, html=True), name="angular")
