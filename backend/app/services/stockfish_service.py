import chess
import chess.engine


class StockfishError(Exception):
    """Le moteur n'a pas pu produire de résultat exploitable."""


def analyse_position(fen):
    """Analyse une FEN pendant une seconde avec le binaire /usr/games/stockfish.

    Renvoie le premier coup UCI/SAN et le score du point de vue des Blancs :
    score_cp en centipions, ou mate pour une annonce de mat. L'appelant valide
    la position avant ce calcul. Le moteur est fermé même si l'analyse échoue.
    """
    board = chess.Board(fen)
    try:
        with chess.engine.SimpleEngine.popen_uci(
            "/usr/games/stockfish", timeout=10.0,
        ) as engine:
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
    except TimeoutError:
        raise StockfishError("Le moteur Stockfish ne répond pas à temps.") from None
    except (OSError, chess.engine.EngineError):
        raise StockfishError("Le moteur Stockfish est indisponible.") from None
