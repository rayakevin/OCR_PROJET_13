import os
from dotenv import load_dotenv
from googleapiclient.discovery import build


def search_videos(opening: str, limit: int = 3) -> list[dict]:

    opening = opening.strip()
    if not opening:
        raise ValueError("Le nom d'ouverture renseignée est vide")

    if limit < 1 or limit > 5 :
        raise ValueError("Le nombre de vidéos doit être compris entre 1 et 5")
    
    load_dotenv()
    api_youtube = os.getenv("YOUTUBE_API_KEY")
    if not api_youtube :
        raise RuntimeError("La variable YOUTUBE_API_KEY est absente ou vide.")
 
    youtube = build("youtube", "v3", developerKey=api_youtube)

    requete = youtube.search().list(
    part="snippet",
    q=f"{opening} échecs explication",
    type="video",
    maxResults=limit,
    relevanceLanguage="fr",
    )
 
    response = requete.execute()
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
