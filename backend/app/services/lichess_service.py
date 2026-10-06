from dotenv import load_dotenv
import os
import httpx
import chess

load_dotenv()
lichess_api_token = os.getenv("LICHESS_API_TOKEN")

def explorer_params(fen: str, base_fen: str | None = None, played_moves: list[str] | None = None) -> dict:
    """Rejoue les coups fournis avant d’utiliser le contexte d’ouverture Lichess."""
    params = {"fen": fen, "topGames": 2, "recentGames": 0, "moves": 3}
    if played_moves:
        if not base_fen:
            raise ValueError("La position de départ est nécessaire pour vérifier les coups.")
        board = chess.Board(base_fen)
        if not board.is_valid():
            raise ValueError("Position de départ invalide.")
        for move in played_moves:
            board.push_uci(move)
        if board.fen() != chess.Board(fen).fen():
            raise ValueError("Les coups fournis ne correspondent pas à la position analysée.")
        params.update(fen=base_fen, play=",".join(played_moves))
    return params


def get_opening_moves(fen, base_fen=None, played_moves=None):

    """Interroge le catalogue masters et renvoie (coups, parties, ouverture).

    Demande jusqu'à trois coups et deux parties. La fréquence est la proportion
    des parties de cette position ayant joué le coup, pas un taux de victoire.
    Une liste vide ne prouve pas que la position est inconnue de toute théorie.
    Les erreurs HTTP et réseau sont propagées à l'appelant.
    """
    params = explorer_params(fen, base_fen, played_moves)
    response = httpx.get("https://explorer.lichess.org/masters",    
                        headers={"Authorization": f"Bearer {lichess_api_token}"},
                        params=params, timeout=15)

    response.raise_for_status()
    data = response.json()
    moves = data["moves"]
    resultats = []
    total_position = data["white"] + data["draws"] + data["black"]

    for coup in moves : 
        notation = coup["san"]

        if coup["opening"] is not None:
            name = coup["opening"]["name"]
        else:
            name = None

        total = coup["white"] + coup["draws"] + coup["black"]
        resultat = {
        "uci": coup["uci"],
        "san": notation,
        "opening": name,
        "games_count": total,
        "frequency": total / total_position if total_position > 0 else 0
        }
        resultats.append(resultat)

    return resultats,data["topGames"], data.get("opening")
