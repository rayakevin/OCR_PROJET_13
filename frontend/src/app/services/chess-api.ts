import { inject, Service } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import type {
  OpeningMovesResponse,
  AnalysisCreatedResponse,
  SavedAnalysis,
  AnalysisSummary,
} from '../models/coach-response';

/** Accès HTTP à FastAPI ; les Observables sont exécutés lors de subscribe(). */
@Service()
export class ChessApi {
  private readonly http = inject(HttpClient);

  /** Calcule une analyse sans l’enregistrer. */
  getOpeningMoves(fen: string) {
    return this.http.get<OpeningMovesResponse>('/api/v1/opening-moves', { params: { fen } });
  }

  /** Calcule et persiste une nouvelle analyse ; renvoie son identifiant et son résultat. */
  createAnalysis(fen: string, base_fen?: string, played_moves: string[] = []) {
    return this.http.post<AnalysisCreatedResponse>('/api/v1/analyses', { fen, base_fen, played_moves });
  }

  /** Analyse automatique sans écriture dans l’historique. */
  previewAnalysis(fen: string, base_fen: string, played_moves: string[]) {
    return this.http.post<OpeningMovesResponse>('/api/v1/analyses/preview', { fen, base_fen, played_moves });
  }

  /** Conserve exactement le résultat affiché, sans nouvel appel aux outils. */
  saveAnalysis(result: OpeningMovesResponse) {
    return this.http.post<AnalysisCreatedResponse>('/api/v1/analyses/save', result);
  }

  /** Relit une analyse existante sans appeler les services de calcul. */
  getAnalysis(analysisId: string) {
    return this.http.get<SavedAnalysis>(`/api/v1/analyses/${encodeURIComponent(analysisId)}`);
  }

  /** Liste toutes les sauvegardes, de la plus récente à la plus ancienne. */
  listAnalyses() {
    return this.http.get<AnalysisSummary[]>('/api/v1/analyses');
  }
}
