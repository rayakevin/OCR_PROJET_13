from fastapi import FastAPI
from fastapi import HTTPException
import httpx

from backend.app.services.chess_service import inspect_position
from backend.app.services.vector_search_service import search_documents
from backend.app.schemas import OpeningMovesResponse, PositionResponse, VectorSearchResponse
from backend.app.graphs.chess_graph import graph


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

@app.get("/api/v1/opening-moves", response_model=OpeningMovesResponse)
def get_opening_moves_endpoint(fen: str):

    etat_initial = {
    "fen": fen,
    "game_over": False,
    "termination": None,
    "moves": [],
    "games": [],
    "source": None,
    "opening": None,
    "documents": [],
    }

    try:
        return graph.invoke(etat_initial)
    except ValueError as erreur:
            raise HTTPException(status_code=400, detail=str(erreur))
    except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Lichess ne répond pas à temps.")
    except httpx.HTTPStatusError:
            raise HTTPException(status_code=502, detail="Lichess a renvoyé une erreur.")
    except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Impossible de contacter Lichess.") 

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

