"""Validation du contexte de coups envoyé à Lichess."""
import unittest
from unittest.mock import Mock, patch

import chess

from backend.app.services.lichess_service import explorer_params, get_opening_moves


class LichessContextTests(unittest.TestCase):
    def setUp(self):
        self.moves = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "a2a3"]
        self.board = chess.Board()
        for move in self.moves:
            self.board.push_uci(move)

    def test_fen_only_stays_supported(self):
        params = explorer_params(self.board.fen())
        self.assertEqual(params["fen"], self.board.fen())
        self.assertNotIn("play", params)

    def test_request_preserves_opening_context(self):
        response = Mock()
        response.json.return_value = {
            "moves": [], "topGames": [], "white": 0, "draws": 0, "black": 0,
            "opening": {"eco": "C50", "name": "Italian Game: Giuoco Piano"},
        }
        with patch("backend.app.services.lichess_service.httpx.get", return_value=response) as get:
            _, _, opening = get_opening_moves(self.board.fen(), chess.STARTING_FEN, self.moves)
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["fen"], chess.STARTING_FEN)
        self.assertEqual(params["play"], ",".join(self.moves))
        self.assertEqual(opening["eco"], "C50")

    def test_mismatched_or_illegal_history_is_rejected(self):
        for base, moves in [(None, self.moves), (chess.STARTING_FEN, ["e2e5"]),
                            (chess.STARTING_FEN, ["e2e4"])]:
            with self.subTest(moves=moves), self.assertRaises(ValueError):
                explorer_params(self.board.fen(), base, moves)
