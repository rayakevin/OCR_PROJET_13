# Projet 13 — Agent d'apprentissage des ouvertures d'échecs

## Organisation

```text
backend/app/
├── main.py              # Routes FastAPI
├── schemas.py           # Modèles de réponse Pydantic
├── graphs/              # Orchestration LangGraph
├── services/            # Fonctions réutilisables par l'API et les commandes
└── commands/            # Collecte, préparation, indexation et évaluation
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
uv run python -m backend.app.commands.embed_wikipedia

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

## Développer sans reconstruire Docker

```bash
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8081 --reload
```

Documentation interactive : <http://127.0.0.1:8081/docs>.
Milvus reste dans Docker ; l'API locale utilise par défaut le GPU et le cache local
du modèle. `EMBEDDING_DEVICE=cpu` permet de choisir le CPU.
Réserver la reconstruction de l'API Docker aux validations d'étape.

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
