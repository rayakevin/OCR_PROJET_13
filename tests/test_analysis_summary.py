"""Les résumés restent lisibles sans exposer les contenus détaillés."""
import unittest
from bson import ObjectId
from backend.app.services.analysis_repository import analysis_summary


class AnalysisSummaryTests(unittest.TestCase):
    def test_summary_uses_saved_opening_and_omits_full_result(self):
        document = {"_id": ObjectId(), "fen": "test", "created_at": "date",
                    "result": {"opening": {"name": "Défense française"},
                               "source": "lichess", "game_over": False,
                               "documents": [{"text": "long contenu"}]}}
        summary = analysis_summary(document)
        self.assertEqual(summary["opening_name"], "Défense française")
        self.assertEqual(summary["_id"], str(document["_id"]))
        self.assertNotIn("result", summary)
        self.assertNotIn("documents", summary)

    def test_old_document_without_metadata_remains_readable(self):
        summary = analysis_summary({"_id": ObjectId(), "fen": "test", "created_at": "date"})
        self.assertIsNone(summary["opening_name"])
        self.assertIsNone(summary["game_over"])
