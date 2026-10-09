"""Quota Groq et réutilisation des succès, sans aucun appel réseau."""
import unittest
from unittest.mock import patch
import httpx
from openai import RateLimitError
from pymongo.errors import ServerSelectionTimeoutError
from backend.app.services import explanation_cache_repository as repository
from backend.app.services import generation_service as service
from backend.app.schemas import ExplanationResponse


class GenerationResilienceTests(unittest.TestCase):
    def setUp(self):
        service._explanation_cache.clear()
        service._retry_after = 0
        self.addCleanup(service._explanation_cache.clear)
        self.addCleanup(setattr, service, '_retry_after', 0)
        # MongoDB simulé par un dictionnaire : aucun test ne contacte de base.
        self.stored = {}
        load = patch.object(repository, 'load_explanation', side_effect=self.stored.get)
        store = patch.object(repository, 'store_explanation',
                             side_effect=lambda key, explanation, model: self.stored.__setitem__(key, explanation))
        self.load, self.store = load.start(), store.start()
        self.addCleanup(load.stop)
        self.addCleanup(store.stop)
        self.claimed = ExplanationResponse(claims=[{
            'claim': 'Les Noirs contestent le centre.', 'source_id': 1,
            'evidence': 'Les Noirs attaquent le centre.',
        }], limitation='none')
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

    def test_cache_distinguishes_positions_and_forwards_context(self):
        with patch.object(service, '_generate_explanation', return_value=self.result) as generate:
            first = {"fen": "position A", "trait": "Blancs"}
            second = {"fen": "position B", "trait": "Noirs"}
            service.generate_explanation('plans', self.documents, first)
            service.generate_explanation('plans', self.documents, first)
            generate.assert_called_once_with('plans', self.documents, first)
            service.generate_explanation('plans', self.documents, second)
            self.assertEqual(generate.call_count, 2)
            generate.assert_called_with('plans', self.documents, second)

    def test_request_includes_position_and_documents(self):
        from types import SimpleNamespace
        document = {"title": "Défense française", "text": "Les Noirs attaquent le centre.", "source_url": "https://example.org"}
        output = '{"claims":[{"claim":"Contestez le centre.","source_id":1,"evidence":"Les Noirs attaquent le centre."}],"limitation":"none"}'
        with patch.object(service, 'OpenAI') as client, patch.object(service, 'load_dotenv'), patch.dict(service.os.environ, {"GROQ_API_KEY": "test"}):
            create = client.return_value.__enter__.return_value.chat.completions.create
            create.return_value = SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop', message=SimpleNamespace(content=output))])
            result = service._generate_explanation('plans', [document], {"trait": "Noirs", "fen": "position-test"})
            prompt = create.call_args.kwargs['messages'][1]['content']
            self.assertIn('position-test', prompt)
            self.assertIn('Les Noirs attaquent le centre.', prompt)
            self.assertEqual(len(result.claims), 1)

    def test_citations_allow_typography_but_reject_changed_words(self):
        documents = [{"text": "Les Noirs manquent souvent d’espace."}]
        response = ExplanationResponse(claims=[
            {"claim": "Espace limité.", "source_id": 1, "evidence": "Les Noirs manquent souvent d'espace."},
            {"claim": "Toujours limité.", "source_id": 1, "evidence": "Les Noirs manquent toujours d'espace."},
        ], limitation='none')
        checked = service.verifier_citations(response, documents)
        self.assertEqual([item.claim for item in checked.claims], ["Espace limité."])
        self.assertEqual(checked.limitation, 'insufficient_context')

    def test_memory_cache_does_not_expire(self):
        with patch.object(service.time, 'monotonic', return_value=10) as clock, patch.object(service, '_generate_explanation', return_value=self.result) as generate:
            service.generate_explanation('plans', self.documents)
            clock.return_value = 10 + 365 * 24 * 3600
            service.generate_explanation('plans', self.documents)
            generate.assert_called_once()

    def test_cache_ignores_milvus_score_but_not_document_order(self):
        first = {'id': 'a', 'text': 'Les Noirs attaquent le centre.', 'score': 0.7263}
        second = {'id': 'b', 'text': 'Autre extrait', 'score': 0.7257}
        with patch.object(service, '_generate_explanation', return_value=self.result) as generate:
            service.generate_explanation('plans', [first, second])
            service.generate_explanation('plans', [{**first, 'score': 0.7276}, {**second, 'score': 0.7263}])
            generate.assert_called_once()
            service.generate_explanation('plans', [second, first])
            self.assertEqual(generate.call_count, 2)

    def test_success_is_stored_then_reused_after_restart(self):
        with patch.object(service, '_generate_explanation', return_value=self.claimed) as generate:
            service.generate_explanation('plans', self.documents)
            self.store.assert_called_once()
            service._explanation_cache.clear()  # Simule une mise en veille de Render.
            reused = service.generate_explanation('plans', self.documents)
            generate.assert_called_once()
            self.assertEqual(reused, self.claimed)

    def test_stored_explanation_is_served_during_groq_cooldown(self):
        key = service.cache_key('plans', self.documents)
        self.stored[key] = self.claimed.model_dump()
        service._retry_after = float('inf')
        with patch.object(service, '_generate_explanation') as generate:
            self.assertEqual(service.generate_explanation('plans', self.documents), self.claimed)
            generate.assert_not_called()

    def test_explanation_without_claims_is_not_stored(self):
        with patch.object(service, '_generate_explanation', return_value=self.result):
            service.generate_explanation('plans', self.documents)
        self.store.assert_not_called()

    def test_invalid_stored_explanation_is_regenerated(self):
        self.stored[service.cache_key('plans', self.documents)] = {'claims': 'corrompu'}
        with patch.object(service, '_generate_explanation', return_value=self.claimed) as generate:
            self.assertEqual(service.generate_explanation('plans', self.documents), self.claimed)
            generate.assert_called_once()

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


class ExplanationCacheRepositoryTests(unittest.TestCase):
    """Le cache MongoDB est facultatif : une panne ne doit jamais bloquer l'analyse."""

    def setUp(self):
        repository._unavailable_until = 0.0
        self.addCleanup(setattr, repository, '_unavailable_until', 0.0)

    def test_disabled_without_mongodb_history(self):
        with patch.dict(repository.os.environ, {'HISTORY_BACKEND': 'hf_dataset'}), patch.object(repository, 'MongoClient') as client:
            self.assertIsNone(repository.load_explanation('cle'))
            repository.store_explanation('cle', {}, 'modele')
            client.assert_not_called()

    def test_mongodb_failure_is_ignored_then_paused(self):
        with patch.dict(repository.os.environ, {'HISTORY_BACKEND': 'mongodb'}), patch.object(repository, '_client') as client:
            collection = client.__getitem__.return_value.__getitem__.return_value
            collection.find_one.side_effect = ServerSelectionTimeoutError('secret')
            self.assertIsNone(repository.load_explanation('cle'))
            repository.store_explanation('cle', {}, 'modele')
            collection.replace_one.assert_not_called()
            collection.find_one.assert_called_once()
