from fastapi import FastAPI
from fastapi import HTTPException
import httpx
import json

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

@app.get("/api/v1/healthcheck")
async def healthcheck():
    return {"message": "API is healthy!"}

@app.get("/api/v1/position", response_model=PositionResponse)
async def get_position(fen: str):
    try:
        return inspect_position(fen)
    except ValueError as erreur:
        raise HTTPException(status_code=400, detail=str(erreur))

def run_analysis(fen: str):

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
    return run_analysis(fen)

@app.get("/api/v1/vector-search",response_model=VectorSearchResponse)
def get_vector_search_endpoint(question:str, limit: int = 3):

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
    try:
        return list_analyses(limit=limit)
    except ConnectionFailure as erreur:
        raise HTTPException(
            status_code=503,
            detail="La base de données est indisponible.",
        ) from erreur