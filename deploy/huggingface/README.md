---
title: Chess Coach
emoji: ♟️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# Chess Coach

Analyse d'une position d'échecs avec Lichess, Stockfish et un RAG documentaire.
Angular et FastAPI sont servis dans un même conteneur. Le corpus vectoriel est
hébergé dans Zilliz ; l'historique de démonstration utilise un Dataset HF privé.
La version Docker Compose du projet conserve MongoDB.

## Variables du Space

- `HISTORY_BACKEND` : `hf_dataset`
- `HF_HISTORY_REPO` : `compte/nom-du-dataset-prive`
- `MILVUS_URI` : endpoint HTTPS Zilliz

## Secrets du Space

- `HF_HISTORY_TOKEN` : écriture sur le Dataset d'historique uniquement
- `MILVUS_TOKEN` : clé du cluster Zilliz
- `HF_TOKEN` : accès aux Inference Providers pour les embeddings
- `GROQ_API_KEY`, `YOUTUBE_API_KEY`, `LICHESS_API_TOKEN`

Créer le Dataset privé et importer le corpus dans Zilliz avant le premier essai.
Aucun secret ne doit être enregistré dans les fichiers du dépôt.

L'historique est partagé entre les visiteurs de cette démonstration. Il ne doit
contenir aucune donnée personnelle. Une sauvegarde représente un petit fichier
JSON et un commit dans le Dataset : cette solution vise un faible trafic et reste
soumise aux quotas du Hub. Le Space gratuit peut se mettre en veille.
