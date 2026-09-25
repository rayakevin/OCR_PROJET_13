from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from backend.app.services.chess_service import inspect_position
from backend.app.services.lichess_service import get_opening_moves
from backend.app.services.stockfish_service import analyse_position
from backend.app.services.opening_service import get_opening_title
from backend.app.services.vector_search_service import search_documents
from backend.app.services.youtube_service import search_videos


class ChessState(TypedDict):
    fen:  str
    game_over: bool
    termination: str | None
    moves: list[dict]
    games: list[dict]
    source : str | None
    opening: dict [str,str] | None
    documents: list[dict]
    videos: list[dict]

def validate_position(state : ChessState):
    fen = state["fen"]
    position = inspect_position(fen)
    return {
        "game_over": position["game_over"],
        "termination": position["termination"],
    }

def fetch_lichess(state: ChessState):
    coups, parties, ouverture = get_opening_moves(state["fen"])

    return {
        "moves": coups,
        "games": parties,
        "source": "lichess",
        "opening": ouverture,
    }

def route_after_validation(state: ChessState):
    if state["game_over"]:
        return END
    return "fetch"

def analyse_stockfish(state: ChessState):
    coups = analyse_position(state["fen"])
    return {
        "moves": [coups],
        "games": [],
        "source": "stockfish",
        }

def route_after_fetch(state: ChessState):
    if state["moves"]:
        return "documents"
    return "stockfish"

def fetch_videos(state: ChessState):
    titre = get_opening_title(state["opening"])
    if titre : 
        videos = search_videos(
            opening=titre,
            limit=2,
        )
        return {"videos": videos}
    
    else :
            return {"videos": []}

def fetch_documents(state: ChessState):
    titre = get_opening_title(state["opening"])
    if titre : 
            passages = search_documents(
        question=f"Quels sont les principes et les plans de {titre} ?",
        opening_title=titre,
        limit=3,
    )
            return {"documents": passages}
    else :
            return {"documents": []}


builder = StateGraph(ChessState)
builder.add_node("validation", validate_position)
builder.add_edge(START, "validation")
builder.add_conditional_edges("validation", route_after_validation)
builder.add_node("fetch",fetch_lichess)
builder.add_conditional_edges("fetch", route_after_fetch)
builder.add_node("stockfish",analyse_stockfish)
builder.add_edge("stockfish",END)
builder.add_node("documents", fetch_documents)
builder.add_node("videos", fetch_videos)
builder.add_edge("documents", "videos")
builder.add_edge("videos", END)


graph = builder.compile()