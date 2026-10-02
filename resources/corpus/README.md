# Lot de démonstration — ouvertures françaises v1

Ce dossier est destiné à être versionné avec le projet. Il permet un démarrage
sans le dossier local `data/`, sans modèle Qwen téléchargé et sans recalcul.

- `chess-openings-fr-v1.zip` : 339 passages de 30 articles, vecteurs à 1024 dimensions.
- `chess-openings-fr-v1.zip.sha256` : empreinte de l'archive, vérifiée avant lecture.
- Dans l'archive : chunks JSON, vecteurs NumPy, manifeste de correspondance et
  `SOURCES.md` avec attribution des contributeurs Wikipédia, liens des articles
  et historiques, licence CC BY-SA 4.0 et transformations apportées.

Les textes ont été extraits, nettoyés et découpés ; les révisions exactes des
articles n'ont pas été conservées lors de la collecte initiale. Le lot fige les
textes encodés le 23 septembre 2026. Il ne contient ni poids du modèle, ni secrets,
ni analyses utilisateur, ni sauvegarde des volumes Milvus/MongoDB.

## Contrôler sans base de données

Depuis la racine, après construction de l'image API :

```bash
docker compose run --rm --no-deps corpus-init python -m backend.app.commands.index_milvus --bundle /corpus/chess-openings-fr-v1.zip --check-only
```

Ou avec Python/uv :

```bash
uv run python -m backend.app.commands.index_milvus --bundle resources/corpus/chess-openings-fr-v1.zip --check-only
```

## Importer

```bash
docker compose run --rm corpus-init
```

Le service réutilise l'image API construite par `docker compose build api` et
attend que Milvus soit healthy. Il crée la collection si nécessaire, valide son
schéma et fait un upsert. Un second lancement réutilise les mêmes identifiants.
Il ne supprime pas les autres entrées d'une collection existante ; un écart de
comptage est signalé. Un import interrompu peut être relancé.

Le profil `setup` évite un import automatique à chaque démarrage de l'application.
L'archive est montée en lecture seule et décompressée temporairement, après
vérification de sa taille, son empreinte et de ses noms de fichiers.

## Renouveler le lot

Après préparation et vérification du corpus local :

```bash
uv run python -m backend.app.commands.package_corpus --output resources/corpus/chess-openings-fr-v2.zip
```

Choisir un nouveau nom pour un contenu différent, mettre à jour le chemin dans
Compose et inclure ensemble l'archive et son checksum dans le prochain commit.
Ne pas ajouter tout `data/` au dépôt. Les lots volumineux pourront être distribués
plus tard comme pièces jointes de releases ; aucune release n'est créée ici.

Référence pour l'attribution et la licence des textes :
[conditions Wikimedia, section 7](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use/en#7._Licensing_of_Content).
