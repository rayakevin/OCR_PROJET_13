from fastapi import FastAPI
from fastapi import HTTPException
import httpx
import json
from fastapi.responses import JSONResponse
from backend.app.services.embedding_service import EmbeddingError
from backend.app.services.youtube_service import YouTubeError
from pymilvus.exceptions import MilvusException
from backend.app.services.stockfish_service import StockfishError

from backend.app.services.chess_service import inspect_position
from backend.app.services.vector_search_service import search_documents
from backend.app.services.youtube_service import  search_videos

from backend.app.schemas import OpeningMovesResponse, PositionResponse, VectorSearchResponse, VideoSearchResponse
from backend.app.graphs.chess_graph import graph

from googleapiclient.errors import HttpError

from openai import APIError, APITimeoutError
from pydantic import ValidationError


from pymongo.errors import ConnectionFailure
from backend.app.services.analysis_repository import get_analysis

from backend.app.schemas import AnalysisRequest, AnalysisCreatedResponse
from backend.app.services.analysis_repository import get_analysis, save_analysis

from fastapi import FastAPI, HTTPException, Query

from backend.app.services.analysis_repository import (
    get_analysis,
    save_analysis,
    list_analyses,
)

app = FastAPI()


@app.exception_handler(EmbeddingError)
@app.exception_handler(YouTubeError)
async def external_service_error_handler(request, erreur):
    """Expose le même message maîtrisé pour la recherche, le graphe et la sauvegarde."""
    return JSONResponse(status_code=erreur.status_code, content={"detail": str(erreur)})


@app.exception_handler(StockfishError)
async def stockfish_error_handler(request, erreur: StockfishError):
    """Retourne une indisponibilité explicite au lieu d'une erreur moteur brute."""
    return JSONResponse(status_code=503, content={"detail": str(erreur)})


@app.exception_handler(MilvusException)
async def milvus_error_handler(request, erreur: MilvusException):
    """Masque les détails internes de Milvus sur toutes les routes de recherche."""
    return JSONResponse(
        status_code=503,
        content={"detail": "La recherche documentaire est indisponible."},
    )

@app.get("/api/v1/healthcheck")
async def healthcheck():
    """Confirme que FastAPI répond, sans sonder les services externes."""
    return {"message": "API is healthy!"}

@app.get("/api/v1/position", response_model=PositionResponse)
async def get_position(fen: str):
    """Valide la FEN et expose le statut de la partie ; une FEN invalide produit un HTTP 400."""
    try:
        return inspect_position(fen)
    except ValueError as erreur:
        raise HTTPException(status_code=400, detail=str(erreur))

def run_analysis(fen: str):

    """Exécute le graphe commun aux routes GET et POST.

    Initialise les ressources vides et traduit les exceptions prises en charge
    ici en erreurs HTTP. Cette fonction ne persiste aucun résultat ; le POST
    se charge ensuite de valider et d'enregistrer la réponse.
    """
    etat_initial = {
    "fen": fen,
    "game_over": False,
    "termination": None,
    "moves": [],
    "games": [],
    "source": None,
    "opening": None,
    "documents": [],
    "videos": [],
    "explanation": None,
    }

    try:
        return graph.invoke(etat_initial)

    except APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="La génération Groq ne répond pas à temps.",
        )

    except APIError:
        raise HTTPException(
            status_code=502,
            detail="La génération Groq a échoué.",
        )

    except ValidationError:
        raise HTTPException(
            status_code=502,
            detail="La réponse générée ne respecte pas le format attendu.",
        )

    except ValueError as erreur:
            raise HTTPException(status_code=400, detail=str(erreur))
    except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Lichess ne répond pas à temps.")
    except httpx.HTTPStatusError:
            raise HTTPException(status_code=502, detail="Lichess a renvoyé une erreur.")
    except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Impossible de contacter Lichess.")
    except HttpError:
        raise HTTPException(status_code=502,detail="La recherche YouTube a échoué.")
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Un service nécessaire à l’analyse est mal configuré ou indisponible.")

@app.get("/api/v1/opening-moves", response_model=OpeningMovesResponse)
def get_opening_moves_endpoint(fen: str):
    """Calcule une analyse sans la sauvegarder dans MongoDB."""
    return run_analysis(fen)

@app.get("/api/v1/vector-search",response_model=VectorSearchResponse)
def get_vector_search_endpoint(question:str, limit: int = 3):

    """Recherche des passages documentaires pour une question libre."""
    try:
        passages = search_documents(question, limit)
        return {
              "question" : question,
              "results": passages,
        }
    except ValueError as erreur:
            raise HTTPException(status_code=400, detail=str(erreur))


@app.get("/api/v1/videos/{opening}", response_model=VideoSearchResponse)
def get_videos_endpoint(opening: str, limit: int = 3):
    """Recherche des vidéos pour un nom d’ouverture, indépendamment du graphe."""
    try :
        videos=search_videos(opening, limit)
        
        return {
            "opening":opening,
            "videos":videos,
        }
    except ValueError as erreur:
            raise HTTPException(status_code=400, detail=str(erreur))
    except RuntimeError :
            raise HTTPException(status_code=500, detail="Le servie YouTube n'est pas configuré")
    except HttpError:
        raise HTTPException(
        status_code=502,
        detail="La recherche YouTube a échoué.",
    )

@app.get("/api/v1/analyses/{analysis_id}")
def get_analysis_endpoint(analysis_id: str):
    """Relit une analyse : 400 si ID mal formé, 404 si absent, 503 si connexion indisponible."""
    try:
        analyse = get_analysis(analysis_id)
    except ValueError as erreur:
        raise HTTPException(
            status_code=400,
            detail=str(erreur),
        ) from erreur
    except ConnectionFailure as erreur:
        raise HTTPException(
            status_code=503,
            detail="La base de données est indisponible.",
        ) from erreur

    if analyse is None:
        raise HTTPException(
            status_code=404,
            detail="Analyse introuvable.",
        )

    return analyse

@app.post(
    "/api/v1/analyses",
    response_model=AnalysisCreatedResponse,
    status_code=201,
)
def create_analysis_endpoint(request: AnalysisRequest):
    """Calcule, valide et enregistre une nouvelle analyse, puis répond en HTTP 201.

    Chaque appel réussi crée un document distinct, même pour une FEN identique.
    Une erreur de stockage empêche la réponse de succès, même si le calcul a abouti.
    """
    resultat = run_analysis(request.fen)

    # Vérifier le résultat avant de l’enregistrer.
    try:
        analyse = OpeningMovesResponse.model_validate(resultat)
    except ValidationError as erreur:
        raise HTTPException(
            status_code=502,
            detail="Le résultat de l’analyse ne respecte pas le format attendu.",
        ) from erreur

    try:
        analysis_id = save_analysis(
            fen=analyse.fen,
            result=analyse.model_dump(mode="json"),
        )
    except ConnectionFailure as erreur:
        raise HTTPException(
            status_code=503,
            detail="Impossible d’enregistrer l’analyse : la base est indisponible.",
        ) from erreur

    return {
        "id": analysis_id,
        "result": analyse,
    }

@app.get("/api/v1/analyses")
def list_analyses_endpoint(limit: int = Query(default=10, ge=1, le=50)):
    """Renvoie les résumés les plus récents ; FastAPI borne limit entre 1 et 50."""
    try:
        return list_analyses(limit=limit)
    except ConnectionFailure as erreur:
        raise HTTPException(
            status_code=503,
            detail="La base de données est indisponible.",
        ) from erreur
