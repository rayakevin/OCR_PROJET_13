# Mise en ligne sur Render

## Architecture

- Render : Angular + FastAPI + Stockfish dans `Dockerfile.cloud`.
- MongoDB Atlas : historique persistant, base `chess_coach`.
- Zilliz : collection `chess_openings_fr_v2`, 339 passages et vecteurs existants.
- Hugging Face Inference Providers : embeddings distants des requêtes.

Le disque Render ne conserve aucune donnée métier. L'historique de démonstration
est commun aux visiteurs : ne pas y importer l'historique personnel local.
Docker Compose reste disponible pour l'exécution locale.

## 1. Vérifier les bases

Le 6 octobre 2026 : lecture MongoDB validée et 339 passages importés puis comptés
sur Zilliz depuis le poste local. Cela ne valide pas encore les accès depuis Render.

Pour refaire les contrôles avec les valeurs distantes dans `.env.cloud` :

```bash
uv run --env-file .env.cloud python -m backend.app.commands.check_cloud
```

`.env.cloud.example` donne les noms nécessaires. Si les valeurs sont dans `.env`,
utiliser `--env-file .env`. Ne jamais versionner ces fichiers de secrets.
L'import est déjà réalisé ; il ne faut pas recalculer les embeddings.

## 2. Publier le code et créer le service

Après commit et push des fichiers de déploiement sur GitHub :

1. Se connecter à Render, puis choisir **New → Blueprint**.
2. Autoriser le dépôt du projet et sélectionner la branche contenant `render.yaml`.
3. Vérifier le plan **Free**, la région **Frankfurt** et le Dockerfile proposé.
4. Renseigner les variables demandées depuis la configuration locale :
   `MONGODB_URI`, `MILVUS_URI`, `MILVUS_TOKEN`, `HF_TOKEN`, `GROQ_API_KEY`,
   `YOUTUBE_API_KEY`, `LICHESS_API_TOKEN`.
5. Créer le service. `HISTORY_BACKEND=mongodb` est déjà défini par le Blueprint.

Alternative manuelle : **New → Web Service**, runtime Docker, racine vide,
Dockerfile `./Dockerfile.cloud`, contexte `.`, plan Free, healthcheck
`/api/v1/healthcheck`. Ne pas définir de commande de démarrage personnalisée :
l'image utilise le port fourni par Render dans `PORT`.

Le Blueprint désactive les déploiements automatiques : pour publier une mise à
jour, sélectionner **Manual Deploy → Deploy latest commit**.
Ne pas recopier des adresses locales MongoDB/Milvus dans Render.

## 3. Autoriser Render dans Atlas

Dans la fiche Render, ouvrir **Connect → Outbound** et relever toutes les plages
IP sortantes affichées. Les ajouter dans **Atlas → Network Access → IP Access List**.
Conserver l'autorisation du poste local pour les contrôles ; éviter une ouverture
à toutes les adresses. Les plages sont partagées : l'authentification MongoDB reste
nécessaire. Relancer un contrôle applicatif après l'ajout.

## 4. Vérifier l'URL publique

1. Charger l'échiquier, déplacer une pièce et vérifier la FEN.
2. Analyser une partie terminée, sauvegarder et relire depuis l'historique.
3. Analyser la Française : coups, documents, explication et vidéos.
4. Tester une position hors catalogue pour vérifier Stockfish.
5. Vérifier qu'une FEN invalide est rejetée.
6. Redémarrer le service puis relire l'historique et refaire une recherche.

Le healthcheck vérifie uniquement le processus HTTP, pas la disponibilité des bases.
La publication n'est validée qu'après cette recette sur l'URL publique.

## Limites de l'offre et variante HF

Render Free se met en veille après inactivité : prévoir un délai au premier accès.
Les quotas Render, Atlas, Zilliz et les appels aux modèles s'appliquent séparément.
Le plan Free ne garantit pas les performances de Stockfish : mesurer les temps de
réponse et la mémoire lors de la recette avant de conclure.

Les fichiers `deploy/huggingface/` et `prepare_space` décrivent une variante
antérieure, non utilisée ici. Ne pas sélectionner `hf_dataset` sur Render.

## Références

- [Configuration Blueprint](https://render.com/docs/blueprint-spec)
- [Docker sur Render](https://render.com/docs/docker)
- [Limites de Render Free](https://render.com/docs/free)
- [Adresses sortantes](https://render.com/docs/outbound-ip-addresses)
- [Zilliz Free](https://docs.zilliz.com/docs/free-trials)
