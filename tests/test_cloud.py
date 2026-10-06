"""Configuration distante et service de fichiers, sans contacter les fournisseurs."""

import importlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.services import milvus_connection


class MilvusConnectionTests(unittest.TestCase):
    def test_cloud_token_is_passed_to_sdk(self):
        with patch.dict(os.environ, {
            "MILVUS_URI": "https://cluster.example", "MILVUS_TOKEN": "test-only-token",
        }, clear=True), patch.object(milvus_connection, "load_dotenv"), patch.object(
            milvus_connection, "MilvusClient"
        ) as constructor:
            milvus_connection.create_milvus_client()
            constructor.assert_called_once_with(
                uri="https://cluster.example", token="test-only-token", timeout=15,
            )

    def test_local_connection_does_not_require_token(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(
            milvus_connection, "load_dotenv"
        ), patch.object(milvus_connection, "MilvusClient") as constructor:
            milvus_connection.create_milvus_client()
            constructor.assert_called_once_with(uri="http://127.0.0.1:19530", timeout=15)


class CloudAppTests(unittest.TestCase):
    def test_api_and_static_files_share_origin_without_masking_api_errors(self):
        from backend.app.main import app

        original_routes = app.router.routes[:]
        try:
            with tempfile.TemporaryDirectory() as directory:
                Path(directory, "index.html").write_text("<h1>Chess Coach</h1>")
                Path(directory, "main.js").write_text("console.log('ready');")
                with patch.dict(os.environ, {"STATIC_DIR": directory}):
                    importlib.import_module("backend.app.cloud")
                    with TestClient(app) as client:
                        self.assertIn("Chess Coach", client.get("/").text)
                        self.assertEqual(client.get("/main.js").status_code, 200)
                        self.assertEqual(client.get("/api/v1/healthcheck").status_code, 200)
                        self.assertEqual(client.get("/api/v1/inconnue").status_code, 404)
                        self.assertEqual(client.get("/.env").status_code, 404)
        finally:
            app.router.routes[:] = original_routes
