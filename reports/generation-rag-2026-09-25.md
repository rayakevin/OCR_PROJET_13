# Évaluation de la génération RAG — 25 septembre 2026

## Objet

Choisir une configuration qui explique les ouvertures à partir du corpus, sans
inventer de plans ni transformer une variante particulière en règle générale.
L'évaluation porte sur des questions documentaires générales, pas sur le meilleur
coup d'une position FEN.

## Recommandation pour le prototype

**Je retiendrais Qwen 3.8 27B sur Groq, en génération courte avec preuves**, pour
privilégier la fidélité documentaire dans notre prototype. C'est le meilleur
compromis qualitatif observé ici, pas un optimum démontré pour toute question.
GPT-OSS 20B reste nettement plus économique et rapide ; son profil court est une
alternative si le coût et le débit deviennent prioritaires.

| Réglage | Valeur retenue pour les essais courts |
| --- | --- |
| Modèle | `qwen/qwen3.8-27b` |
| Température | `0.1` |
| Raisonnement | `low` |
| Plafond de sortie, raisonnement compris | `950` tokens |
| Réponse | JSON strict, au maximum **2 affirmations** |
| Preuve | Citation exacte et numéro de source pour chaque affirmation |
| Contexte | Jusqu'à 3 passages, titre et chemin de section conservés |
| Information absente | Réponse partielle ou abstention explicite |
| Contrôle local | Format, source, copie de la preuve, sortie complète |

Le rendu doit conserver les références et les sections. Il ne faut pas demander
ensuite à un autre modèle de réécrire librement la réponse contrôlée : cela
introduirait une nouvelle génération non évaluée. Une preuve introuvable est
rejetée ; si aucune affirmation ne reste, afficher l'insuffisance du contexte.
Le contrôle textuel **ne valide pas à lui seul le sens de la reformulation**.

Pour une restitution plus prudente, on peut afficher directement les extraits
avec leurs sections. Pour expliquer un coup dans une FEN donnée, cette fiche
documentaire devra être séparée de l'analyse de position et de la légalité des coups.

## Résultats comparables sur les ouvertures

Les deux profils courts utilisent **exactement le même prompt**, la même
température, les mêmes documents et le même plafond de sortie. Les profils longs
ci-dessous autorisent jusqu'à quatre affirmations avec raisonnement `medium` :
leur comparaison ne permet pas d'isoler l'effet de la taille du modèle.

Le texte libre de départ a également été essayé sur la Française et la
Sicilienne, avec les deux GPT : seulement deux ouvertures par modèle. Ces quatre
essais exploratoires ne servent pas à calculer un taux de réussite global.

| Profil | Ouvertures testées | Réponses non vides après contrôle textuel | Réponses entièrement conformes aux contrôles textuels | Latence médiane de génération |
| --- | ---: | ---: | ---: | ---: |
| GPT-OSS 20B, jusqu'à 4 faits | 30 | 25 | 22 | 2,20 s |
| GPT-OSS 120B, jusqu'à 4 faits | 30 | 29 | 21 | 3,08 s |
| GPT-OSS 20B, jusqu'à 2 faits | 30 | 30 | 27 | 0,72 s |
| Qwen 3.8 27B, jusqu'à 2 faits, première tentative | 30 | 29 | 28 | 1,68 s |
| Qwen 3.8 27B, jusqu'à 2 faits, avec un réessai | 30 | 30 | 29 | 1,71 s |

Une réponse vide peut réussir les contrôles textuels : la colonne « conforme »
ne mesure donc ni la couverture ni la fidélité sémantique. Qwen a rencontré un
HTTP 400 sur la Catalane, conservé séparément dans les résultats bruts.
**Un seul réessai, avec les mêmes paramètres, a réussi.** Sa définition de la
Catalane et le jugement attribué aux auteurs sont fidèles au document. La cause
du premier HTTP 400 n'a pas été établie ; on ne le masque pas dans le bilan.

### Relecture qualitative des profils courts

Après les contrôles Python, j'ai relu toutes les réponses disponibles contre les
documents complets : **30 pour chaque profil**, avec le réessai Qwen identifié.

- **GPT-OSS 20B : 6 affirmations à corriger dans 5 réponses.** Notamment : plans
  de la Moderne sans préciser `4.Fe3`, portée ambiguë sur le gambit dame accepté,
  branche du gambit du roi omise, numérotation altérée dans la Catalane et pion
  qui se soutient lui-même dans l'Espagnole.
- **Qwen : 3 affirmations à corriger dans 3 réponses.** Il omet `3.Cc3` pour
  expliquer le blocage du pion c dans la Scandinave ; il omet l'attribution à
  Reuben Fine dans l'Espagnole ; il fusionne deux sources du gambit Göring en
  n'en citant qu'une dans l'Écossaise.
- Aucune autre alerte de ce type n'a été repérée dans **25/30** réponses GPT et
  **27/30** réponses Qwen après le réessai. **Ce n'est pas une
  précision certifiée** : une relecture indépendante pourrait trouver d'autres erreurs.
- Qwen signale une limitation documentaire dans **13/30** réponses, contre
  **0/30** pour GPT. Cela correspond notamment aux contextes contenant surtout
  une définition ou une liste de variantes. Ce champ reste lui-même à contrôler.

Les preuves textuelles éliminent trois affirmations GPT et une affirmation Qwen
avant cette relecture. Le JSON strict évite des erreurs de format ; il n'empêche
pas les erreurs de sens ci-dessus. Une preuve peut aussi être trop courte pour
justifier seule toute la phrase, même si le document complet contient l'information.

### Coût et choix pratique

Aux tarifs catalogue, en comptant les tokens effectivement retournés sur les
ouvertures, les essais courts représentent environ **0,0053 USD pour 30 réponses
GPT** et **0,1085 USD pour 30 réponses Qwen** après le réessai. C'est environ **21 fois plus cher
par réponse** pour Qwen sur cet échantillon. Ces montants sont des estimations
hors quota gratuit, sans cache ni coût des erreurs non renseigné, **pas une
facture ni une dépense constatée**. Les prix de référence sont ceux des pages
[GPT-OSS 20B](https://console.groq.com/docs/model/openai/gpt-oss-20b) et
[Qwen 3.8 27B](https://console.groq.com/docs/model/qwen/qwen3.8-27b).

Pour notre usage occasionnel de prototype, je privilégie Qwen et sa prudence
supplémentaire. Pour du volume, le gain qualitatif observé ne justifie pas
automatiquement ce surcoût : GPT court ou restitution directe des passages sont
à considérer. Qwen est aussi présenté comme un modèle en preview par Groq.

### Cas limites des profils courts

| Cas | Résultat observé pour les deux profils |
| --- | --- |
| Liste de variantes sans plans expliqués | Aucune affirmation ; limite documentaire signalée |
| Taux de victoire 2025 absent du contexte | Abstention, aucun taux inventé |
| Contexte vide | Aucun appel au modèle |
| Instruction parasite dans un document | Instruction ignorée dans ces deux essais |

Dans le dernier cas, GPT reprend aussi une phrase marquée `[Quoi ?]`, que Python
rejette ; Qwen l'évite. Un seul exemple d'instruction parasite ne constitue pas
un audit de résistance aux injections de prompt.

## Protocole

- Corpus français existant : **30 ouvertures, 339 chunks, vecteurs de 1 024 dimensions**.
- Une question par ouverture : « Quels sont les principes et les plans de … ? ».
- Trois passages au maximum, avec filtre exact sur le titre de l'ouverture :
  **89 chunks distincts** présentés au total, soit environ 26 % des chunks du corpus.
- Classement cosine exact sur les vecteurs existants, sans appel Milvus. Le modèle
  d'embedding et sa révision sont ceux du manifeste. Une seconde préparation avec
  cette révision fixée reproduit les 30 classements et leurs scores à l'identique.
- Les modèles reçoivent les mêmes textes, titres, sections et liens. Les jeux de
  documents sont figés dans `data/generation_evaluation/cases.json`.
- Quatre cas supplémentaires : liste de variantes sans plans, statistique absente,
  contexte vide, instruction parasite ajoutée à une source.
- Température principale : **0,1**. Les réglages de raisonnement et de longueur
  sont enregistrés avec chaque réponse.
- Les pauses imposées par les quotas sont exclues des latences d'appel indiquées.

Les premières consignes ont été mises au point sur la Française et la Sicilienne.
Les 28 autres ouvertures n'avaient pas servi à ajuster ce premier prompt. Les
expériences suivantes sont exploratoires : elles s'appuient sur les défauts
observés et ne constituent donc pas un second test indépendant à l'aveugle.

## Ce que mesurent les contrôles

Le contrôle Python vérifie le format, les numéros des sources, la présence des
citations dans le texte, certaines notations anglaises et les marqueurs éditoriaux
d'incertitude. Il tolère les différences typographiques, sans supprimer de mots.
Il rejette aussi les réponses interrompues et les citations trop courtes.

**Une citation authentique ne prouve pas que la reformulation en découle.** Il
faut encore vérifier le camp, la pièce, les conditions, la variante et les nuances.
Une relecture qualitative par l'assistant complète les contrôles. Ce n'est pas
une annotation indépendante par un expert humain ni une validation de la vérité
échiquéenne de Wikipédia.

Les fichiers `audit_qualitatif.json`, les réponses brutes et les raisons de rejet
permettent de revoir les constats. L'échantillon d'erreurs ciblées n'est pas une
mesure représentative de la précision globale.
`audit_final.json` contient la relecture complète des deux profils courts ;
`final_metrics_with_retry.json` en agrège les résultats. Les nombres précédents
s'appuient sur cette relecture, pas sur le juge LLM abandonné.

## Constats établis

### Le format seul ne suffit pas

GPT-OSS 20B et 120B produisent des JSON exploitables, mais certaines reformulations
restent incorrectes. Exemples observés :

- un commentaire sur la fin d'une partie Réti devient une propriété de l'ouverture ;
- des plans de la variante d'avance sont présentés comme ceux de toute la Française ;
- dans le gambit dame refusé, le 120B remplace le fou dame bloqué par le fou roi ;
- certaines preuves sont recomposées au lieu d'être citées exactement ;
- deux réponses du 120B passent en anglais malgré un contexte français.

L'ajout explicite d'une consigne de français a corrigé la langue dans les deux
cas réessayés. Cela ne suffit pas à garantir la fidélité du contenu.

### La seconde lecture par GPT-OSS 120B n'est pas retenue

Cette expérience a été arrêtée après **8 ouvertures** : parmi **9 erreurs ciblées**
déjà identifiées dans ces cas, le relecteur n'en a rejeté **aucune**. Il a notamment
accepté des affirmations attribuées à une source qui ne contenait pas l'idée.
Les contrôles de copie en éliminent certaines, mais le juge LLM ne constitue pas
une protection sémantique suffisante dans ce protocole.

Ce résultat concerne ce modèle, ce prompt et cet échantillon ; il ne démontre pas
que toute méthode de vérification par LLM serait inutile. Ici, elle ajoute du
temps et des tokens sans bénéfice suffisant pour la recommander.

### Une température nulle ne règle pas la fidélité

Un réessai ciblé à température zéro sur la Française a encore produit une preuve
réécrite et perdu le qualificatif « souvent ». Un premier HTTP 400 n'a pas été
reproduit au réessai. Ce test ponctuel ne permet pas de classer statistiquement
0 et 0,1 ; il montre seulement que zéro n'est pas une garantie d'exactitude.

### Une restitution sans réécriture reste une solution de repli

Un autre profil demande au modèle de choisir des numéros de passages ; Python
recopie ensuite les textes sources avec leurs sections. Sur les **18 ouvertures
essayées**, il a conservé au moins un passage dans **14 cas**. Cette expérience
a été arrêtée pour concentrer les essais sur la génération courte.

Ce mode ne peut pas inventer une nouvelle phrase, puisque le texte est recopié
depuis les documents. Il peut toutefois choisir un passage peu pertinent ou
reproduire une erreur de Wikipédia. La réponse est aussi plus longue et moins
synthétique. C'est un repli documentaire possible, pas une preuve de réussite
de la génération ni une mesure de précision sur les 30 ouvertures.

### La qualité documentaire compte

Les résultats récupérés mélangent parfois idées générales, listes de coups,
histoire et parties complètes. Une question sur les plans ne peut pas toujours
recevoir une explication stratégique à partir de ces trois passages.

Un diagnostic de filtrage a changé les contextes de 11 ouvertures en excluant les
sections d'exemples et d'histoire. Ce filtre trop large fait aussi perdre des
explications utiles, notamment dans l'historique de Philidor et de la Viennoise.
Il n'a pas été testé en génération : ce n'est pas un gain de qualité démontré.

Pour la suite, privilégier les passages de principes et de plans, pénaliser les
parties d'exemple pour ces questions, et conserver les conditions des variantes.
Ne pas supprimer aveuglément toute section historique.

## Modèles et contraintes du compte

Llama 3.3 70B est documenté par Groq mais n'était pas accessible sur ce compte
(HTTP 404). Il n'a donc pas été évalué qualitativement.

Qwen 3.8 27B est accessible, mais la limite effective observée est de **1 000
tokens de sortie par minute**. Les tokens de raisonnement comptent dans cette
contrainte. Un refus indiquait une sortie attendue de 1 748 tokens : attendre
davantage ne pouvait pas faire passer cette requête trop grande.

Les limites réelles du compte peuvent différer du tableau public. Le banc d'essai
conserve séparément erreurs techniques, abstentions et réponses exploitables.

Références : [limites Groq](https://console.groq.com/docs/rate-limits),
[sorties structurées](https://console.groq.com/docs/structured-outputs),
[GPT-OSS 20B](https://console.groq.com/docs/model/openai/gpt-oss-20b),
[GPT-OSS 120B](https://console.groq.com/docs/model/openai/gpt-oss-120b),
[Qwen 3.8 27B](https://console.groq.com/docs/model/qwen/qwen3.8-27b).

## Reproduire et inspecter

Le banc d'essai est `backend/app/commands/evaluate_generation.py`. Il réutilise les
résultats d'une campagne identique et refuse d'écraser une réponse provenant de
paramètres différents. Les données et résultats volumineux restent ignorés par Git.

```bash
# Statistiques et restitutions lisibles, sans réseau.
uv run python -m backend.app.commands.evaluate_generation summarize

# Nouvelle campagne isolée : préparation sur le modèle local, avec CUDA.
uv run python -m backend.app.commands.evaluate_generation --output data/nouvelle_campagne prepare
```

Les appels de génération consomment le quota Groq. Les contextes figés permettent
de comparer la génération sans reconstruire l'image Docker, recalculer les
embeddings ni modifier la collection Milvus.

La restitution annotée des 30 réponses Qwen est disponible localement dans
`data/generation_evaluation/responses_qwen_low_with_retry.md`. Les erreurs
repérées y sont signalées, sans réécrire les réponses brutes. Les contrôles ont
été vérifiés par **11 tests locaux sans réseau**, et le module d'évaluation
compile correctement. Les scripts de test restent ignorés par Git.

Les profils et contrôles sont disponibles dans le banc d'essai. Leur intégration
dans un service de génération puis dans le graphe constitue l'étape suivante.

## Limites de portée

Une question par ouverture et une réponse par configuration ne suffisent pas à
mesurer la variabilité, toutes les variantes, ni toutes les formulations possibles.
Les erreurs du corpus peuvent être reproduites fidèlement. Aucun modèle testé
n'est certifié exact aux échecs par cette campagne. Les latences excluent
l'encodage de la question, Milvus et les démarrages à froid de l'API.

Les sorties structurées facilitent les contrôles ; elles ne garantissent pas la
vérité. Pour un futur coach lié à une FEN, les affirmations sur la position et les
coups devront aussi être confrontées aux données de python-chess et Stockfish.
