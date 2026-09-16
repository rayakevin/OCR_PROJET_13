from fastapi import FastAPI
from fastapi import HTTPException
import httpx
import os
from dotenv import load_dotenv

from backend.app.services.chess_service import inspect_position
from backend.app.services.lichess_services import get_opening_moves 


app = FastAPI()
load_dotenv()
lichess_api_token = os.getenv("LICHESS_API_TOKEN")

@app.get("/api/v1/healthcheck")
async def healthcheck():
    return {"message": "API is healthy!"}

@app.get("/api/v1/position")
async def get_position(fen: str):
    try:
        return inspect_position(fen)
    except ValueError as erreur:
        raise HTTPException(status_code=400, detail=str(erreur))

@app.get("/api/v1/opening-moves")
def get_opening_moves_endpoint(fen: str):
    #Etape 01 on vérifie la validité de la position FEN
    try:
        position = inspect_position(fen)
    except ValueError as erreur:
        raise HTTPException(status_code=400, detail=str(erreur))
    #Etape 02 on récupère les coups d'ouverture depuis l'API Lichess

    if position["game_over"]:
        return {
            "fen": fen, 
            "game_over": True,
            "Termination": position["termination"],
            "moves": [],
        }

    try:
        coups = get_opening_moves(fen)
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Lichess ne répond pas à temps.")
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=502, detail="Lichess a renvoyé une erreur.")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Impossible de contacter Lichess.")    

   #REPRENDRE ICI POUR AJOUTER STOCKFISH

    return {
    "fen": fen,
    "game_over": False,
    "termination": None,
    "moves": coups,
    }