import { inject, Service } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import type {
  OpeningMovesResponse,
  AnalysisCreatedResponse,
  SavedAnalysis,
  AnalysisSummary,
 } from '../models/coach-response';


@Service()
export class ChessApi {
  private readonly http = inject(HttpClient);

  getOpeningMoves(fen: string) {
    return this.http.get<OpeningMovesResponse>(
      '/api/v1/opening-moves',
      { params: { fen } },
    );
  }

  createAnalysis(fen: string) {
  return this.http.post<AnalysisCreatedResponse>(
    '/api/v1/analyses',
    { fen },
  );
  }

  getAnalysis(analysisId: string) {
  return this.http.get<SavedAnalysis>(
    `/api/v1/analyses/${encodeURIComponent(analysisId)}`,
  );
  }

  listAnalyses(limit: number = 10) {
  return this.http.get<AnalysisSummary[]>(
    '/api/v1/analyses',
    { params: { limit } },
  );
}
}

