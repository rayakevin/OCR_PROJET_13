"""Découpage structurel : paragraphes, listes et limites de section."""

from langchain_text_splitters import RecursiveCharacterTextSplitter


TAILLE_MAX = 1500
SEUIL_COURT = 300
TYPES_LISTE = {"list_item", "definition", "definition_term"}


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Regroupe les petits blocs contigus sans franchir une section.

    Les paragraphes suffisamment longs restent indépendants. Les éléments de
    liste sont regroupés, et leur introduction est conservée quand elle tient.
    Seuls les blocs trop longs sont découpés avec chevauchement.
    Le seuil court est une cible : un petit bloc isolé n'est jamais supprimé.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=TAILLE_MAX, chunk_overlap=150, length_function=len,
    )
    tous_les_chunks = []

    for document in documents:
        groupes = []
        courant = None
        for index, bloc in enumerate(document["blocks"]):
            for morceau in splitter.split_text(bloc["text"]):
                nouveau = {
                    "section_path": list(bloc["section_path"]),
                    "text": morceau,
                    "block_indices": [index],
                    "block_types": [bloc["type"]],
                }
                fusionner = False
                if courant is not None:
                    candidat = courant["text"] + "\n\n" + morceau
                    meme_section = courant["section_path"] == nouveau["section_path"]
                    # Ne pas recoller les fragments d'un même bloc trop long.
                    blocs_distincts = index not in courant["block_indices"]
                    petit_bloc = min(len(courant["text"]), len(morceau)) < SEUIL_COURT
                    suite_liste = bloc["type"] in TYPES_LISTE
                    fusionner = (
                        meme_section and blocs_distincts
                        and len(candidat) <= TAILLE_MAX
                        and (petit_bloc or suite_liste)
                    )
                if fusionner:
                    courant["text"] = candidat
                    courant["block_indices"].append(index)
                    courant["block_types"].append(bloc["type"])
                else:
                    if courant is not None:
                        groupes.append(courant)
                    courant = nouveau
        if courant is not None:
            groupes.append(courant)

        for numero, groupe in enumerate(groupes):
            section = " > ".join(groupe["section_path"])
            types = set(groupe["block_types"])
            tous_les_chunks.append({
                "id": f"{document['id']}_chunk_{numero}",
                "document_id": document["id"],
                "title": document["title"],
                "source_url": document["source_url"],
                "language": document["language"],
                "section_path": groupe["section_path"],
                "type": next(iter(types)) if len(types) == 1 else "mixed",
                "block_indices": groupe["block_indices"],
                "block_types": groupe["block_types"],
                "text": groupe["text"],
                "embedding_text": f"{document['title']}\nSection : {section}\n\n{groupe['text']}",
            })
    return tous_les_chunks
