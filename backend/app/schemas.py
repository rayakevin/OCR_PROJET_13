from pydantic import BaseModel
from typing import Literal

class PositionResponse(BaseModel):
    valid: bool
    turn: str
    legal_moves_count: int
    game_over: bool
    termination: str | None

class LichessMove(BaseModel):
    uci: str
    san: str
    opening: str | None
    games_count: int
    frequency: float

class StockfishMove(BaseModel):
    uci: str | None
    san: str | None
    score_cp: int | None
    mate: int | None

class PlayerReference(BaseModel):
    name: str
    rating: int

class GameReference(BaseModel):
    id: str
    uci: str
    white: PlayerReference
    black: PlayerReference
    winner: Literal["white","black",None]
    month: str

class DocumentSearchResult(BaseModel) :
    id: str
    title : str
    section_path: list[str]
    text: str
    source_url: str
    score: float
    

class VideoReference (BaseModel) :
    id: str
    title: str
    channel: str
    url: str

class OpeningMovesResponse(BaseModel):
    fen: str
    game_over: bool
    termination: str | None
    source: Literal["lichess","stockfish", None]
    moves: list[LichessMove] | list[StockfishMove]
    games : list[GameReference]
    opening: dict[str, str] | None
    documents: list[DocumentSearchResult]
    videos: list[VideoReference]



class VectorSearchResponse(BaseModel) : 
    question: str
    results: list[DocumentSearchResult]


class VideoSearchResponse (BaseModel) : 
    opening : str
    videos : list [VideoReference]