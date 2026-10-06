"""Préparer un dossier de publication HF limité aux fichiers de l'application.

Ne publie rien et ne lit aucun secret. Le dossier de sortie doit être neuf.
"""

import argparse
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[3]


def prepare(output: Path) -> None:
    """Copie une liste explicite de sources ; refuse les liens symboliques."""
    output = output.resolve()
    if output.exists():
        raise ValueError("Le dossier de sortie existe déjà : choisir un nouveau dossier.")
    files = {
        ROOT / "Dockerfile.cloud": "Dockerfile",
        ROOT / "Dockerfile.cloud.dockerignore": ".dockerignore",
        ROOT / "deploy/huggingface/README.md": "README.md",
        ROOT / "pyproject.toml": "pyproject.toml",
        ROOT / "uv.lock": "uv.lock",
    }
    for path in (ROOT / "backend").rglob("*.py"):
        if "__pycache__" not in path.parts:
            files[path] = str(path.relative_to(ROOT))
    allowed = {".ts", ".html", ".css", ".scss", ".json", ".svg", ".png", ".jpg", ".webp", ".ico", ".woff", ".woff2"}
    for path in (ROOT / "frontend").rglob("*"):
        if any(part in ("node_modules", "dist", ".angular", ".git") for part in path.parts):
            continue
        if path.is_file() and path.suffix in allowed:
            files[path] = str(path.relative_to(ROOT))
    for name in ("chess-openings-fr-v1.zip", "chess-openings-fr-v1.zip.sha256", "README.md"):
        path = ROOT / "resources/corpus" / name
        files[path] = str(path.relative_to(ROOT))
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Source non régulière : {path.name}")
    output.mkdir(parents=True)
    for source, name in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(f"Dossier HF préparé : {output} ({len(files)} fichiers). Aucune publication effectuée.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output/hf-space")
    args = parser.parse_args()
    prepare(args.output)


if __name__ == "__main__":
    main()
