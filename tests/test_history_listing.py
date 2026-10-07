"""L'historique complet reste accessible au-delà des anciennes limites."""
import unittest
from unittest.mock import MagicMock, patch
from bson import ObjectId
from fastapi.testclient import TestClient
from backend.app import main
from backend.app.services import analysis_repository as repository


class HistoryListingTests(unittest.TestCase):
    def test_default_http_listing_does_not_truncate_sixty_saves(self):
        summaries = [{"_id": str(ObjectId()), "fen": "test", "created_at": "date"}
                     for _ in range(60)]
        with patch.object(main, "list_analyses", return_value=summaries) as listing:
            response = TestClient(main.app).get('/api/v1/analyses')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 60)
        listing.assert_called_once_with(limit=None)

    def test_optional_limit_is_preserved_and_invalid_limits_rejected(self):
        with patch.object(main, 'list_analyses', return_value=[]) as listing:
            client = TestClient(main.app)
            self.assertEqual(client.get('/api/v1/analyses?limit=5').status_code, 200)
            listing.assert_called_once_with(limit=5)
            self.assertEqual(client.get('/api/v1/analyses?limit=0').status_code, 422)

    def test_mongo_returns_all_summaries_without_full_results(self):
        collection = MagicMock()
        cursor = collection.find.return_value.sort.return_value
        docs = [{'_id': ObjectId(), 'fen': 'test', 'created_at': 'date'} for _ in range(60)]
        cursor.limit.side_effect = lambda n: docs if n == 0 else docs[:n]
        with patch.object(repository, 'MongoClient') as connection:
            connection.return_value.__enter__.return_value.__getitem__.return_value.__getitem__.return_value = collection
            self.assertEqual(len(repository.list_analyses()), 60)
            self.assertEqual(len(repository.list_analyses(5)), 5)
        projection = collection.find.call_args.args[1]
        self.assertNotIn('result', projection)
