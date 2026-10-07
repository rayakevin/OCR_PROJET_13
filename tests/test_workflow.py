"""Tests hors réseau du vrai graphe et des routes HTTP, sans Docker ni clés API."""

import socket
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from pymilvus.exceptions import MilvusException
from pymongo.errors import ConnectionFailure
from openai import APITimeoutError

from backend.app import main
from backend.app.graphs import chess_graph
from backend.app.schemas import ExplanationResponse
from backend.app.services.embedding_service import EmbeddingError
from backend.app.services.youtube_service import YouTubeError
from backend.app.services.stockfish_service import StockfishError


FRENCH = "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3"
FINISHED = "8/8/8/8/8/2k5/8/K7 w - - 0 1"
MOVE = {
    "uci": "b1c3", "san": "Nc3", "opening": "French Defense",
    "games_count": 10, "frequency": 0.5,
}
DOCUMENT = {
    "id": "french_1", "title": "Défense française",
    "section_path": ["Introduction"], "text": "Les Noirs attaquent le centre.",
    "source_url": "https://fr.wikipedia.org/wiki/Défense_française", "score": 0.7,
}


class WorkflowTests(unittest.TestCase):
    """Conserve le routage LangGraph réel ; remplace ses dépendances externes."""

    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        # Un oubli de simulation doit échouer, jamais contacter un fournisseur.
        stack.enter_context(patch.object(
            socket.socket, "connect", side_effect=AssertionError("Réseau interdit")
        ))
        self.services = {}
        for name in (
            "get_opening_moves", "analyse_position", "search_documents",
            "search_videos", "generate_explanation",
        ):
            self.services[name] = stack.enter_context(patch.object(chess_graph, name))
        self.services["get_opening_moves"].return_value = (
            [MOVE], [], {"eco": "C00", "name": "French Defense"}
        )
        self.services["analyse_position"].return_value = {
            "uci": "b1c3", "san": "Nc3", "score_cp": 24, "mate": None,
        }
        self.services["search_documents"].return_value = [DOCUMENT]
        self.services["search_videos"].return_value = []
        self.services["generate_explanation"].return_value = ExplanationResponse(
            claims=[{
                "claim": "Les Noirs attaquent le centre.", "source_id": 1,
                "evidence": DOCUMENT["text"],
            }], limitation="none",
        )
        self.save = stack.enter_context(patch.object(main, "save_analysis"))
        self.save.return_value = "0123456789abcdef01234567"
        self.client = stack.enter_context(TestClient(main.app))

    def analyse(self, fen=FRENCH):
        return self.client.post("/api/v1/analyses", json={"fen": fen})

    def test_preview_does_not_save(self):
        response = self.client.post("/api/v1/analyses/preview", json={"fen": FRENCH})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["opening"]["name"], "French Defense")
        self.save.assert_not_called()

    def test_explicit_save_preserves_result_without_recomputing(self):
        preview = self.client.post("/api/v1/analyses/preview", json={"fen": FRENCH}).json()
        for service in self.services.values():
            service.reset_mock()
        response = self.client.post("/api/v1/analyses/save", json=preview)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["result"], preview)
        self.save.assert_called_once_with(fen=FRENCH, result=preview)
        for service in self.services.values():
            service.assert_not_called()

    def test_explicit_save_rejects_invalid_position(self):
        preview = self.client.post("/api/v1/analyses/preview", json={"fen": FINISHED}).json()
        preview["fen"] = "invalid"
        response = self.client.post("/api/v1/analyses/save", json=preview)
        self.assertEqual(response.status_code, 400)
        self.save.assert_not_called()

    def test_invalid_fen_stops_before_tools_and_storage(self):
        for fen in ("bonjour", "8/8/8/8/8/8/8/8 w - - 0 1"):
            with self.subTest(fen=fen):
                self.assertEqual(self.analyse(fen).status_code, 400)
        for service in self.services.values():
            service.assert_not_called()
        self.save.assert_not_called()

    def test_finished_game_is_saved_without_external_calls(self):
        response = self.analyse(FINISHED)
        self.assertEqual(response.status_code, 201)
        result = response.json()["result"]
        self.assertTrue(result["game_over"])
        self.assertEqual(result["termination"], "INSUFFICIENT_MATERIAL")
        self.assertIsNone(result["source"])
        self.assertEqual(result["moves"], [])
        for service in self.services.values():
            service.assert_not_called()
        self.save.assert_called_once_with(fen=FINISHED, result=result)

    def test_known_opening_enriches_and_saves_result(self):
        response = self.analyse()
        self.assertEqual(response.status_code, 201)
        result = response.json()["result"]
        self.assertEqual(result["source"], "lichess")
        self.assertEqual(result["moves"], [MOVE])
        self.assertEqual(result["documents"], [DOCUMENT])
        self.assertTrue(result["explanation"]["claims"])
        self.services["search_documents"].assert_called_once_with(
            question="Quels sont les principes et les plans de Défense française ?",
            opening_title="Défense française", limit=3,
        )
        self.services["search_videos"].assert_called_once_with(
            opening="Défense française", limit=2,
        )
        self.services["analyse_position"].assert_not_called()
        self.save.assert_called_once_with(fen=FRENCH, result=result)

    def test_empty_catalogue_uses_stockfish_without_resources(self):
        self.services["get_opening_moves"].return_value = ([], [], None)
        response = self.analyse()
        self.assertEqual(response.status_code, 201)
        result = response.json()["result"]
        self.assertEqual(result["source"], "stockfish")
        self.assertEqual(result["moves"][0]["score_cp"], 24)
        self.services["analyse_position"].assert_called_once_with(FRENCH)
        for name in ("search_documents", "search_videos", "generate_explanation"):
            self.services[name].assert_not_called()
        self.assertIsNone(result["explanation"])

    def test_unmapped_opening_skips_resources(self):
        self.services["get_opening_moves"].return_value = ([MOVE], [], None)
        self.assertEqual(self.analyse().status_code, 201)
        for name in ("search_documents", "search_videos", "generate_explanation"):
            self.services[name].assert_not_called()

    def test_empty_retrieval_skips_generation(self):
        self.services["search_documents"].return_value = []
        self.assertEqual(self.analyse().status_code, 201)
        self.services["generate_explanation"].assert_not_called()

    def test_lichess_timeout_is_not_an_empty_catalogue(self):
        self.services["get_opening_moves"].side_effect = httpx.ReadTimeout("secret")
        response = self.analyse()
        self.assertEqual(response.status_code, 504)
        self.assertNotIn("secret", response.text)
        self.services["analyse_position"].assert_not_called()
        self.save.assert_not_called()

    def test_lichess_network_error(self):
        self.services["get_opening_moves"].side_effect = httpx.ConnectError("secret")
        self.assertEqual(self.analyse().status_code, 502)
        self.save.assert_not_called()

    def test_stockfish_failure_prevents_save(self):
        self.services["get_opening_moves"].return_value = ([], [], None)
        self.services["analyse_position"].side_effect = StockfishError("Moteur indisponible")
        self.assertEqual(self.analyse().status_code, 503)
        self.save.assert_not_called()

    def test_generation_unavailable_keeps_moves_documents_and_warning(self):
        from backend.app.services.generation_service import GenerationUnavailable
        self.services["generate_explanation"].side_effect = GenerationUnavailable("Limite de débit Groq")
        response = self.client.post("/api/v1/analyses/preview", json={"fen": FRENCH})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["moves"][0]["uci"], MOVE["uci"])
        self.assertEqual(result["documents"][0]["id"], DOCUMENT["id"])
        self.assertIsNone(result["explanation"])
        self.assertEqual(result["warnings"], ["Limite de débit Groq"])
        self.save.assert_not_called()

    def test_generation_timeout_prevents_save(self):
        self.services["generate_explanation"].side_effect = APITimeoutError(
            request=httpx.Request("POST", "https://example.invalid")
        )
        self.assertEqual(self.analyse().status_code, 504)
        self.save.assert_not_called()

    def test_invalid_tool_result_is_not_saved(self):
        self.services["get_opening_moves"].return_value = ([{"uci": "b1c3"}], [], None)
        self.assertEqual(self.analyse().status_code, 502)
        self.save.assert_not_called()

    def test_embedding_error_keeps_status_and_prevents_save(self):
        self.services["search_documents"].side_effect = EmbeddingError("Quota épuisé", 503)
        response = self.analyse()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Quota épuisé")
        self.services["search_videos"].assert_not_called()
        self.save.assert_not_called()

    def test_milvus_failure_returns_controlled_503(self):
        self.services["search_documents"].side_effect = MilvusException(message="secret")
        response = self.analyse()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.text)
        self.save.assert_not_called()

    def test_youtube_timeout_returns_controlled_504(self):
        self.services["search_videos"].side_effect = YouTubeError("YouTube ne répond pas à temps.", 504)
        response = self.analyse()
        self.assertEqual(response.status_code, 504)
        self.assertNotIn("secret", response.text)
        self.save.assert_not_called()

    def test_mongodb_failure_does_not_report_success(self):
        self.save.side_effect = ConnectionFailure("secret")
        response = self.analyse(FINISHED)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.text)

    def test_get_analysis_calculation_does_not_save(self):
        response = self.client.get("/api/v1/opening-moves", params={"fen": FRENCH})
        self.assertEqual(response.status_code, 200)
        self.save.assert_not_called()

    def test_missing_fen_is_rejected(self):
        self.assertEqual(self.client.post("/api/v1/analyses", json={}).status_code, 422)
        self.save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
