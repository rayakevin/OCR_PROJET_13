"""Cycle de vie du moteur simulé : aucun binaire Stockfish n'est lancé."""

import unittest
from unittest.mock import patch

import chess
import chess.engine

from backend.app.services.stockfish_service import StockfishError, analyse_position


class StockfishTests(unittest.TestCase):
    def test_missing_binary_is_sanitized(self):
        with patch.object(chess.engine.SimpleEngine, "popen_uci", side_effect=FileNotFoundError("secret")):
            with self.assertRaises(StockfishError) as caught:
                analyse_position(chess.STARTING_FEN)
        self.assertNotIn("secret", str(caught.exception))

    def test_engine_is_closed_after_analysis_failure(self):
        with patch.object(chess.engine.SimpleEngine, "popen_uci") as launch:
            context = launch.return_value
            context.__enter__.return_value.analyse.side_effect = chess.engine.EngineTerminatedError("secret")
            with self.assertRaises(StockfishError):
                analyse_position(chess.STARTING_FEN)
            context.__exit__.assert_called_once()

    def test_score_and_move_are_serializable(self):
        with patch.object(chess.engine.SimpleEngine, "popen_uci") as launch:
            launch.return_value.__enter__.return_value.analyse.return_value = {
                "pv": [chess.Move.from_uci("e2e4")],
                "score": chess.engine.PovScore(chess.engine.Cp(32), chess.WHITE),
            }
            result = analyse_position(chess.STARTING_FEN)
            self.assertEqual(result, {"uci": "e2e4", "san": "e4", "score_cp": 32, "mate": None})
            launch.return_value.__exit__.assert_called_once()
