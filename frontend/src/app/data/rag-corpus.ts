/**
 * Les 30 ouvertures dont l’article Wikipédia est indexé dans le corpus du RAG.
 *
 * Chaque séquence a été vérifiée contre l’explorateur Lichess masters : le nom
 * d’ouverture renvoyé correspond au titre du corpus (backend opening_service).
 */
export interface CorpusOpening {
  title: string;
  /** Coups caractéristiques en notation SAN, depuis la position initiale. */
  moves: string[];
}

export const ragCorpusOpenings: CorpusOpening[] = [
  { title: 'Début Réti', moves: ['Nf3', 'd5', 'c4'] },
  { title: 'Défense Alekhine', moves: ['e4', 'Nf6'] },
  { title: 'Défense Benoni', moves: ['d4', 'Nf6', 'c4', 'c5', 'd5', 'e6'] },
  { title: 'Défense Caro-Kann', moves: ['e4', 'c6'] },
  { title: 'Défense est-indienne', moves: ['d4', 'Nf6', 'c4', 'g6', 'Nc3', 'Bg7', 'e4', 'd6'] },
  { title: 'Défense française', moves: ['e4', 'e6'] },
  { title: 'Défense Grünfeld', moves: ['d4', 'Nf6', 'c4', 'g6', 'Nc3', 'd5'] },
  { title: 'Défense hollandaise', moves: ['d4', 'f5'] },
  { title: 'Défense moderne', moves: ['e4', 'g6'] },
  { title: 'Défense nimzo-indienne', moves: ['d4', 'Nf6', 'c4', 'e6', 'Nc3', 'Bb4'] },
  { title: 'Défense ouest-indienne', moves: ['d4', 'Nf6', 'c4', 'e6', 'Nf3', 'b6'] },
  { title: 'Défense Philidor', moves: ['e4', 'e5', 'Nf3', 'd6'] },
  { title: 'Défense Pirc', moves: ['e4', 'd6', 'd4', 'Nf6', 'Nc3', 'g6'] },
  { title: 'Défense russe', moves: ['e4', 'e5', 'Nf3', 'Nf6'] },
  { title: 'Défense scandinave', moves: ['e4', 'd5'] },
  { title: 'Défense semi-slave', moves: ['d4', 'd5', 'c4', 'c6', 'Nf3', 'Nf6', 'Nc3', 'e6'] },
  { title: 'Défense sicilienne', moves: ['e4', 'c5'] },
  { title: 'Défense slave', moves: ['d4', 'd5', 'c4', 'c6'] },
  { title: 'Gambit dame', moves: ['d4', 'd5', 'c4'] },
  { title: 'Gambit dame accepté', moves: ['d4', 'd5', 'c4', 'dxc4'] },
  { title: 'Gambit dame refusé', moves: ['d4', 'd5', 'c4', 'e6'] },
  { title: 'Gambit du roi', moves: ['e4', 'e5', 'f4'] },
  { title: 'Ouverture anglaise', moves: ['c4'] },
  { title: 'Partie catalane', moves: ['d4', 'Nf6', 'c4', 'e6', 'g3'] },
  { title: 'Partie des quatre cavaliers', moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Nc3', 'Nf6'] },
  { title: 'Partie écossaise', moves: ['e4', 'e5', 'Nf3', 'Nc6', 'd4'] },
  { title: 'Partie espagnole', moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Bb5'] },
  { title: 'Partie italienne', moves: ['e4', 'e5', 'Nf3', 'Nc6', 'Bc4'] },
  { title: 'Partie viennoise', moves: ['e4', 'e5', 'Nc3'] },
  { title: 'Système de Londres', moves: ['d4', 'd5', 'Nf3', 'Nf6', 'Bf4'] },
];
