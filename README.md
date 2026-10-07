# Mon coach d’échecs — Projet 13

Démonstration pédagogique : jouer ou importer une position, consulter les coups
Lichess ou Stockfish, une explication sourcée et des vidéos, puis sauvegarder l’analyse.
Interface Angular, API FastAPI, orchestration LangGraph, recherche Milvus et historique MongoDB.

[Essayer l’application](https://chess-coach-g68p.onrender.com/) · [Comprendre le fonctionnement](https://chess-coach-g68p.onrender.com/projet.html)

## Première installation depuis un clone

**Prérequis :** Git, Docker avec Compose et des clés Lichess, YouTube Data API,
Groq et Hugging Face. Le token HF doit autoriser les Inference Providers, avec
un quota ou des crédits disponibles pour DeepInfra. Python et Node ne sont pas
nécessaires sur la machine pour ce lancement Docker.

```bash
git clone https://github.com/rayakevin/OCR_PROJET_13.git
cd OCR_PROJET_13
```

Créer un fichier `.env` à la racine, avec ses propres clés (ce fichier est ignoré par Git) :

```dotenv
COMPOSE_PROJECT_NAME=projet_13
APP_PORT=8080
LICHESS_API_TOKEN=remplacer
YOUTUBE_API_KEY=remplacer
GROQ_API_KEY=remplacer
HF_TOKEN=remplacer
```

Puis, depuis la racine du dépôt :

```bash
docker compose build api frontend
docker compose run --rm corpus-init
docker compose up -d api frontend
```

Attendre la réussite de l’import avant la dernière commande : il démarre Milvus
et charge les **339 passages prévectorisés** fournis, sans recalculer les embeddings.
Les ports 4200 et 8080 doivent être libres.

- **Interface :** [http://127.0.0.1:4200](http://127.0.0.1:4200)
- **Documentation API :** [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

## Utilisation et relance

Jouer un coup ou importer une FEN déclenche l’analyse. « Sauvegarder la position »
enregistre le résultat affiché ; l’historique permet de le recharger sans recalcul.

```bash
# Relancer après un arrêt, sans réimporter le corpus.
docker compose up -d standalone mongodb api frontend

# Vérifier les services et consulter les logs.
docker compose ps
docker compose logs -f api

# Arrêter les services en conservant les données.
docker compose down
```

Attendre que Milvus (`standalone`) soit sain avant d’analyser. Ne pas ajouter
`-v` à la commande d’arrêt si l’on souhaite conserver le volume MongoDB.

## À savoir

- Même en local, Lichess, YouTube, Groq et les embeddings utilisent des services
  distants : connexion Internet, clés et quotas restent nécessaires.
- L’historique de cette démonstration est **partagé, sans comptes utilisateurs**.
  Sur Render, le premier accès après une période d’inactivité peut être lent.
- Les explications sont pédagogiques : leur pertinence n’est pas garantie.
  Une indisponibilité Groq conserve les autres résultats ; certaines autres pannes
  peuvent interrompre l’analyse. Avant une démo, vérifier analyse, sauvegarde et relecture.

## Tests et documentation complémentaire

Pour les tests hors Docker : Python 3.12 avec uv, et Node.js 24 avec npm.
Les tests automatisés utilisent des fournisseurs simulés.

```bash
uv sync --locked
uv run python -m unittest discover -s tests -v
npm --prefix frontend ci
npm --prefix frontend run test:behavior
npm --prefix frontend run build
```

[Déploiement Render](deploy/README.md) · [Corpus fourni](resources/corpus/README.md) · [Étude vidéo / MCP](reports/etude-faisabilite-video-mcp.md)
