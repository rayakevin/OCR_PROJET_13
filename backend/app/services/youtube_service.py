import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
import httplib2


class YouTubeError(Exception):
    """Erreur de transport publique, sans détails sensibles du fournisseur."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def search_videos(opening: str, limit: int = 3) -> list[dict]:

    """Renvoie jusqu'à limit liens vidéo pour une ouverture (limite de 1 à 5).

    Privilégie les résultats en français sans garantir leur langue ou leur qualité.
    Lève ValueError pour les paramètres invalides et RuntimeError sans clé API.
    Les erreurs YouTube remontent à l'appelant ; cet appel consomme du quota.
    """
    opening = opening.strip()
    if not opening:
        raise ValueError("Le nom d'ouverture renseignée est vide")

    if limit < 1 or limit > 5 :
        raise ValueError("Le nombre de vidéos doit être compris entre 1 et 5")
    
    load_dotenv()
    api_youtube = os.getenv("YOUTUBE_API_KEY")
    if not api_youtube :
        raise RuntimeError("La variable YOUTUBE_API_KEY est absente ou vide.")
 
    transport = httplib2.Http(timeout=15)
    try:
        youtube = build(
            "youtube", "v3", developerKey=api_youtube,
            http=transport, cache_discovery=False,
        )
        requete = youtube.search().list(
            part="snippet",
            q=f"{opening} échecs explication",
            type="video",
            maxResults=limit,
            relevanceLanguage="fr",
        )
        response = requete.execute(num_retries=0)
    except TimeoutError:
        raise YouTubeError("YouTube ne répond pas à temps.", 504) from None
    except (OSError, httplib2.HttpLib2Error):
        raise YouTubeError("Impossible de contacter YouTube.") from None
    finally:
        transport.close()
    videos = []

    for item in response["items"]:
        identifiant = item["id"]["videoId"]

        video = {}

        video["id"] = identifiant
        video["title"]= item["snippet"]["title"]
        video["channel"]= item["snippet"]["channelTitle"]
        video["url"]= f"https://www.youtube.com/watch?v={identifiant}"
        videos.append(video)

    return videos
