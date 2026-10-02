# Projet 13 — Agent d'apprentissage des ouvertures d'échecs

POC pédagogique : déplacer les pièces, analyser une position FEN, consulter les
coups du catalogue Lichess, les parties de référence, les documents et vidéos,
puis enregistrer et retrouver une analyse dans MongoDB.

## Architecture et responsabilités

```text
Navigateur : Angular + Chessground (affichage) + chess.js (règles)
    │ HTTP /api — Nginx dans Docker, proxy Angular en développement
    ▼
FastAPI → LangGraph → validation FEN
                       ├─ partie terminée → résultat sans ressources
                       └─ Lichess
                          ├─ aucun coup → Stockfish → résultat moteur
                          └─ coups trouvés → Milvus → YouTube → génération Groq
    │ POST /analyses : validation du résultat, puis enregistrement
    ▼
MongoDB : analyses, dates et historique
```

Milvus recherche les passages du corpus ; MongoDB conserve les analyses utilisateur.
MinIO stocke les objets utilisés par Milvus et etcd ses métadonnées. Le modèle
Qwen3-Embedding-0.6B encode les questions chez DeepInfra via Hugging Face ;
Milvus reçoit le vecteur normalisé à 1024 dimensions. La génération est distante, chez Groq. La branche Stockfish se termine sans appel documentaire ou génération.

**État actuel :** frontend Nginx, backend et bases dans Docker Compose. Le frontend
peut aussi être lancé avec `npm start` en développement. L’API ne nécessite plus
de modèle local, mais le corpus doit être indexé dans Milvus : son initialisation
n’est pas encore entièrement automatisée depuis un clone vierge.

## Prérequis et configuration

- Docker Engine ou Docker Desktop avec Compose ; utiliser le même contexte Docker
  dans tous les terminaux (`docker context show`).
- Python 3.12 et uv pour les commandes locales.
- Node.js 24 et npm pour Angular ; dépendances fixées par `frontend/package-lock.json`.
- Clés Lichess, YouTube Data API, Groq et `HF_TOKEN` (permission Inference Providers).
  Le compte HF doit disposer de crédits/quota pour DeepInfra.
- Pour préparer le corpus localement uniquement : modèle
  `Qwen/Qwen3-Embedding-0.6B` présent dans le cache Hugging Face.
- Pour FastAPI hors Docker : Stockfish installé à `/usr/games/stockfish`.

Créer un `.env` non versionné à la racine avec ses propres valeurs :

```dotenv
APP_PORT=8080
LICHESS_API_TOKEN=remplacer
YOUTUBE_API_KEY=remplacer
GROQ_API_KEY=remplacer
HF_TOKEN=remplacer
```

Compose utilise `.env` pour substituer les valeurs et ne transmet au conteneur que
les variables déclarées dans `environment`. Le fichier n'est pas copié dans l'image.
En Python local, les services d'API externes chargent `.env` via python-dotenv.

| Paramètre | Python local | API Docker |
| --- | --- | --- |
| Adresse HTTP | `127.0.0.1:8081` avec la commande ci-dessous | `127.0.0.1:${APP_PORT}` |
| `MILVUS_URI` | `http://127.0.0.1:19530` par défaut | `http://standalone:19530` |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017` par défaut | `mongodb://mongodb:27017` |
| Embeddings des questions | API HF / DeepInfra | API HF / DeepInfra |
| `HF_TOKEN` | Chargé depuis `.env` | Transmis par Compose |

Pour les paramètres Python lus avec `os.getenv`, les exporter dans le terminal
avant le lancement plutôt que compter sur l'ordre des imports chargeant `.env`.

MongoDB utilise `mongo:7.0` : l'image 8.0 essayée sur ce poste refusait de démarrer
avec son noyau Linux. La base locale n'a pas d'authentification et son port est
publié sur la boucle locale. Cette configuration est celle du POC local.

## Lancer le POC actuel

Depuis la racine, après préparation et indexation du corpus (section suivante) :

```bash
# Démarrer les bases ; attendre les contrôles de santé avant d'analyser.
docker compose up -d standalone mongodb
docker compose ps

# Reconstruire seulement si le code ou les dépendances du backend ont changé.
docker compose up -d --build api

# Consulter les logs ; Ctrl+C quitte le suivi sans arrêter le conteneur.
docker compose logs -f api
```

L'API attend MongoDB grâce à `depends_on`. Milvus doit être démarré séparément
par la première commande : il n'est pas encore une dépendance déclarée de l'API.
Swagger : [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs) avec `APP_PORT=8080`.
Le healthcheck HTTP confirme seulement que FastAPI répond, pas que ses dépendances
ou les clés externes sont disponibles.

Pour le frontend Docker (libérer le port 4200 si `npm start` tourne déjà) :

```bash
docker compose up -d --build --no-deps frontend
```

Nginx transmet `/api/` au service `api:8080`. Après une recréation de l’API,
redémarrer Nginx si l’ancienne adresse du conteneur provoque un HTTP 502 :
`docker compose restart frontend`.

Ou, pour développer le frontend avec rechargement automatique :

```bash
cd frontend
npm ci
npm start
```

Interface : [http://127.0.0.1:4200](http://127.0.0.1:4200).
Le proxy actuel transmet `/api/**` à `http://127.0.0.1:8080`.
Changer sa cible si `APP_PORT` diffère, puis redémarrer Angular. `npm start` doit
être lancé dans `frontend`, où se trouve `package.json`.

### Développement du backend sans reconstruction

Garder les bases Docker actives, puis lancer à la racine :

```bash
uv sync --locked
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8081 --reload --reload-dir backend
```

Pour tester cette API depuis Angular, cibler `http://127.0.0.1:8081` dans
`frontend/proxy.conf.json` et redémarrer Angular. L'API Docker peut rester sur 8080.

## Embeddings hébergés et préparation locale

`embedding_service.py` encode une question via HF / DeepInfra avec le même modèle
et la même instruction que l’évaluation. Il vérifie la forme `(1, 1024)`, les
valeurs finies et une norme non nulle, puis normalise le vecteur. Aucun repli local
silencieux n’est effectué. `vector_search_service.py` conserve les recherches
COSINE et le filtre paramétré par titre.

Les erreurs sont exposées de façon identique sur les routes de recherche et
d’analyse : 500 pour une clé absente ou un accès refusé, 504 pour un délai dépassé,
503 pour crédits/quota indisponibles, 502 pour réseau, autre erreur fournisseur ou
réponse incompatible. Les réponses brutes et secrets du fournisseur ne sont pas
renvoyés au navigateur. Une analyse en échec n’est pas enregistrée.

Évaluation locale/distance sur 30 ouvertures, avec et sans filtre : mêmes ensembles
de passages dans les 60 comparaisons, cosinus moyen 0,99979. Les deux premiers
passages de la française changent d’ordre ; l’italienne filtrée retourne deux
passages dans les deux cas. Encodage du lot : 1,34 s distant (réseau inclus),
9,51 s CPU (hors chargement). Ces résultats ne constituent pas une garantie de
latence ou de pertinence pour toute question. Le coût n’a pas été mesuré.

Le cache `embedding_cache` et le service optionnel `embedding-init` restent
disponibles pour les essais locaux ; ils ne sont plus montés dans l’API.
Pour télécharger le modèle dans le cache de l’ordinateur utilisé pour préparer
le corpus, lancer `uv run python -m backend.app.commands.download_embedding_model`.
L’encodage des documents reste local. Ses dépendances (`sentence-transformers`,
PyTorch et bibliothèques NVIDIA/CUDA sous Linux) appartiennent au groupe optionnel
`local-embeddings`. L’image API installe uniquement les dépendances principales :
ces bibliothèques lourdes en sont exclues. NumPy reste nécessaire pour valider et
normaliser les vecteurs reçus de HF.

```bash
# Environnement API uniquement.
uv sync --locked --no-default-groups

# Encodage local ou comparaison : inclure explicitement le groupe.
uv run --group local-embeddings python -m backend.app.commands.embed_wikipedia
uv run --group local-embeddings python -m scripts.explore_embeddings_hf --evaluation
```

Un `uv sync` standard peut retirer les paquets optionnels de l’environnement ;
utiliser `--group local-embeddings` avec les commandes qui chargent le modèle.
Le fichier `uv.lock` conserve les versions NVIDIA pour ce groupe : leur présence
dans le verrou ne signifie pas qu’elles sont installées dans l’image API.

Le Dockerfile copie `pyproject.toml` et `uv.lock` avant le code et installe les
dépendances dans une couche distincte. Une modification du backend seule réutilise
cette couche ; une modification des dépendances nécessite une nouvelle installation.
Seul `backend/` est ensuite copié : corpus, scripts locaux et frontend sont exclus.
La première reconstruction avec cette organisation doit recréer les couches.

## Contrat HTTP et persistance

| Méthode et route | Rôle |
| --- | --- |
| `GET /api/v1/healthcheck` | Disponibilité du processus API |
| `GET /api/v1/position?fen=...` | Validité, trait, coups légaux, fin de partie |
| `GET /api/v1/opening-moves?fen=...` | Analyse via le graphe, sans enregistrement |
| `POST /api/v1/analyses` | Corps `{"fen": "..."}` ; calcule et enregistre, répond `201` avec `{id, result}` |
| `GET /api/v1/analyses/{id}` | Relit `{_id, fen, created_at, result}` |
| `GET /api/v1/analyses?limit=10` | Résumés `{_id, fen, created_at}`, récents d'abord ; limite de 1 à 50 |
| `GET /api/v1/vector-search?question=...&limit=3` | Recherche documentaire libre |
| `GET /api/v1/videos/{opening}?limit=3` | Recherche YouTube indépendante |

Les analyses sont stockées dans `chess_coach.analyses`. Un POST crée toujours un
nouveau document, même pour la même FEN. GET ne recalcule pas l'analyse. Les dates
sont enregistrées en UTC ; la liste conserve le fuseau, tandis que la lecture
individuelle renvoie actuellement une date UTC sans suffixe de fuseau.

Le frontend conserve l'identifiant du résultat courant et invalide l'affichage
lorsqu'une position change. Une réponse devenue obsolète est ignorée côté écran,
mais cela n'annule pas le calcul ou l'enregistrement déjà lancé sur le serveur.
L'historique s'actualise manuellement, via son bouton.

MongoDB persiste dans le volume nommé `mongodb_data` (préfixé par le projet dans
Docker). Milvus, etcd et MinIO utilisent `volumes/`. `docker compose down` conserve
le volume nommé ; `docker compose down -v` le supprime. Ne pas employer cette
seconde commande pour un simple redémarrage.

## Vérifications manuelles et limites

- **Partie terminée** : `8/8/8/8/8/2k5/8/K7 w - - 0 1` ; aucun appel Lichess,
  Stockfish, documentaire ou vidéo. Le POST doit enregistrer le résultat.
- **Défense française** : `rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3` ;
  vérifier coups, ressources, explication, puis relecture par identifiant.
- **Identifiant** : `bonjour` doit produire 400 ; un ObjectId valide absent produit 404.
- **Historique** : `limit=0` produit 422. Charger un élément doit restaurer la FEN
  et le panneau sans nouveau POST.
- **Frontend** : `cd frontend` puis `npm run build` vérifie TypeScript et les templates.

Les essais manuels réussis ne remplacent pas une suite de tests automatisés. Les
commandes d'évaluation ci-dessous portent sur la recherche et la génération.
Le script npm `test` est hérité du squelette Angular : aucune suite frontend n'est
encore configurée dans `angular.json`.

Les coups Lichess sont des coups observés dans son catalogue masters, pas une
preuve du meilleur coup absolu. L'explication décrit l'ouverture reconnue ; elle
ne constitue pas une analyse tactique détaillée de la FEN. Le filtre documentaire
ne couvre que les correspondances présentes dans `opening_service.py`. Une FEN
ne contient pas l'historique nécessaire pour détecter toutes les répétitions.

À finaliser pour la livraison : initialisation du corpus portable,
test de persistance après recréation, validation de la branche Stockfish et étude
vidéo/MCP. Les routes séparées moves/evaluate évoquées dans le sujet ne sont pas
exposées à l'identique : l'analyse est actuellement regroupée dans le graphe.

## Organisation

```text
backend/app/
├── main.py              # Routes FastAPI
├── schemas.py           # Modèles de réponse Pydantic
├── graphs/              # Orchestration LangGraph
├── services/            # Fonctions réutilisables par l'API et les commandes
└── commands/            # Collecte, préparation, indexation et évaluation
frontend/                # Angular : échiquier, panneau et services HTTP
scripts/                 # Explorations et tests manuels internes, ignorés par Git
data/                    # Corpus, caches et vecteurs générés, ignorés par Git
```

Les commandes dans `backend/app/commands/` sont versionnées et se lancent
explicitement : importer un module ne télécharge rien et ne lance aucun traitement.
Les anciens exercices dans `scripts/` ne constituent pas le pipeline de référence.

## Préparer le corpus français

Depuis la racine du projet, dans l'environnement installé avec `uv sync --locked` :

```bash
# Collecte les 30 articles, réutilise leur cache local et produit les chunks.
uv run python -m backend.app.commands.collect_wikipedia

# Facultatif : redécouper uniquement le corpus déjà enregistré.
uv run python -m backend.app.commands.chunk_wikipedia

# Encoder les chunks (GPU par défaut ; --device cpu pour le CPU).
uv run --group local-embeddings python -m backend.app.commands.embed_wikipedia

# Vérifier le manifeste, les identifiants et les vecteurs sans contacter Milvus.
uv run python -m backend.app.commands.index_milvus --check-only

# Démarrer Milvus et ses dépendances ; attendre leur état healthy.
docker compose up -d standalone
docker compose ps

# Importer les vecteurs existants, sans les recalculer.
uv run python -m backend.app.commands.index_milvus
```

Les quatre commandes de préparation acceptent `--data-dir /chemin/du/corpus`.
Sans cet argument, elles utilisent `data/wikipedia_fr/`, indépendamment de leur
emplacement dans `backend/app/commands/`. Lancer les modules depuis la racine permet
à Python de trouver le package `backend`.

La collecte accepte `--refresh` pour télécharger de nouveau les articles.
L'encodage accepte `--reuse` pour vérifier et recharger les embeddings existants.
Le modèle `Qwen/Qwen3-Embedding-0.6B` doit déjà être disponible dans le cache
Hugging Face : les commandes utilisent `local_files_only=True`.
Après une modification des chunks, recalculer les embeddings avant l'import.
Le manifeste vérifie la correspondance entre le texte et les vecteurs.

La commande d'import utilise la collection `chess_openings_fr_v2` et remplace les
entrées de même identifiant par `upsert`. Elle ne supprime ni collection ni anciens
identifiants absents du nouvel import. L'adresse Milvus est configurable via
`MILVUS_URI` (par défaut `http://127.0.0.1:19530` en local).

## Corpus Wikichess de référence

```bash
uv run python -m backend.app.commands.collect_wikichess
```

Cette commande collecte cinq articles anglais dans `data/wikichess.json`.
Elle accepte `--output /chemin/fichier.json`. Ce corpus reste séparé du corpus
Wikipédia français actuellement indexé dans Milvus.

## Évaluer la recherche libre

```bash
uv run python -m backend.app.commands.evaluate_retrieval
```

Milvus doit être lancé et la collection remplie. Le modèle est chargé une fois pour
les trois cas. Le bilan indique si l'ouverture attendue apparaît dans les trois
premiers résultats, en séparant les erreurs techniques des résultats non pertinents.
Cette évaluation ne mesure ni la qualité des explications ni le routage FEN du graphe.

## Évaluer la génération documentaire

La campagne compare des modèles Groq et des consignes de génération, avec des
contextes identiques pour les 30 ouvertures et un contrôle Python des preuves
textuelles. Le classement utilise les vecteurs existants en cosine exact,
sans reconstruire Docker ni réindexer Milvus.

```bash
# Première campagne seulement : prépare les cas figés (modèle local, CUDA).
uv run --group local-embeddings python -m backend.app.commands.evaluate_generation prepare

# Appels Groq : consomment le quota de GROQ_API_KEY ; reprise des cas déjà terminés.
uv run python -m backend.app.commands.evaluate_generation run --configs gpt20_low qwen_low --interval 40

# Recalcule les contrôles et produit les réponses lisibles, sans appel réseau.
uv run python -m backend.app.commands.evaluate_generation summarize
```

Les sorties sont dans `data/generation_evaluation/` : cas, réponses brutes,
`summary.json` et `checked_*.md`. Pour une nouvelle campagne,
passer `--output data/autre_campagne` **avant** la sous-commande. Les prompts et
paramètres sont enregistrés ; changer les paramètres exige un dossier séparé.
La préparation refuse d'écraser des cas déjà utilisés.

Le sous-programme `review` conserve une expérience de relecture LLM non retenue :
elle n'a pas détecté les erreurs ciblées. Les fichiers historiques `validated_*`
ne sont pas un label de fiabilité. Les contrôles de citations ne garantissent ni
la fidélité des reformulations ni la pertinence pour une position FEN précise. Le rapport
[d'évaluation](reports/generation-rag-2026-09-25.md) distingue ces limites des
mesures techniques et expose les choix retenus.

## Anciennes commandes déplacées

| Ancien module | Nouveau module |
| --- | --- |
| `scripts.explore_wikipedia` | `backend.app.commands.collect_wikipedia` |
| `scripts.explore_wikichess` | `backend.app.commands.collect_wikichess` |
| `scripts.explore_milvus` | `backend.app.commands.index_milvus` |
| `scripts.evaluate_retrieval` | `backend.app.commands.evaluate_retrieval` |
| Écriture depuis `scripts.explore_chunking` | `backend.app.commands.chunk_wikipedia` |
| Génération depuis `scripts.explore_embeddings` | `backend.app.commands.embed_wikipedia` |

Les explorations de chunking et d'embeddings restent dans `scripts/` pour comparer
les résultats, sans réécrire le corpus ou les vecteurs.
