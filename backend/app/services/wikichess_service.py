import httpx
from bs4 import BeautifulSoup


def extract_wikichess(url: str, title: str) -> dict:
    '''
    Fonction qui prend en argument l'url et le titre d'une page wikichess présente sur "https://ficgs.com"
    et retourne un dictionnaire qui comprend ('id','title','source_url', 'language', 'text')

    Args :
    - url : str
    - title : str
    Return : 
    - wikichess_dict : Dict
    '''
    response = httpx.get(url=url, follow_redirects=True, timeout=20.0)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser",from_encoding="windows-1252",)
    bloc = soup.find("div", attrs={"align":"justify"})

    if bloc is not None:
        texte = bloc.get_text(separator="\n", strip=True)
        explication = texte.split("============", maxsplit=1)[0].strip()
        identifiant = url.replace("https://ficgs.com/","")
        identifiant = identifiant.replace(".html","")

        wikichess_dict = {
        "id":identifiant,
        "title":title,
        "source_url": url,
        "language": "en",
        "text": explication,
        }

    else:
        raise ValueError(f"Le bloc attendu n'a pas été trouvé sur {url}")

    return wikichess_dict