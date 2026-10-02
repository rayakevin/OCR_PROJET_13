"""Prépare le lot versionné du corpus, sans réseau ni écriture dans Milvus.

uv run python -m backend.app.commands.package_corpus
Pour un autre lot : --output /chemin/lot.zip
"""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from backend.app.commands._common import PROJECT_ROOT, WIKIPEDIA_DIR
from backend.app.commands._corpus_bundle import DATA_FILES
from backend.app.commands.index_milvus import charger_entrees


def creer_lot(dossier: Path, sortie: Path) -> str:
    """Valide, attribue les sources et produit une archive déterministe.

    Un lot différent déjà présent n'est pas écrasé : choisir un nouveau nom pour
    conserver les versions distribuées. Les poids du modèle ne sont pas inclus.
    """
    entrees = charger_entrees(dossier)
    sources = sorted({(e["title"], e["source_url"]) for e in entrees})
    manifeste = json.loads((dossier / DATA_FILES[2]).read_text(encoding="utf-8"))
    notice = (
        "# Sources du corpus français\n\n"
        f"{len(entrees)} passages ; {len(sources)} articles.\n\n"
        "Textes : contributeurs et contributrices de Wikipédia en français, "
        "attribués par les liens vers les articles ci-dessous et leurs historiques.\n"
        "Licence des textes adaptés : CC BY-SA 4.0, "
        "https://creativecommons.org/licenses/by-sa/4.0/\n"
        "Conditions de réutilisation : "
        "https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use/en#7._Licensing_of_Content\n\n"
        "Transformations : extraction du texte HTML, nettoyage, sélection et regroupement "
        "en passages par section, ajout du titre et du chemin de section pour l'encodage. "
        "Aucune image n'est incluse. Les révisions Wikipédia exactes n'ont pas été "
        "enregistrées lors de la collecte ; les liens peuvent avoir évolué. "
        "L'archive fige les textes effectivement encodés.\n\n"
        f"Modèle : {manifeste['model']} ; révision : {manifeste.get('model_revision', 'non enregistrée')}.\n"
        f"Date d'encodage : {manifeste['created_at']}.\n"
        "Les vecteurs sont des données calculées ; aucun poids du modèle n'est redistribué.\n\n"
    )
    notice += "\n".join(f"- [{titre}]({url}) — [historique]({url}?action=history)" for titre, url in sources)
    fichiers = {nom: (dossier / nom).read_bytes() for nom in DATA_FILES}
    fichiers["SOURCES.md"] = (notice + "\n").encode("utf-8")
    tampon = BytesIO()
    with ZipFile(tampon, "w", compression=ZIP_DEFLATED) as archive:
        for nom, contenu in fichiers.items():
            info = ZipInfo(nom, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, contenu)
    contenu = tampon.getvalue()
    if sortie.exists() and sortie.read_bytes() != contenu:
        raise ValueError("Un autre lot existe déjà à cet emplacement. Choisir un nouveau --output.")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_bytes(contenu)
    empreinte = hashlib.sha256(contenu).hexdigest()
    sortie.with_suffix(sortie.suffix + ".sha256").write_text(
        f"{empreinte}  {sortie.name}\n", encoding="utf-8"
    )
    print(f"Lot prêt : {sortie} ({len(contenu)} octets, {len(entrees)} passages)")
    return empreinte


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=WIKIPEDIA_DIR)
    parser.add_argument("--output", type=Path,
                        default=PROJECT_ROOT / "resources/corpus/chess-openings-fr-v1.zip")
    args = parser.parse_args()
    creer_lot(args.data_dir, args.output)


if __name__ == "__main__":
    main()
