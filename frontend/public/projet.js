'use strict';
// Parcours pédagogiques : aucun appel réseau ni accès aux données des visiteurs.
const steps = {
  move: ['Navigateur', 'Un coup légal', 'chess.js valide le coup ; Chessground actualise le plateau. Après 300 ms, le navigateur demande une analyse. Une seule requête est active ; les réponses dépassées sont ignorées.', 'FEN + position de départ + coups UCI'],
  api: ['FastAPI', 'Une analyse sans stockage', 'Pydantic contrôle le corps de la requête. FastAPI initialise l’état de LangGraph. Rien n’est écrit dans MongoDB pendant ce parcours.', 'POST /api/v1/analyses/preview'],
  validate: ['LangGraph · python-chess', 'Valider et orienter', 'Le premier nœud inspecte la position. Une partie terminée arrête le graphe. Sinon, le parcours continue vers Lichess.', 'validation → fin OU fetch'],
  lichess: ['Lichess Explorer', 'Consulter les coups théoriques', 'Le catalogue masters renvoie jusqu’à trois coups et deux parties de référence. Les coups joués depuis la FEN chargée aident à conserver le contexte d’ouverture. Une panne Lichess reste une erreur, pas une absence de théorie.', 'fetch → documents si coups ; sinon stockfish'],
  documents: ['Hugging Face · Milvus / Zilliz', 'Retrouver des passages', 'Si le nom d’ouverture possède une correspondance dans le corpus, le service encode une question sur ses principes et plans avec Qwen. Milvus recherche trois passages avec un filtre par ouverture ; ils sont ensuite remis dans l’ordre de lecture de l’article, ce qui stabilise la numérotation des sources et le cache.', 'question → embedding 1 024 dimensions → passages Wikipédia'],
  videos: ['YouTube Data API', 'Compléter avec des vidéos', 'Le nœud suivant recherche deux vidéos en utilisant le nom français de l’ouverture. Ce sont des liens vers des vidéos ; aucun traitement vidéo ni reconnaissance d’échiquier n’a lieu.', 'documents → videos'],
  explain: ['Groq', 'Générer une explication sourcée', 'Avec une ouverture couverte et des documents, le modèle produit une réponse structurée. Le code contrôle les numéros de sources et la présence exacte des citations. Le corpus étant figé, les succès sont réutilisés sans expiration à position, question et documents identiques : d’abord en mémoire, puis depuis MongoDB.', 'videos → explanation → fin'],
  quota: ['Groq · résultat partiel', 'Conserver ce qui fonctionne', 'Si Groq atteint son quota, le service respecte Retry-After avant de rappeler le fournisseur. L’explication reste vide, mais les coups, documents et vidéos sont conservés avec un avertissement. Une reprise est possible depuis l’interface.', 'explanation = null ; warnings = [message]'],
  ragFailure: ['Hugging Face · Milvus · résultat partiel', 'Continuer sans documents', 'Si l’encodage de la question échoue (quota ou crédits Hugging Face épuisés, délai dépassé) ou si Milvus est indisponible, le nœud documents renvoie une liste vide et un avertissement. Les coups sont conservés, les vidéos sont recherchées et Groq n’est pas appelé, faute de sources.', 'documents = [] ; warnings = [message]'],
  engine: ['Stockfish', 'Évaluer avec le moteur', 'Si Lichess renvoie zéro coup, Stockfish propose un coup et une évaluation. Cette branche termine le graphe sans passer par la recherche documentaire, YouTube ou Groq.', 'stockfish → fin'],
  unmapped: ['Services documentaires', 'S’abstenir sans correspondance', 'Les nœuds vérifient le nom d’ouverture. Sans correspondance documentaire, ils retournent des listes vides et aucune explication. Les coups Lichess restent disponibles.', 'documents = [] ; videos = [] ; explanation = null'],
  terminal: ['LangGraph', 'Terminer sans outils externes', 'Une position terminée renvoie son motif : mat, pat, matériel insuffisant, etc. Aucun appel Lichess, Stockfish, embeddings, YouTube ou Groq n’est nécessaire.', 'game_over = true ; moves = []'],
  display: ['Angular', 'Afficher la réponse actuelle', 'L’interface vérifie que la réponse appartient encore à la position affichée. Elle présente les coups, les ressources disponibles et les avertissements. La sauvegarde reste un choix explicite.', 'résultat JSON → panneau du coach'],
  save: ['Navigateur', 'Choisir de conserver la position', 'Le bouton devient disponible quand une analyse est affichée. Il transmet cette analyse, y compris ses éventuels avertissements. Un double clic est bloqué pendant l’enregistrement.', 'Sauvegarder la position'],
  persist: ['FastAPI · Pydantic', 'Valider le résultat à sauvegarder', 'La route valide le résultat transmis par le navigateur et sa FEN, puis appelle le service de stockage. Elle ne recalcule pas l’analyse et ne relance aucun fournisseur.', 'POST /api/v1/analyses/save'],
  mongo: ['MongoDB / Atlas', 'Écrire une sauvegarde', 'Un document contient la FEN, le résultat et une date UTC. Un nouvel enregistrement reçoit un identifiant. Il s’agit d’un instantané, pas du déroulé complet de la partie.', '{ _id, fen, created_at, result }'],
  saved: ['Angular', 'Confirmer et actualiser', 'Le bouton indique « Position sauvegardée ». L’interface actualise toutes les sauvegardes, triées par date décroissante. Cet historique est commun aux visiteurs.', '201 Created → GET /api/v1/analyses'],
  choose: ['Navigateur', 'Sélectionner une sauvegarde', 'Un clic sur une ligne de l’historique transmet son identifiant au backend. La liste contient toutes les positions sauvegardées, des plus récentes aux plus anciennes.', 'identifiant de sauvegarde'],
  read: ['FastAPI → MongoDB', 'Relire le résultat enregistré', 'Le backend vérifie l’identifiant et retrouve le document. Une sauvegarde absente renvoie 404. Les outils Lichess, Stockfish, Milvus, YouTube et Groq ne sont pas appelés.', 'GET /api/v1/analyses/{id}'],
  restore: ['Angular', 'Restaurer l’échiquier et l’analyse', 'Le navigateur charge la FEN, puis affiche le résultat conservé, sans nouveau calcul. Jouer un nouveau coup déclenchera une nouvelle analyse. Les coups antérieurs à la sauvegarde ne sont pas restaurés.', 'FEN enregistrée + résultat enregistré']
};
steps.failure = ['FastAPI · erreur', 'Signaler l’échec de Lichess', 'Un délai dépassé produit une réponse HTTP 504 ; une erreur HTTP ou réseau produit une 502. Le graphe s’arrête : Stockfish n’est pas un repli automatique en cas de panne Lichess. Le navigateur affiche l’erreur et permet une nouvelle tentative.', '504 / 502 → message dans Angular'];
steps.storageFailure = ['FastAPI · stockage', 'Ne pas confirmer une sauvegarde échouée', 'Une erreur de connexion MongoDB est traduite en HTTP 503. L’analyse affichée reste disponible, mais aucune confirmation de sauvegarde n’est annoncée. L’utilisateur peut réessayer.', '503 → analyse conservée à l’écran'];
const paths = {
  failure: ['move','api','validate','lichess','failure'],
  storageFailure: ['save','persist','mongo','storageFailure'],
  opening: ['move','api','validate','lichess','documents','videos','explain','display'],
  engine: ['move','api','validate','lichess','engine','display'],
  unmapped: ['move','api','validate','lichess','unmapped','display'],
  finished: ['move','api','validate','terminal','display'],
  quota: ['move','api','validate','lichess','documents','videos','quota','display'],
  ragFailure: ['move','api','validate','lichess','ragFailure','videos','display'],
  save: ['save','persist','mongo','saved'],
  restore: ['choose','read','restore']
};

// Modules et connexions fixes : l’étape sélectionnée ne modifie que leur état visuel.
const activity = {
  move: ['browser', '', 'chess.js → état Angular : nouvelle FEN légale'],
  api: ['browser api graph', 'browser-api api-graph', 'Angular → FastAPI → LangGraph : FEN, position de départ et coups UCI'],
  validate: ['graph', '', 'validation : inspection de la FEN → statut de la position'],
  lichess: ['graph lichess', 'graph-lichess', 'LangGraph → Lichess → LangGraph : contexte → coups, ouverture et parties'],
  documents: ['graph rag', 'graph-rag', 'LangGraph → embedding de la question → Milvus → passages filtrés'],
  videos: ['graph youtube', 'graph-youtube', 'LangGraph → YouTube → LangGraph : ouverture → liens vidéo'],
  explain: ['graph groq', 'graph-groq', 'LangGraph → Groq → contrôle des citations → explication'],
  quota: ['graph groq', 'graph-groq', 'Groq → LangGraph : indisponibilité → avertissement et résultat partiel'],
  ragFailure: ['graph rag', 'graph-rag', 'Embeddings / Milvus → LangGraph : indisponibilité → documents vides et avertissement'],
  engine: ['graph engine', 'graph-engine', 'LangGraph → Stockfish → LangGraph : FEN → coup et évaluation'],
  unmapped: ['graph', '', 'Nœuds documents, videos et explanation : absence de correspondance → sorties vides'],
  terminal: ['graph', '', 'validation → END : position terminée, aucun outil externe'],
  display: ['graph api browser', 'api-graph browser-api', 'LangGraph → FastAPI → Angular : résultat de la position courante'],
  save: ['browser', '', 'Angular : analyse affichée → demande explicite de sauvegarde'],
  persist: ['browser api', 'browser-api', 'Angular → FastAPI : résultat JSON → validation Pydantic'],
  mongo: ['api mongo', 'api-mongo', 'FastAPI → MongoDB : insertion FEN + résultat + date → identifiant'],
  saved: ['mongo api browser', 'api-mongo browser-api', 'MongoDB → FastAPI → Angular : confirmation puis liste complète des résumés'],
  choose: ['browser', '', 'Angular : sélection d’un identifiant dans l’historique'],
  read: ['browser api mongo', 'browser-api api-mongo', 'Angular → FastAPI → MongoDB → Angular : identifiant → résultat sauvegardé'],
  restore: ['browser', '', 'Angular → chess.js / Chessground : FEN restaurée et résultat affiché'],
  failure: ['lichess graph api browser', 'graph-lichess api-graph browser-api', 'Lichess → FastAPI → Angular : délai dépassé ou erreur réseau'],
  storageFailure: ['mongo api browser', 'api-mongo browser-api', 'MongoDB → FastAPI → Angular : erreur de connexion, aucune confirmation']
};
const safeguards = {
  move: ['Les coups illégaux sont refusés. Une promotion attend le choix de la pièce. Les nouvelles positions remplacent la demande en attente ; une réponse obsolète ne remplace pas l’écran courant.', 'Temporisation de 300 ms. Une seule requête active par interface ; pas de délai maximal global côté navigateur.'],
  api: ['Le contrat Pydantic contrôle les types et champs : requête mal formée → 422. La FEN est ensuite inspectée côté métier. Cette route n’écrit rien en base.', 'Exécution synchrone du graphe. Les délais des services peuvent se cumuler.'],
  validate: ['FEN invalide → 400. Mat, pat ou autre fin détectée → END. La FEN ne permet pas à elle seule de reconstruire tous les coups précédents.', 'Contrôle local avant tout appel externe.'],
  lichess: ['Les coups doivent être compatibles avec la position. Zéro coup déclenche Stockfish ; une panne ne déclenche pas cette bifurcation.', 'Timeout HTTP configuré à 15 s. Délai dépassé → 504 ; erreur fournisseur ou transport → 502.'],
  documents: ['Sans correspondance d’ouverture, aucun appel d’embedding. Sinon recherche de trois documents avec filtre d’ouverture. Une panne d’embedding ou de Milvus ne bloque pas l’analyse : documents vides et avertissement.', 'Embedding : 60 s ; connexion Milvus : 15 s ; recherche : 30 s. Ces seuils ne forment pas une garantie de latence totale.'],
  videos: ['Recherche bornée à deux résultats dans le graphe. Sans ouverture couverte, liste vide. Une panne YouTube peut interrompre l’analyse entière.', 'Transport HTTP : 15 s. Les erreurs maîtrisées de recherche deviennent des erreurs HTTP 502.'],
  explain: ['Sans documents, abstention. Contrôle du JSON, des identifiants de sources et des extraits cités. Cache sans expiration : 64 réponses en mémoire, puis MongoDB (explanation_cache), consulté même pendant une limite Groq. Le score Milvus est exclu de la clé. Une panne MongoDB entraîne une simple régénération. Accès sérialisé par processus.', 'Timeout SDK : 60 s par appel, sans retries SDK. L’attente du verrou peut s’ajouter. Une erreur de génération devient un avertissement.'],
  quota: ['HTTP 429 : arrêt des nouveaux appels jusqu’à expiration du cooldown ; les coups, documents et vidéos sont conservés. Aucun retry automatique en boucle.', 'Retry-After est utilisé ; 30 s par défaut, minimum 1 s. Le bouton de reprise permet une tentative ultérieure.'],
  ragFailure: ['Les erreurs d’embedding et de Milvus sont interceptées dans le nœud documents : coups et vidéos conservés, aucune explication sans sources. Le message Milvus est générique, sans détail interne.', 'Quota ou crédits épuisés (HTTP 402/429) : échec immédiat, sans retry. Embedding : 60 s ; Milvus : 15 s de connexion, 30 s de recherche.'],
  engine: ['Le moteur est lancé uniquement après une réponse Lichess sans coups. Une erreur moteur est remontée, jamais convertie en faux conseil.', 'Budget d’analyse moteur : 1 s ; timeout de communication configuré : 10 s. Ce budget n’inclut pas tout le parcours HTTP.'],
  unmapped: ['Abstention documentaire explicite ; les coups théoriques restent affichables. Le nom de l’ouverture ne garantit pas une couverture dans le corpus.', 'Les appels d’enrichissement sont évités pour ce cas.'],
  terminal: ['Retour du motif de fin, sans suggestion de coup ni appel fournisseur.', 'Traitement local ; pas de latence fournisseur.'],
  display: ['Vérification de la position associée à la réponse ; résultats obsolètes ignorés. Avertissements visibles et sauvegarde manuelle.', 'La réponse complète est attendue avant affichage ; pas de streaming.'],
  save: ['Bouton désactivé pendant l’enregistrement ; pas de sauvegarde automatique à chaque coup. La position sauvegardée est un instantané.', 'Aucun recalcul ni délai des fournisseurs d’analyse.'],
  persist: ['Contrat du résultat et FEN validés côté serveur. Pas de recalcul pour vérifier l’origine du résultat : le serveur accepte le contenu valide fourni par le client.', 'Erreurs de validation → 400 ou 422 ; panne de connexion au stockage → 503.'],
  mongo: ['Chaque insertion crée un identifiant distinct. FEN, résultat et date UTC sont persistés. Le double clic est bloqué côté interface, sans clé d’idempotence serveur.', 'Sélection du serveur MongoDB : 5 s. Ce délai n’est pas une borne globale sur toutes les opérations.'],
  saved: ['Confirmation uniquement après réponse de succès. Tous les résumés sont rechargés et triés du plus récent au plus ancien ; les résultats détaillés restent chargés à la demande.', 'Une erreur d’actualisation ne supprime pas la sauvegarde déjà confirmée.'],
  choose: ['La liste affiche des positions, pas des parties complètes. L’identifiant provient de la ligne sélectionnée.', 'Lecture à la demande du détail, sans réanalyse.'],
  read: ['Identifiant mal formé → 400 ; document absent → 404 ; connexion indisponible → 503.', 'Sélection serveur MongoDB : 5 s ; aucun appel Lichess, Milvus, YouTube ou Groq.'],
  restore: ['Le chargement restaure le résultat enregistré. Les coups avant la FEN ne sont pas récupérés ; un nouveau coup relance le parcours d’analyse.', 'Rendu local après réception du document.'],
  failure: ['Les erreurs sont affichées et l’état de chargement est libéré. La position reste jouable. Le chemin Stockfish n’est emprunté que sur absence de coups, jamais sur erreur.', 'Pas de relance automatique infinie. L’utilisateur peut réessayer.'],
  storageFailure: ['L’interface garde le résultat mais n’affirme pas qu’il a été enregistré. Sans idempotence, une coupure après écriture mais avant réponse peut entraîner un doublon à la reprise.', 'HTTP 503 pour une erreur de connexion prise en charge. Nouvelle tentative explicite.']
};

// Retour attendu du scénario, distinct du module actif à l’étape courante.
const exchanges = {
  opening: ['200 · analyse enrichie', 'Coups théoriques, parties de référence et ressources de l’ouverture. L’explication dépend des sources disponibles.', ['moves','games','opening','documents','videos','explanation']],
  engine: ['200 · analyse moteur', 'Un coup et son évaluation Stockfish. Aucun enrichissement documentaire ou vidéo.', ['moves + score','source: stockfish','documents: []','videos: []','explanation: null']],
  unmapped: ['200 · coups théoriques seuls', 'Les coups et parties restent disponibles ; l’ouverture n’a pas de correspondance dans le corpus.', ['moves','games','opening','documents: []','videos: []','explanation: null']],
  finished: ['200 · position terminée', 'Le motif de fin est affiché. Aucun outil externe n’est appelé et aucun coup n’est proposé.', ['game_over: true','termination','moves: []']],
  quota: ['200 · analyse partielle', 'Les coups et ressources sont conservés ; Angular affiche un avertissement à la place de l’explication.', ['moves','games','documents','videos','explanation: null','warnings']],
  ragFailure: ['200 · analyse sans documents', 'Les coups et les vidéos sont conservés ; Angular affiche l’avertissement et aucune explication.', ['moves','games','opening','documents: []','videos','explanation: null','warnings']],
  failure: ['502 / 504 · erreur', 'Angular reçoit un message d’erreur, pas un résultat d’analyse partiel.', ['detail']],
  save: ['201 · sauvegarde confirmée', 'L’identifiant et le résultat enregistré confirment la sauvegarde. Angular recharge ensuite les résumés via GET /api/v1/analyses.', ['id','result']],
  storageFailure: ['503 · sauvegarde non confirmée', 'Angular garde l’analyse à l’écran et affiche l’erreur de stockage.', ['detail']],
  restore: ['200 · sauvegarde retrouvée', 'La FEN et le résultat sont relus tels qu’enregistrés : leur richesse dépend de l’analyse sauvegardée, sans nouveau calcul.', ['_id','fen','created_at','result']]
};
// Une communication par étape : les réponses destinées à Angular arrivent en fin de parcours.
const communications = {
  move: ['chess.js → Angular → Chessground', 'Traitement local · aucun appel HTTP', 'Entrée : déplacement et position courante.', 'Position prête', 'Le coup légal met à jour la FEN et le contexte ; la demande attend la temporisation.', ['fen','base_fen','played_moves']],
  api: ['Angular → FastAPI → LangGraph', 'POST /api/v1/analyses/preview → graph.invoke(état)', 'Corps JSON : fen + base_fen + played_moves.', 'Analyse en cours', 'Pydantic valide la demande ; FastAPI initialise ChessState. Angular attend encore la réponse.', ['ChessState']],
  validate: ['LangGraph → python-chess → ChessState', 'validation → route_after_validation', 'Entrée : fen.', 'État mis à jour', 'Le statut détermine la prochaine branche.', ['game_over','termination']],
  lichess: ['LangGraph ↔ Lichess Explorer', 'GET https://explorer.lichess.org/masters', 'Paramètres : fen, play si historique disponible, moves=3, topGames=2.', 'Réponse au graphe', 'Le service normalise les coups, les parties et le nom d’ouverture.', ['moves','games','opening','source']],
  documents: ['LangGraph → Hugging Face → Milvus → ChessState', 'feature_extraction(question) → client.search(vecteur, filtre)', 'Entrée : question sur l’ouverture reconnue ; vecteur de 1 024 dimensions.', 'Passages retrouvés', 'Jusqu’à trois passages filtrés par ouverture alimentent l’état du graphe.', ['documents']],
  videos: ['LangGraph ↔ YouTube Data API', 'youtube.search().list(part="snippet", type="video")', 'Entrée : nom français de l’ouverture, maxResults=2.', 'Liens reçus par le graphe', 'Le service renvoie les titres, chaînes et URL des vidéos.', ['videos']],
  explain: ['LangGraph ↔ Groq', 'client.chat.completions.create(…) · ou cache mémoire / MongoDB', 'Entrée : position vérifiée, coups candidats, question et passages documentaires numérotés.', 'Explication contrôlée', 'Le JSON et les citations sont vérifiés, puis ajoutés à ChessState ; aucun retour Angular à cette étape.', ['explanation','warnings']],
  quota: ['Groq → service de génération → ChessState', 'HTTP 429 · ou appel évité pendant le cooldown', 'Entrée : demande de génération avec les documents.', 'Avertissement conservé', 'Le graphe garde les données obtenues et termine sans explication.', ['explanation: null','warnings']],
  ragFailure: ['LangGraph → Hugging Face / Milvus → ChessState', 'feature_extraction(question) · ou client.search(…) en échec', 'Entrée : question sur l’ouverture reconnue.', 'Avertissement conservé', 'L’exception est convertie en avertissement ; le graphe poursuit vers les vidéos.', ['documents: []','warnings']],
  engine: ['LangGraph ↔ Stockfish', 'Protocole UCI · analyse locale de la FEN', 'Entrée : position actuelle ; budget moteur de 1 s.', 'Évaluation reçue par le graphe', 'Stockfish fournit un coup et une évaluation, puis le graphe rejoint END.', ['moves + score','source: stockfish']],
  unmapped: ['Nœuds documentaires → ChessState', 'Contrôle local · aucun appel fournisseur', 'Entrée : ouverture sans correspondance dans le corpus.', 'Enrichissement ignoré', 'Les coups déjà reçus sont conservés ; les ressources restent vides.', ['documents: []','videos: []','explanation: null']],
  terminal: ['LangGraph · validation → END', 'Fin locale · aucun appel fournisseur', 'Entrée : game_over=true et motif de fin.', 'État final prêt', 'Le graphe termine ; FastAPI pourra sérialiser cet état à l’étape suivante.', ['game_over: true','termination','moves: []']],
  save: ['Interface Angular → état de sauvegarde', 'Clic sur « Sauvegarder la position »', 'Entrée : analyse actuellement affichée.', 'Demande préparée', 'Le bouton est verrouillé pendant l’enregistrement ; la requête part à l’étape suivante.', ['result']],
  persist: ['Angular → FastAPI', 'POST /api/v1/analyses/save', 'Corps JSON : résultat affiché, dont la FEN.', 'Résultat validé', 'Pydantic contrôle le contenu avant son insertion ; aucun outil d’analyse n’est relancé.', ['result','fen']],
  mongo: ['FastAPI ↔ MongoDB', 'collection.insert_one(document)', 'Document : fen + result + created_at en UTC.', 'Identifiant de stockage', 'L’identifiant de la nouvelle sauvegarde remonte au service ; Angular attend la confirmation.', ['inserted_id']],
  choose: ['Historique Angular → sélection locale', 'Clic sur une position sauvegardée', 'Entrée : résumé sélectionné dans la liste.', 'Identifiant choisi', 'Le détail sera demandé à l’API à l’étape suivante.', ['analysis_id']],
  read: ['Angular → FastAPI ↔ MongoDB', 'GET /api/v1/analyses/{id} → collection.find_one(…)', 'Entrée : identifiant de la sauvegarde.', 'Document retrouvé', 'FastAPI prépare la FEN et le résultat conservés pour leur retour à Angular.', ['fen','created_at','result']]
};
function exchangeFor(mode, id) {
  if (['display','saved','restore','failure','storageFailure'].includes(id)) {
    const [status, output, fields] = exchanges[mode];
    return ['FastAPI → Angular', status,
      mode === 'restore' ? 'Réponse au GET /api/v1/analyses/{id}.' : ['save','storageFailure'].includes(mode) ? 'Réponse au POST /api/v1/analyses/save.' : 'Réponse au POST /api/v1/analyses/preview.',
      id === 'saved' ? 'Confirmation puis GET /api/v1/analyses' : 'Réception dans l’interface', output, fields];
  }
  const data = [...communications[id]];
  if (id === 'lichess' && mode === 'engine') {
    data[3] = 'Aucun coup retourné'; data[4] = 'Une réponse valide mais vide oriente le graphe vers Stockfish.'; data[5] = ['moves: []'];
  } else if (id === 'lichess' && mode === 'failure') {
    data[3] = 'Échec du fournisseur'; data[4] = 'Erreur réseau ou délai dépassé : le graphe s’interrompt. FastAPI traduira l’exception à l’étape suivante.'; data[5] = ['exception'];
  } else if (id === 'validate') {
    data[4] = mode === 'finished' ? 'Position terminée : game_over=true, motif renseigné ; prochaine destination END.' : 'Position en cours : game_over=false ; prochaine destination fetch.';
  } else if (id === 'mongo' && mode === 'storageFailure') {
    data[3] = 'Erreur de connexion'; data[4] = 'Le stockage lève une exception. Aucune confirmation de sauvegarde n’est disponible.'; data[5] = ['exception'];
  }
  return data;
}
function renderExchange(mode, id) {
  const data = exchangeFor(mode,id);
  ['exchange-direction','http-route','http-input','http-status','http-output'].forEach((key,index) => document.getElementById(key).textContent = data[index]);
  document.getElementById('response-fields').replaceChildren(...data[5].map(field => {
    const chip = document.createElement('code'); chip.textContent = field; return chip;
  }));
}
const scenario = document.querySelector('#scenario');
const flow = document.querySelector('#flow');
const previous = document.querySelector('#previous');
const next = document.querySelector('#next');
let current = 0;
function render() {
  const path = paths[scenario.value];
  renderExchange(scenario.value, path[current]);
  flow.replaceChildren(...path.map((id, index) => {
    const li = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    const number = document.createElement('span');
    number.textContent = `${index + 1} · ${steps[id][0]}`;
    button.append(number, document.createTextNode(steps[id][1]));
    if (index === current) button.setAttribute('aria-current', 'step');
    button.addEventListener('click', () => { current = index; render(); flow.children[index].firstChild.focus(); });
    li.append(button); return li;
  }));
  const id = path[current];
  const step = [...steps[id]];
  const communication = exchangeFor(scenario.value,id);
  // Même scénario et même étape pour le schéma, le contrat et l’explication.
  if (['display','saved','restore','failure','storageFailure'].includes(id)) {
    step[2] = `${communication[4]} ${steps[id][2]}`;
  } else if (['validate','lichess','mongo'].includes(id)) {
    step[2] = `${communication[4]} ${steps[id][2]}`;
  }
  step[3] = communication[1];
  const [modules, edges, transfer] = activity[id];
  document.querySelectorAll('[data-module]').forEach(node => node.classList.toggle('active', modules.split(' ').includes(node.dataset.module)));
  const returning = ['display','saved','failure','storageFailure'].includes(id);
  document.querySelectorAll('[data-edge]').forEach(node => {
    node.classList.toggle('active', edges.split(' ').includes(node.dataset.edge));
    node.classList.toggle('returning', returning);
    node.setAttribute('marker-start', returning ? 'url(#arrow)' : 'none');
    node.setAttribute('marker-end', returning ? 'none' : 'url(#arrow)');
  });
  document.getElementById('transfer').textContent = transfer;
  document.getElementById('guard').textContent = safeguards[id][0];
  document.getElementById('timing').textContent = safeguards[id][1];
  ['layer','step-title','step-description','contract'].forEach((id, index) => document.getElementById(id).textContent = step[index]);
  document.getElementById('progress').textContent = `Étape ${current + 1} / ${path.length}`;
  previous.disabled = current === 0;
  next.disabled = current === path.length - 1;
}
scenario.addEventListener('change', () => { current = 0; render(); });
previous.addEventListener('click', () => { if (current > 0) { current--; render(); } });
next.addEventListener('click', () => { if (current < paths[scenario.value].length - 1) { current++; render(); } });
render();

const graphRoutes = {
  enriched: ['start','validation','fetch','documents','videos','explanation','end'],
  motor: ['start','validation','fetch','stockfish','end'],
  terminal: ['start','validation','end']
};
// Fixtures illustratives : les valeurs ne proviennent pas d’une analyse en direct.
function graphSnapshot(mode, target) {
  const state = {
    fen: mode === 'terminal' ? '8/8/8/8/8/2k5/8/K7 w - - 0 1' : 'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3',
    base_fen: null, played_moves: [], game_over: false, termination: null,
    moves: [], games: [], source: null, opening: null, documents: [], videos: [],
    explanation: null, warnings: []
  };
  const patches = {
    validation: {game_over: mode === 'terminal', termination: mode === 'terminal' ? 'INSUFFICIENT_MATERIAL' : null},
    fetch: mode === 'motor' ? {moves: [], games: [], source: 'lichess', opening: null} : {
      moves: [{uci:'b1c3',san:'Nc3'}], games: [{id:'exemple',white:{name:'Blancs'},black:{name:'Noirs'}}],
      source:'lichess', opening:{name:'French Defense',eco:'C00'}
    },
    documents: {documents:[{id:'exemple-1',title:'Défense française',text:'Les Noirs attaquent le centre.'}]},
    videos: {videos:[{title:'Exemple de vidéo sur la défense française',url:'https://www.youtube.com/watch?v=exemple'}]},
    explanation: {explanation:{claims:[{claim:'Les Noirs attaquent le centre.',source_id:1,evidence:'Les Noirs attaquent le centre.'}],limitation:'none'},warnings:[]},
    stockfish: {moves:[{uci:'b1c3',san:'Nc3',score_cp:25,mate:null}],games:[],source:'stockfish'}
  };
  let written = [], changed = [];
  for (const node of graphRoutes[mode]) {
    const patch = patches[node] || {};
    written = Object.keys(patch);
    changed = written.filter(key => JSON.stringify(state[key]) !== JSON.stringify(patch[key]));
    Object.assign(state, patch);
    if (node === target) break;
  }
  return {state,written,changed};
}
const graphRoute = document.getElementById('graph-route');
let stateNode = 'start';
function renderGraph() {
  const route = graphRoutes[graphRoute.value];
  const position = route.indexOf(stateNode);
  document.querySelectorAll('[data-lg-node]').forEach(node => {
    node.disabled = !route.includes(node.dataset.lgNode);
    node.classList.toggle('on-route', route.includes(node.dataset.lgNode));
    node.setAttribute('aria-pressed', String(node.dataset.lgNode === stateNode));
  });
  const links = route.slice(1, position + 1).map((node, i) => `${route[i]}-${node}`);
  document.querySelectorAll('[data-lg-edge]').forEach(edge => edge.classList.toggle('on-route', links.includes(edge.dataset.lgEdge)));
  const {state,written,changed} = graphSnapshot(graphRoute.value,stateNode);
  document.getElementById('state-at').textContent = stateNode === 'start' ? '· état initial' : `· après ${stateNode}`;
  document.getElementById('state-update').textContent = stateNode === 'start' ? 'Entrées reçues ; résultats initialisés à vide.' : written.length ? `Champs écrits : ${written.join(', ')}. Vert : valeur modifiée ; bleu : valeur réécrite à l’identique.` : 'État final conservé : aucun champ supplémentaire.';
  document.getElementById('state-values').replaceChildren(...Object.entries(state).map(([key,value]) => {
    const row = document.createElement('div');
    row.className = changed.includes(key) ? 'state-field changed' : written.includes(key) ? 'state-field written' : 'state-field';
    const label = document.createElement('code'); label.textContent = key;
    const data = document.createElement('code'); data.textContent = JSON.stringify(value);
    row.append(label,data); return row;
  }));
}
graphRoute.addEventListener('change', () => {stateNode = 'start'; renderGraph();});
document.querySelectorAll('[data-lg-node]').forEach(node => {
  const inspect = () => {
    if (!node.disabled && stateNode !== node.dataset.lgNode) {stateNode = node.dataset.lgNode; renderGraph();}
  };
  node.addEventListener('mouseenter',inspect);
  node.addEventListener('focus',inspect);
  node.addEventListener('click',inspect);
});
renderGraph();

// Explorateurs documentaires : données descriptives, sans accès réseau.
const ragSteps = {
  collect: ['Collecter', 'commands/ · collecte Wikipédia', 'Conserver le texte et sa provenance', 'Les articles sont extraits en blocs structurés : paragraphes, listes et sections. Les liens des sources accompagnent les textes.', 'Articles Wikipédia sur les ouvertures', 'Texte, titre, URL et chemin de section', 'Le lot actuel contient 30 articles. Les révisions exactes de la collecte initiale ne sont pas conservées.'],
  chunk: ['Découper', 'services/chunking_service.py', 'Créer des passages cohérents', 'Les petits blocs contigus sont regroupés sans franchir les limites de section. Les blocs trop longs sont découpés ; le titre et la section enrichissent le texte à encoder.', 'Blocs structurés d’un article', 'Passages identifiés ; cible maximale de 1 500 caractères', 'Chevauchement de 150 caractères pour les blocs découpés. Un passage court isolé reste conservé.'],
  embed: ['Vectoriser', 'commands/ · préparation du corpus', 'Encoder les passages', 'Qwen3-Embedding-0.6B transforme chaque passage en vecteur. Le même modèle et la même dimension doivent être utilisés pour les questions à la recherche.', 'Titre + section + texte du passage', 'Un vecteur de 1 024 dimensions par passage', 'Le lot versionné contient déjà 339 passages et leurs vecteurs : aucun recalcul n’est requis pour son import.'],
  index: ['Indexer', 'commands/index_milvus.py', 'Charger les données dans Milvus', 'Le lot est vérifié puis importé par upsert : les identifiants stables permettent de relancer un import. Les textes et métadonnées restent associés aux vecteurs.', 'Archive du corpus + empreinte SHA-256', 'Collection Milvus prête pour la recherche', 'L’import valide le schéma. Il ne supprime pas les autres entrées d’une collection existante.'],
  opening: ['Identifier', 'services/opening_service.py', 'Relier l’ouverture au corpus', 'Le nom renvoyé par Lichess est rapproché d’un titre documentaire. Le graphe construit une question sur les principes et plans de cette ouverture.', 'ChessState.opening', 'Titre couvert + question en français', 'La position FEN ne devient pas directement une requête vectorielle : le point de départ documentaire est le nom d’ouverture.'],
  question: ['Encoder', 'services/embedding_service.py', 'Transformer la question en vecteur', 'Le service distant Hugging Face / DeepInfra encode la question avec Qwen3-Embedding-0.6B et le préfixe de requête prévu par le projet.', 'Question sur les principes et plans', 'Vecteur de recherche de 1 024 dimensions', 'Cette étape a lieu pendant l’analyse, contrairement à l’encodage préalable des documents.'],
  retrieve: ['Rechercher', 'services/vector_search_service.py', 'Retrouver trois passages', 'Milvus classe les passages par similarité cosinus, avec un filtre sur le titre exact de l’ouverture. Il renvoie le texte et sa provenance.', 'Vecteur + filtre opening_title + limit=3', 'documents : texte, source_url, section_path, score et identifiant', 'Le filtre limite les mélanges entre ouvertures ; il ne garantit pas que tous les passages soient pertinents pour la variante jouée.'],
  generate: ['Générer', 'services/generation_service.py', 'Produire une explication sourcée', 'Groq reçoit la position vérifiée, les coups candidats et les extraits numérotés. Il synthétise les principes pertinents ; les références restent visibles, les citations servent au contrôle interne.', 'Position + coups candidats + question + documents récupérés', 'Explication et références ; preuves contrôlées côté serveur', 'Sans documents, le service s’abstient. Un cache peut réutiliser un succès pour une position, une question et des documents identiques.'],
  verify: ['Contrôler', 'Génération → ChessState → réponse API', 'Vérifier avant de restituer', 'Le code contrôle le format JSON, les références et la présence exacte des citations dans les passages. Le graphe conserve l’explication validée ou un avertissement en cas d’échec de génération.', 'Réponse structurée du modèle', 'explanation et warnings, avec les documents sources', 'Un extrait exact ne prouve pas à lui seul que la reformulation est juste : cette qualité reste à mesurer.'],
  absent: ['S’abstenir', 'Nœuds documents · videos · explanation', 'Ne pas inventer de contexte', 'Sans correspondance documentaire, ces nœuds ne lancent pas les recherches d’enrichissement. Les coups Lichess déjà obtenus restent dans le résultat.', 'Ouverture non couverte par la correspondance', 'documents=[] ; videos=[] ; explanation=null', 'Cette branche reste distincte de celle de Stockfish, déclenchée quand Lichess ne renvoie aucun coup.']
};
const ragPaths = {prepare:['collect','chunk','embed','index'],query:['opening','question','retrieve','generate','verify'],missing:['opening','absent']};
const ragMode = document.getElementById('rag-mode');
let ragCurrent = 0;
function renderRag() {
  const route = ragPaths[ragMode.value];
  document.getElementById('rag-flow').replaceChildren(...route.map((id,index) => {
    const li = document.createElement('li'), button = document.createElement('button');
    button.type = 'button'; button.textContent = `${index+1} · ${ragSteps[id][0]}`;
    button.setAttribute('aria-pressed',String(index===ragCurrent));
    button.addEventListener('click',()=>{ragCurrent=index;renderRag();document.getElementById('rag-flow').children[index].firstChild.focus();});
    li.append(button); return li;
  }));
  const data = [...ragSteps[route[ragCurrent]]];
  if(ragMode.value==='missing' && ragCurrent===0){data[3]='Le nom d’ouverture ne correspond à aucun titre du corpus configuré. Le graphe conserve les données de jeu, mais ne construit pas de contexte documentaire.';data[5]='Aucun titre documentaire couvert';}
  ['rag-location','rag-title','rag-description','rag-input','rag-output','rag-check'].forEach((id,index)=>document.getElementById(id).textContent=data[index+1]);
}
ragMode.addEventListener('change',()=>{ragCurrent=0;renderRag();});renderRag();
const deployments = {
  local: {
    overview:'Réseau Docker Compose : le navigateur entre par Nginx sur localhost:4200. Les noms de services servent d’adresses entre conteneurs.',
    nodes:[
      ['frontend','Navigateur → frontend:80','localhost:4200 → Nginx → /api/','frontend/Dockerfile · nginx.conf','Servir Angular et relayer l’API','Nginx sert les fichiers statiques du frontend et relaie /api/ vers le conteneur API. Le navigateur ne résout pas les noms internes Docker.','Hôte 4200 → conteneur 80 ; proxy HTTP → api:8080','Build Angular dans l’image frontend ; aucun stockage des analyses.'],
      ['api','Nginx → api:8080','FastAPI · LangGraph · Stockfish','Dockerfile · compose.yaml','Exécuter le parcours d’analyse','Le conteneur Python héberge l’API et lance Stockfish comme processus local. Il contacte les bases sur le réseau Compose et les fournisseurs externes par HTTPS.','MongoDB : mongodb:27017 ; Milvus : standalone:19530 ; fournisseurs : HTTPS','L’API attend MongoDB sain au démarrage. Le port API est aussi publié sur 127.0.0.1:${APP_PORT}.'],
      ['mongo','api → mongodb:27017','Positions et analyses sauvegardées','compose.yaml · service mongodb','Persister les sauvegardes','MongoDB 7 conserve les documents de sauvegarde ; ce stockage est indépendant du corpus vectoriel.','Protocole MongoDB depuis api ; port hôte 27017 lié à 127.0.0.1','Volume nommé mongodb_data → /data/db.'],
      ['milvus','api → standalone:19530','Recherche vectorielle','compose.yaml · service standalone','Interroger le corpus','Milvus reçoit les vecteurs de question et retourne les passages similaires. Le service dépend d’etcd et de MinIO.','Milvus → etcd:2379 ; Milvus → minio:9000 ; santé sur :9091','Volume local volumes/milvus ; import du corpus par le service ponctuel corpus-init.'],
      ['etcd','standalone → etcd:2379','Métadonnées Milvus','compose.yaml · service etcd','Conserver les métadonnées de Milvus','etcd sert au fonctionnement interne de Milvus. Angular et FastAPI ne lui envoient aucune requête métier directe.','Réseau Compose uniquement ; client Milvus → port 2379','Répertoire local volumes/etcd → /etcd.'],
      ['minio','standalone → minio:9000','Stockage objet Milvus','compose.yaml · service minio','Conserver les objets de Milvus','MinIO fournit le stockage objet utilisé par Milvus ; les sauvegardes utilisateur restent dans MongoDB.','Milvus → port 9000 ; console locale :9001','Répertoire local volumes/minio → /minio_data.'],
      ['external','api → services externes','Lichess · HF · YouTube · Groq','services/ · adaptateurs fournisseurs','Appeler les fournisseurs','Même en local, l’exploration, l’encodage de question, la recherche vidéo et la génération utilisent les services distants configurés.','HTTPS sortant depuis api ; Stockfish reste local au conteneur','Clés injectées côté serveur ; quotas et disponibilité restent ceux des fournisseurs.']
    ]
  },
  cloud: {
    overview:'Render exécute une seule image : FastAPI sert l’API et le build Angular sur le même port. Les bases sont externes ; Compose, Nginx, etcd et MinIO ne sont pas déployés dans ce conteneur.',
    nodes:[
      ['render','Navigateur → Render → conteneur','HTTPS public → Uvicorn sur $PORT','Dockerfile.cloud · backend/app/cloud.py','Servir le frontend et l’API ensemble','Render reçoit le trafic public. Uvicorn exécute FastAPI ; les routes API sont enregistrées avant le montage des fichiers Angular.','/api/v1/* → FastAPI ; / → fichiers statiques ; un seul port d’écoute','Build Angular copié dans /app/static ; pas de volume de base de données local.'],
      ['engine','FastAPI → Stockfish','Processus dans le même conteneur','Dockerfile.cloud · stockfish_service.py','Évaluer sans service Docker séparé','Le binaire Stockfish est installé dans l’image Python et lancé par le service moteur quand le graphe choisit cette branche.','Communication locale UCI ; aucun port réseau Stockfish','Processus moteur temporaire ; aucun stockage persistant des évaluations.'],
      ['mongo','FastAPI → MongoDB Atlas','Stockage géré distant','render.yaml · HISTORY_BACKEND=mongodb','Conserver les sauvegardes hors Render','L’API utilise l’URI MongoDB injectée dans son environnement. Les données restent dans le service de base de données lors d’un redémarrage du conteneur.','Connexion MongoDB distante via MONGODB_URI','Persistance assurée par MongoDB Atlas, séparée du disque du conteneur.'],
      ['milvus','FastAPI → Zilliz / Milvus','Corpus vectoriel distant','MILVUS_URI · MILVUS_TOKEN','Rechercher dans la collection distante','Le même adaptateur Milvus contacte la collection configurée dans le cloud. Le corpus doit être importé dans cette collection avant les recherches.','Client Milvus → URI distante configurée','Données conservées par le service géré ; les dépendances internes etcd/MinIO ne sont pas des conteneurs Render du projet.'],
      ['external','FastAPI → services externes','Lichess · HF · YouTube · Groq','render.yaml · variables serveur','Enrichir avec les mêmes fournisseurs','Les appels passent depuis le backend vers les fournisseurs, comme en local. Les adresses des bases et les clés ne sont pas livrées à Angular.','HTTPS sortant ; retours intégrés à ChessState','Cache de génération en mémoire du processus, perdu au redémarrage.']
    ]
  }
};
const dockerMode=document.getElementById('docker-mode');let dockerCurrent=0;
function renderDocker(){
  const config=deployments[dockerMode.value];
  document.querySelectorAll('[data-topology]').forEach(figure=>{figure.hidden=figure.dataset.topology!==dockerMode.value;});
  document.getElementById('docker-overview').textContent=config.overview;
  document.getElementById('docker-map').replaceChildren(...config.nodes.map((node,index)=>{
    const button=document.createElement('button');button.type='button';button.setAttribute('aria-pressed',String(index===dockerCurrent));
    const title=document.createElement('strong'), subtitle=document.createElement('span');title.textContent=node[1];subtitle.textContent=node[2];button.append(title,subtitle);
    button.addEventListener('click',()=>{dockerCurrent=index;renderDocker();document.getElementById('docker-map').children[index].focus();});return button;
  }));
  const node=config.nodes[dockerCurrent];['docker-location','docker-title','docker-description','docker-links','docker-storage'].forEach((id,index)=>document.getElementById(id).textContent=node[index+3]);
}
dockerMode.addEventListener('change',()=>{dockerCurrent=0;renderDocker();});renderDocker();
