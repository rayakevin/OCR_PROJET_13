from typing import TypedDict
from langgraph.graph import StateGraph, START, END

from backend.app.services.chess_service import inspect_position
from backend.app.services.lichess_service import get_opening_moves
from backend.app.services.stockfish_service import analyse_position
from backend.app.services.opening_service import get_opening_title
from backend.app.services.vector_search_service import search_documents
from backend.app.services.youtube_service import search_videos
from backend.app.services.generation_service import generate_explanation


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
    explanation: dict | None

def validate_position(state : ChessState):
    """Valide la FEN et ne met à jour que les champs liés à la fin de partie."""
    fen = state["fen"]
    position = inspect_position(fen)
    return {
        "game_over": position["game_over"],
        "termination": position["termination"],
    }

def fetch_lichess(state: ChessState):
    """Ajoute les coups du catalogue, les parties de référence et le nom de l’ouverture."""
    coups, parties, ouverture = get_opening_moves(state["fen"])

    return {
        "moves": coups,
        "games": parties,
        "source": "lichess",
        "opening": ouverture,
    }

def route_after_validation(state: ChessState):
    """Arrête le graphe si la partie est terminée ; sinon interroge Lichess."""
    if state["game_over"]:
        return END
    return "fetch"

def analyse_stockfish(state: ChessState):
    """Produit une suggestion moteur lorsque Lichess ne fournit aucun coup."""
    coups = analyse_position(state["fen"])
    return {
        "moves": [coups],
        "games": [],
        "source": "stockfish",
        }

def route_after_fetch(state: ChessState):
    """Choisit les ressources documentaires si des coups existent, sinon Stockfish."""
    if state["moves"]:
        return "documents"
    return "stockfish"

def fetch_videos(state: ChessState):
    """Recherche des vidéos si le nom Lichess possède une correspondance française."""
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
    """Recherche les principes et plans dans le corpus filtré par ouverture."""
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


def explain_opening(state: ChessState):
    """Génère une explication documentaire de l’ouverture, ou None sans contexte couvert."""
    titre = get_opening_title(state["opening"])

    if not titre or not state["documents"]:
        return {"explanation": None}

    explication = generate_explanation(
        question=f"Quels sont les principes et les plans de {titre} ?",
        documents=state["documents"],
    )

    return {"explanation": explication.model_dump()}


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
builder.add_node("explanation", explain_opening)
builder.add_edge("videos", "explanation")
builder.add_edge("explanation", END)


graph = builder.compile()
