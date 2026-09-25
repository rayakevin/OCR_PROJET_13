"""Extraction du texte des articles Wikipédia pour le corpus de comparaison."""

from urllib.parse import unquote, urlparse

import httpx
from bs4 import BeautifulSoup


# Les sections bibliographiques ne servent pas d'explications échiquéennes.
SECTIONS_EXCLUES = {
    "see also", "references", "notes", "footnotes", "sources", "citations",
    "bibliography", "further reading", "external links", "notes and references",
    "voir aussi", "notes et références", "références", "bibliographie",
    "liens externes", "articles connexes", "sources et références",
}


def extract_wikipedia(url: str, user_agent: str, language: str = "en") -> dict:
    """Télécharge un article et conserve ses blocs et leur chemin de section.

    user_agent doit identifier le programme et fournir un contact joignable.
    language décrit la langue de l'URL fournie ; il ne traduit pas la page.
    blocks conserve les paragraphes, éléments de liste et définitions.
    text reste disponible pour les scripts utilisant le texte complet.
    Les erreurs HTTP et les contenus manquants sont remontés à l'appelant.
    """
    response = httpx.get(
        url,
        headers={"User-Agent": user_agent},
        follow_redirects=True,
        timeout=20.0,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    titre = soup.find("h1")
    bloc = soup.find("div", class_="mw-parser-output")
    if titre is None or bloc is None:
        raise ValueError(f"Titre ou contenu Wikipédia introuvable : {url}")

    # Retirer les éléments annexes avant de parcourir le texte.
    for element in bloc.select(
        "table, script, style, .reference, .reflist, .mw-editsection, "
        ".navbox, .hatnote, .shortdescription, .thumb, figure, .toc, "
        ".metadata, .noprint"
    ):
        element.decompose()

    morceaux = []
    blocks = []
    niveau_exclu = None
    titres_section = {}
    for element in bloc.find_all(["h2", "h3", "h4", "h5", "h6", "p", "li", "dt", "dd"]):
        # Un élément peut être imbriqué dans une liste : éviter les doublons.
        if element.find_parent(["p", "li", "dt", "dd"]) is not None:
            continue
        texte = " ".join(element.get_text(separator=" ", strip=True).split())
        if not texte:
            continue

        if element.name in ["h2", "h3", "h4", "h5", "h6"]:
            niveau = int(element.name[1:])
            titres_section = {
                ancien_niveau: ancien_titre
                for ancien_niveau, ancien_titre in titres_section.items()
                if ancien_niveau < niveau
            }
            titres_section[niveau] = texte

            # Une rubrique exclue englobe aussi toutes ses sous-sections.
            if niveau_exclu is not None:
                if niveau > niveau_exclu:
                    continue
                niveau_exclu = None
            if texte.casefold() in SECTIONS_EXCLUES:
                niveau_exclu = niveau
                continue

            # Les titres sont des métadonnées, pas des blocs isolés à encoder.
            morceaux.append(texte)
            continue

        if niveau_exclu is not None:
            continue

        types_blocs = {
            "p": "paragraph", "li": "list_item",
            "dt": "definition_term", "dd": "definition",
        }
        blocks.append({
            "section_path": list(titres_section.values()) or ["Introduction"],
            "type": types_blocs[element.name],
            "text": texte,
        })
        morceaux.append(texte)

    if not blocks:
        raise ValueError(f"Aucun texte exploitable : {url}")

    nom_page = unquote(urlparse(str(response.url)).path.rsplit("/", 1)[-1])
    return {
        "id": f"wikipedia_{language}_{nom_page}",
        "title": titre.get_text(" ", strip=True),
        "source_url": str(response.url),
        "language": language,
        "blocks": blocks,
        "text": "\n\n".join(morceaux),
    }
