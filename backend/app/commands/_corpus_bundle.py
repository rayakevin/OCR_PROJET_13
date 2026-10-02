"""Lecture contrôlée du lot de corpus livré avec le projet."""

from contextlib import contextmanager
import hashlib
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from zipfile import ZipFile

DATA_FILES = (
    "wikipedia_chunks.json",
    "wikipedia_embeddings.npy",
    "wikipedia_embeddings_manifest.json",
)
BUNDLE_FILES = (*DATA_FILES, "SOURCES.md")
MAX_BYTES = 32 * 1024 * 1024


@contextmanager
def ouvrir_lot(archive: Path):
    """Vérifie SHA-256 et contenu avant de fournir un dossier temporaire.

    Le checksum détecte une corruption ; la confiance repose sur la provenance
    du dépôt. Aucun chemin de l'archive n'est utilisé pour une extraction libre.
    """
    if archive.stat().st_size > MAX_BYTES:
        raise ValueError("Archive trop volumineuse.")
    empreinte = archive.with_suffix(archive.suffix + ".sha256").read_text().strip().split()
    if not empreinte or not re.fullmatch(r"[0-9a-f]{64}", empreinte[0]):
        raise ValueError("Empreinte SHA-256 absente ou invalide.")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != empreinte[0]:
        raise ValueError("L'archive ne correspond pas à son empreinte SHA-256.")
    with ZipFile(archive) as lot, TemporaryDirectory(prefix="chess-corpus-") as temporaire:
        infos = lot.infolist()
        if len(infos) != len(BUNDLE_FILES) or set(lot.namelist()) != set(BUNDLE_FILES):
            raise ValueError("Le lot ne contient pas exactement les fichiers attendus.")
        if sum(info.file_size for info in infos) > MAX_BYTES:
            raise ValueError("Contenu décompressé trop volumineux.")
        dossier = Path(temporaire)
        for nom in BUNDLE_FILES:
            (dossier / nom).write_bytes(lot.read(nom))
        yield dossier
