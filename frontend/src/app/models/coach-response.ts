export interface ExplanationClaim {
  claim: string;
  source_id: number;
  evidence: string;
}

export interface ExplanationResponse {
  claims: ExplanationClaim[];
  limitation: 'none' | 'no_strategic_plans' | 'insufficient_context';
}

export interface DocumentSearchResult {
  id: string;
  title: string;
  section_path: string[];
  text: string;
  source_url: string;
  score: number;
}

export interface VideoReference {
  id: string;
  title: string;
  channel: string;
  url: string;
}

export interface PlayerReference {
  name: string;
  rating: number;
}

export interface GameReference {
  id: string;
  uci: string;
  white: PlayerReference;
  black: PlayerReference;
  winner: 'white' | 'black' | null;
  month: string;
}

export interface LichessMove {
  uci: string;
  san: string;
  opening: string | null;
  games_count: number;
  frequency: number;
}

export interface StockfishMove {
  uci: string | null;
  san: string | null;
  score_cp: number | null;
  mate: number | null;
}

export interface OpeningMovesResponse {
  fen: string;
  game_over: boolean;
  termination: string | null;
  source: 'lichess' | 'stockfish' | null;
  moves: LichessMove[] | StockfishMove[];
  games: GameReference[];
  opening: Record<string, string> | null;
  documents: DocumentSearchResult[];
  videos: VideoReference[];
  explanation: ExplanationResponse | null;
}

export interface AnalysisCreatedResponse {
  id: string;
  result: OpeningMovesResponse;
}

export interface SavedAnalysis {
  _id: string;
  fen: string;
  created_at: string;
  result: OpeningMovesResponse;
}

export interface AnalysisSummary {
  _id: string;
  fen: string;
  created_at: string;
}