import type {
  DocumentSearchResult,
  ExplanationResponse,
  GameReference,
  OpeningMovesResponse,
  VideoReference,
} from '../models/coach-response';

export const demoDocuments: DocumentSearchResult[] = [
  {
    id: 'wikipedia_fr_Défense_française_chunk_0',
    title: 'Défense française',
    section_path: ['Introduction'],
    text: "La défense française est une ouverture du jeu d'échecs, débutant par les coups 1. e4 e6.",
    source_url: 'https://fr.wikipedia.org/wiki/Défense_française',
    score: 0.6777499914169312,
  },
];

export const demoExplanation: ExplanationResponse = {
  claims: [
    {
      claim: 'La défense française commence par les coups 1. e4 e6.',
      source_id: 1,
      evidence: demoDocuments[0].text,
    },
  ],
  limitation: 'insufficient_context',
};

export const demoVideos: VideoReference[] = [
  {
    id: 'sIQjKy-Y4jg',
    title: 'Un répertoire complet sur la FRANCAISE en 10min',
    channel: 'Julien Song',
    url: 'https://www.youtube.com/watch?v=sIQjKy-Y4jg',
  },
];

export const demoGames: GameReference[] = [
  {
    id: '7nbTX8Jv',
    uci: 'b1d2',
    white: { name: 'Carlsen, M.', rating: 2881 },
    black: { name: 'Caruana, F.', rating: 2791 },
    winner: 'white',
    month: '2014-06',
  },
  {
    id: 'hVPOX7F4',
    uci: 'b1c3',
    white: { name: 'So, W.', rating: 2815 },
    black: { name: 'Carlsen, M.', rating: 2832 },
    winner: null,
    month: '2017-11',
  },
];

export interface CoachDemoScenario {
  id: string;
  label: string;
  response: OpeningMovesResponse;
}

// Réponses de démonstration : aucun appel Lichess ou Stockfish n'est effectué.
export const coachDemoScenarios: CoachDemoScenario[] = [
  {
    id: 'french',
    label: 'Défense française',
    response: {
      fen: 'rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3',
      game_over: false,
      termination: null,
      source: 'lichess',
      opening: { eco: 'C00', name: 'French Defense' },
      moves: [
        { uci: 'b1c3', san: 'Nc3', opening: 'French Defense: Paulsen Variation', games_count: 70617, frequency: 0.5053384093543817 },
        { uci: 'b1d2', san: 'Nd2', opening: 'French Defense: Tarrasch Variation', games_count: 43735, frequency: 0.31296961543415724 },
        { uci: 'e4e5', san: 'e5', opening: 'French Defense: Advance Variation', games_count: 15864, frequency: 0.1135234932947861 },
      ],
      games: demoGames,
      documents: demoDocuments,
      videos: demoVideos,
      explanation: demoExplanation,
    },
  },
  {
    id: 'stockfish',
    label: 'Position initiale',
    response: {
      fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
      game_over: false,
      termination: null,
      source: 'stockfish',
      opening: null,
      // Exemple d'analyse initiale précédemment obtenu ; pas un calcul en direct.
      moves: [{ uci: 'e2e4', san: 'e4', score_cp: 32, mate: null }],
      games: [],
      documents: [],
      videos: [],
      explanation: null,
    },
  },
  {
    id: 'finished',
    label: 'Partie terminée',
    response: {
      fen: '8/8/8/8/8/2k5/8/K7 w - - 0 1',
      game_over: true,
      termination: 'INSUFFICIENT_MATERIAL',
      source: null,
      opening: null,
      moves: [],
      games: [],
      documents: [],
      videos: [],
      explanation: null,
    },
  },
];
