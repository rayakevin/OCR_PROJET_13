from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from backend.app.services.chess_service import inspect_position
from backend.app.services.lichess_service import get_opening_moves
from backend.app.services.stockfish_service import analyse_position


class ChessState(TypedDict):
    fen:  str
    game_over: bool
    termination: str | None
    moves: list[dict]
    games: list[dict]
    source : str | None

def validate_position(state : ChessState):
    fen = state["fen"]
    position = inspect_position(fen)
    return {
        "game_over": position["game_over"],
        "termination": position["termination"],
    }

def fetch_lichess(state : ChessState) :
    coups,parties = get_opening_moves(state["fen"])
    return {
        "moves":coups,
        "games": parties,
        "source": "lichess",
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
        return END
    return "stockfish"

builder = StateGraph(ChessState)
builder.add_node("validation", validate_position)
builder.add_edge(START, "validation")
builder.add_conditional_edges("validation", route_after_validation)
builder.add_node("fetch",fetch_lichess)
builder.add_conditional_edges("fetch", route_after_fetch)
builder.add_node("stockfish",analyse_stockfish)
builder.add_edge("stockfish",END)


graph = builder.compile()