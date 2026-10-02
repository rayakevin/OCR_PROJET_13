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
  createAnalysis(fen: string) {
    return this.http.post<AnalysisCreatedResponse>('/api/v1/analyses', { fen });
  }

  /** Relit une analyse existante sans appeler les services de calcul. */
  getAnalysis(analysisId: string) {
    return this.http.get<SavedAnalysis>(`/api/v1/analyses/${encodeURIComponent(analysisId)}`);
  }

  /** Liste les derniers résumés ; le backend accepte une limite de 1 à 50. */
  listAnalyses(limit: number = 10) {
    return this.http.get<AnalysisSummary[]>('/api/v1/analyses', { params: { limit } });
  }
}
