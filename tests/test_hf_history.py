"""Persistance distante : fichiers distincts, confidentialité et erreurs publiques."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.app import main
from backend.app.services import hf_history_repository as history


class HFHistoryTests(unittest.TestCase):
    def setUp(self):
        self.api = MagicMock()
        self.api.repo_info.return_value.private = True
        self.connection = patch.object(history, "connection", return_value=(self.api, "test/history"))
        self.connection.start()
        self.addCleanup(self.connection.stop)

    def test_saves_distinct_remote_files_and_reads_without_local_state(self):
        with tempfile.TemporaryDirectory() as directory:
            stored = {}

            def upload(**kwargs):
                filename = Path(kwargs["path_in_repo"]).name
                path = Path(directory, filename)
                path.write_bytes(kwargs["path_or_fileobj"])
                stored[kwargs["path_in_repo"]] = str(path)

            self.api.upload_file.side_effect = upload
            self.api.hf_hub_download.side_effect = lambda **kw: stored[kw["filename"]]
            self.api.list_repo_files.side_effect = lambda **kw: list(stored)
            first = history.save_analysis("fen-first", {"game_over": True})
            second = history.save_analysis("fen-second", {"game_over": False})
            self.assertNotEqual(first, second)
            self.assertEqual(history.get_analysis(first)["fen"], "fen-first")
            summaries = history.list_analyses(limit=1)
            self.assertEqual(summaries[0]["_id"], second)
            self.assertNotIn("result", summaries[0])
            self.assertIn("+00:00", summaries[0]["created_at"])

    def test_refuses_public_dataset(self):
        self.api.repo_info.return_value.private = False
        with self.assertRaises(history.HistoryError):
            history.save_analysis("fen", {})
        self.api.upload_file.assert_not_called()

    def test_failed_upload_is_not_reported_as_saved(self):
        self.api.upload_file.side_effect = RuntimeError("secret upstream detail")
        with self.assertRaises(history.HistoryError) as error:
            history.save_analysis("fen", {})
        self.assertNotIn("secret", str(error.exception))

    def test_invalid_id_never_contacts_hub(self):
        with self.assertRaises(ValueError):
            history.get_analysis("../../.env")
        self.api.hf_hub_download.assert_not_called()

    def test_http_history_error_is_a_controlled_503(self):
        with patch.object(main, "list_analyses", side_effect=history.HistoryError("Historique indisponible.")):
            with TestClient(main.app) as client:
                response = client.get("/api/v1/analyses")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Historique indisponible.")
