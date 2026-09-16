import chess

def inspect_position(fen):
    
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