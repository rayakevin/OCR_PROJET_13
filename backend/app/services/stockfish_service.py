import chess
import chess.engine

def analyse_position(fen):
    board = chess.Board(fen)
    engine = chess.engine.SimpleEngine.popen_uci("/usr/games/stockfish")

    try:
        info = engine.analyse(board, chess.engine.Limit(time=1.0))
        variante = info.get("pv", [])
        premier_coup = variante[0] if variante else None
        score_blancs = info["score"].white()
        return {
            "uci": premier_coup.uci() if premier_coup else None,
            "san": board.san(premier_coup) if premier_coup else None,
            "score_cp": score_blancs.score(),
            "mate": score_blancs.mate(),
        }
    finally:
        engine.quit()