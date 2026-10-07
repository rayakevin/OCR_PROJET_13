"""Quota Groq et réutilisation des succès, sans aucun appel réseau."""
import unittest
from unittest.mock import patch
import httpx
from openai import RateLimitError
from backend.app.services import generation_service as service
from backend.app.schemas import ExplanationResponse


class GenerationResilienceTests(unittest.TestCase):
    def setUp(self):
        service._explanation_cache.clear()
        service._retry_after = 0
        self.addCleanup(service._explanation_cache.clear)
        self.addCleanup(setattr, service, '_retry_after', 0)
        self.documents = [{'text': 'Les Noirs attaquent le centre.'}]
        self.result = ExplanationResponse(claims=[], limitation='insufficient_context')

    def test_cache_reuses_success_but_not_changed_documents(self):
        with patch.object(service, '_generate_explanation', return_value=self.result) as generate:
            first = service.generate_explanation('plans', self.documents)
            first.limitation = 'none'
            second = service.generate_explanation('plans', self.documents)
            self.assertEqual(second.limitation, 'insufficient_context')
            generate.assert_called_once()
            service.generate_explanation('plans', [{'text': 'Autre extrait'}])
            self.assertEqual(generate.call_count, 2)

    def test_cache_expires(self):
        with patch.object(service.time, 'monotonic', return_value=10) as clock, patch.object(service, '_generate_explanation', return_value=self.result) as generate:
            service.generate_explanation('plans', self.documents)
            clock.return_value = 10 + service._CACHE_TTL + 1
            service.generate_explanation('plans', self.documents)
            self.assertEqual(generate.call_count, 2)

    def test_rate_limit_respects_retry_after_then_recovers(self):
        response = httpx.Response(429, headers={'retry-after': '18'}, request=httpx.Request('POST', 'https://example.invalid'))
        error = RateLimitError('secret fournisseur', response=response, body=None)
        with patch.object(service.time, 'monotonic', return_value=100) as clock, patch.object(service, '_generate_explanation', side_effect=[error, self.result]) as generate:
            with self.assertRaises(service.GenerationUnavailable) as raised:
                service.generate_explanation('plans', self.documents)
            self.assertNotIn('secret', str(raised.exception))
            clock.return_value = 117
            with self.assertRaises(service.GenerationUnavailable):
                service.generate_explanation('plans', self.documents)
            generate.assert_called_once()
            clock.return_value = 119
            service.generate_explanation('plans', self.documents)
            self.assertEqual(generate.call_count, 2)
