"""Erreurs du transport YouTube : aucun appel réseau réel."""

import unittest
from unittest.mock import patch

from backend.app.services import youtube_service


class YouTubeTests(unittest.TestCase):
    def test_transport_failure_is_sanitized_and_closed(self):
        for error, status in ((TimeoutError("secret"), 504), (OSError("secret"), 502)):
            with self.subTest(error=type(error).__name__), \
                    patch.object(youtube_service, "load_dotenv"), \
                    patch.dict("os.environ", {"YOUTUBE_API_KEY": "fake-test-key"}), \
                    patch.object(youtube_service.httplib2, "Http") as transport, \
                    patch.object(youtube_service, "build") as build:
                build.return_value.search.return_value.list.return_value.execute.side_effect = error
                with self.assertRaises(youtube_service.YouTubeError) as caught:
                    youtube_service.search_videos("Défense française")
                self.assertEqual(caught.exception.status_code, status)
                self.assertNotIn("secret", str(caught.exception))
                transport.assert_called_once_with(timeout=15)
                transport.return_value.close.assert_called_once()

    def test_invalid_parameters_never_open_transport(self):
        with patch.object(youtube_service, "build") as build:
            for opening, limit in ((" ", 3), ("Sicilienne", 0), ("Sicilienne", 6)):
                with self.subTest(opening=opening, limit=limit):
                    with self.assertRaises(ValueError):
                        youtube_service.search_videos(opening, limit)
            build.assert_not_called()
