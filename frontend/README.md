# Frontend — Coach d’échecs

Interface Angular 22, TypeScript, Chessground pour l'échiquier et chess.js pour
les règles. Les données du coach viennent de FastAPI ; aucune clé API externe
n'est nécessaire dans le navigateur.

## Démarrer

Depuis ce dossier, avec Node.js 24 et npm :

```bash
npm ci
npm start
```

Ouvrir [http://127.0.0.1:4200](http://127.0.0.1:4200). Garder le terminal ouvert ;
les modifications du code sont rechargées automatiquement. Ctrl+C arrête le serveur.
Si 4200 est occupé, retrouver le serveur existant plutôt que multiplier les instances.

`proxy.conf.json` transmet `/api/**` à l'API Docker sur 8080. Pour travailler avec
FastAPI local sur 8081, modifier cette cible et redémarrer `npm start`.
Le proxy appartient au serveur de développement : il n'est pas embarqué dans le
build statique. Dans Docker, `nginx.conf` sert les fichiers compilés et transmet
`/api/` à `api:8080`. Depuis la racine, lancer
`docker compose up -d --build --no-deps frontend` avec l’API déjà démarrée.
Le port 4200 doit être libre ; il faut reconstruire le frontend après une modification.

Voir le [README principal](../README.md) pour démarrer le backend et les bases.

## Où lire le code ?

| Fichier | Responsabilité |
| --- | --- |
| `src/main.ts` | Démarre le composant App avec sa configuration |
| `src/app/app.config.ts` | Fournit notamment HttpClient |
| `src/app/app.ts` | Partie chess.js, échiquier, signaux et actions utilisateur |
| `src/app/app.html` | Affichage conditionnel, boucles et événements des boutons |
| `src/app/app.css` | Mise en page et styles du composant |
| `src/app/services/chess-api.ts` | Appels HTTP ; ne gère pas l'affichage |
| `src/app/models/coach-response.ts` | Contrats TypeScript des réponses ; pas une validation JSON à l'exécution |
| `src/app/data/coach-demo.ts` | Positions et anciennes réponses d'exemple ; les appels réels ne lisent que les réponses API |
| `src/styles.css` | Styles globaux et styles des pièces Chessground |

## Parcours des données

1. Un déplacement est validé par chess.js ; `syncPosition()` actualise la FEN et
   les destinations légales, puis efface l'analyse de l'ancienne position.
2. `analysePosition()` appelle le POST : FastAPI calcule et enregistre dans MongoDB.
3. `response.result` alimente le panneau ; `response.id` identifie l'enregistrement.
4. `refreshHistory()` charge les dix derniers résumés. L'actualisation est manuelle.
5. `loadSavedAnalysis()` restaure d'abord la FEN, puis le résultat enregistré.

Les signaux représentent l'état courant. Les templates les lisent avec `signal()`.
Les méthodes modifient cet état avec `.set(...)`. `analysisRequestId` empêche une
réponse ancienne de remplacer le panneau après un changement de position ; il
n'annule pas l'opération côté serveur. La promotion demande le choix d'une pièce
avant de permettre une nouvelle analyse.

## Vérifier

```bash
npm run build
```

Le build vérifie le code et les templates et produit `dist/chess-coach/`.
Le script `npm test` est encore celui du squelette : aucun exécuteur de tests n'est
configuré. Pour les contrôles manuels, tester analyse, erreur, déplacement d'un
coup proposé, promotion, changement de FEN, historique et restauration.
