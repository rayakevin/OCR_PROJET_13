import chess

def inspect_position(fen):
    
    """Valide une FEN et renvoie le trait, les coups légaux et l'issue éventuelle.

    Lève ValueError si la notation ou la position est invalide. Une FEN seule
    ne reconstitue pas l'historique nécessaire à la détection des répétitions.
    """
    try:
        board = chess.Board(fen)
    except ValueError :
        raise ValueError("Format FEN invalide. Assurez-vous que la chaîne FEN est correctement formatée.")
    
    if board.is_valid() : 
        return {
            "valid": True,
            "turn": "white" if board.turn else "black",
            "legal_moves_count": board.legal_moves.count(),
            "game_over": board.outcome() is not None,
            "termination": board.outcome().termination.name if board.outcome() is not None else None,
                }
    
    else:
        raise ValueError("La position décrite est invalide.")
