import {
  Component,
  signal,
  viewChild,
  ElementRef,
  afterNextRender,
  inject,
} from '@angular/core';

import { Chess } from 'chess.js';
import { Chessground } from '@lichess-org/chessground';
import type { Api } from '@lichess-org/chessground/api';
import type { Key } from '@lichess-org/chessground/types';

import { coachDemoScenarios } from './data/coach-demo';
import type { AnalysisSummary, LichessMove, OpeningMovesResponse, StockfishMove } from './models/coach-response';
import { DatePipe } from '@angular/common';

import { ChessApi } from './services/chess-api';
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  imports: [DatePipe],
  selector: 'app-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})

export class App {
  private board?: Api;
  private readonly chessApi = inject(ChessApi);

  protected readonly title = signal('Mon coach d’échecs');

  protected readonly moveCount = signal(0);
  protected readonly turn = signal('white');

  protected readonly demoScenarios = coachDemoScenarios;
  protected readonly analysis = signal<OpeningMovesResponse | null>(null);
  protected readonly analysisId = signal<string | null>(null);
  
  private game = new Chess();
  protected readonly fen = signal(this.game.fen());
  protected readonly fenError = signal('');
  protected readonly gameStatus = signal('Au tour des Blancs');
  protected readonly pendingPromotion =
    signal<{ from: Key; to: Key } | null>(null);
  protected readonly analysisState =
  signal<'idle' | 'loading' | 'ready' | 'error'>('idle');
  protected readonly analysisError = signal('');
  protected readonly savedAnalysisError = signal('');
  protected readonly analysisHistory = signal<AnalysisSummary[]>([]);
  protected readonly historyLoading = signal(false);
  protected readonly historyLoaded = signal(false);
  protected readonly historyError = signal('');

  private analysisRequestId = 0;
  
  private readonly boardElement =
  viewChild.required<ElementRef<HTMLElement>>('boardElement');

  constructor() {
    afterNextRender(() => {
      this.board = Chessground(this.boardElement().nativeElement, {
        fen: this.game.fen(),
        orientation: 'white',
        turnColor: 'white',
        movable: {
          free: false,
          color: 'white',
          dests: this.getLegalDestinations(),
          rookCastle: false,
          events: {
            after: (from, to) => this.playMove(from, to),
          },
        },
        premovable: { enabled: false },
      });
    });
  }


protected undoMove(): void {
  this.game.undo();
  this.syncPosition();
}

protected flipBoard(): void {
  this.board?.toggleOrientation();
}

protected playSuggestedMove(uci: string | null): void {
  const response = this.analysis();
  if (!uci || !response || response.fen !== this.game.fen()
      || this.pendingPromotion() || this.game.isGameOver()) {
    return;
  }
  if (!response.moves.some(move => move.uci === uci)
      || !this.game.moves({ verbose: true }).some(move => move.lan === uci)) {
    this.analysisError.set('Ce coup ne peut pas être joué dans la position actuelle.');
    this.analysisState.set('error');
    return;
  }

  this.game.move(uci);
  this.syncPosition();
}

protected resetGame(): void {
  this.game.reset();
  this.syncPosition();
  this.fenError.set('');
}

protected loadFen(value: string): void {
  try {
    this.game.load(value.trim());
  } catch {
    this.fenError.set('FEN invalide : vérifie la position saisie.');
    return;
  }

  this.fenError.set('');
  this.syncPosition();
}

private syncPosition(): void {
  this.pendingPromotion.set(null);
  this.analysisRequestId++;
  this.analysisState.set('idle');
  this.analysis.set(null);
  this.analysisId.set(null);
  this.analysisError.set('');
  const color = this.game.turn() === 'w' ? 'white' : 'black';
  this.turn.set(color);

  this.fen.set(this.game.fen());
  this.moveCount.set(this.game.history().length);

  this.board?.selectSquare(null);
  this.board?.set({
    fen: this.game.fen(),
    turnColor: color,
    movable: {
      color,
      dests: this.getLegalDestinations(),
    },
    });
  this.updateGameStatus();
}

private getLegalDestinations(): Map<Key, Key[]> {
  const destinations = new Map<Key, Key[]>();
  if (this.game.isGameOver()) {
    return destinations;
  }

  for (const move of this.game.moves({ verbose: true })) {
    const squares = destinations.get(move.from) ?? [];

    if (!squares.includes(move.to)) {
      squares.push(move.to);
    }

    destinations.set(move.from, squares);
  }

  return destinations;
}

private playMove(from: Key, to: Key): void {
  if (this.pendingPromotion() || this.game.isGameOver()) {
    return;
  }

  const legalMove = this.game.moves({ verbose: true }).find(
    move => move.from === from && move.to === to
  );
  if (!legalMove) {
    this.syncPosition();
    return;
  }

  if (legalMove.promotion) {
    this.syncPosition();
    this.pendingPromotion.set({ from, to });
    this.board?.set({
      movable: {
        color: undefined,
        dests: new Map<Key, Key[]>(),
      },
    });
    return;
  }

  this.game.move({ from, to });
  this.syncPosition();
}

protected choosePromotion(piece: 'q' | 'r' | 'b' | 'n'): void {
  const move = this.pendingPromotion();
  if (!move) {
    return;
  }

  this.game.move({ from: move.from, to: move.to, promotion: piece });
  this.syncPosition();
}

protected cancelPromotion(): void {
  this.syncPosition();
}

private updateGameStatus(): void {
  if (this.game.isCheckmate()) {
    this.gameStatus.set(
      this.game.turn() === 'w'
        ? 'Échec et mat — les Noirs gagnent'
        : 'Échec et mat — les Blancs gagnent'
    );
  } else if (this.game.isStalemate()) {
    this.gameStatus.set('Partie nulle — pat');
  } else if (this.game.isInsufficientMaterial()) {
    this.gameStatus.set('Partie nulle — matériel insuffisant');
  } else if (this.game.isDraw()) {
    this.gameStatus.set('Partie nulle');
  } else {
    const player = this.game.turn() === 'w' ? 'Blancs' : 'Noirs';
    const check = this.game.isCheck() ? ' — échec !' : '';

    this.gameStatus.set(`Au tour des ${player}${check}`);
  }
}

protected formatMonth(month: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${month}-01T00:00:00Z`));
}

protected isLichessMove(move: LichessMove | StockfishMove): move is LichessMove {
  return 'games_count' in move;
}

protected isStockfishMove(move: LichessMove | StockfishMove): move is StockfishMove {
  return 'score_cp' in move;
}

protected formatFrequency(frequency: number): string {
  return new Intl.NumberFormat('fr-FR', {
    style: 'percent', maximumFractionDigits: 1,
  }).format(frequency);
}

protected formatScore(score: number): string {
  return new Intl.NumberFormat('fr-FR', {
    minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'always',
  }).format(score / 100);
}

protected analysePosition(): void {
  if (this.pendingPromotion() || this.analysisState() === 'loading') {
    return;
  }

  const requestId = ++this.analysisRequestId;
  const requestedFen = this.game.fen();

  this.analysis.set(null);
  this.analysisId.set(null);
  this.analysisError.set('');
  this.analysisState.set('loading');

  this.chessApi.createAnalysis(requestedFen).subscribe({
    next: (response) => {
      if (requestId !== this.analysisRequestId) {
        return;
      }

      this.analysis.set(response.result);
      this.analysisId.set(response.id);
      this.analysisState.set('ready');
    },

    error: (erreur: HttpErrorResponse) => {
      if (requestId !== this.analysisRequestId) {
        return;
      }

      this.analysisError.set(
        erreur.status === 0
          ? 'Impossible de joindre le serveur.'
          : `L’analyse a échoué (erreur ${erreur.status}). Réessaie.`
      );
      this.analysisState.set('error');
    },
  });
}

protected refreshHistory(): void {
  if (this.historyLoading()) {
    return;
  }

  this.historyLoading.set(true);
  this.historyError.set('');

  this.chessApi.listAnalyses().subscribe({
    next: (analyses) => {
      this.analysisHistory.set(analyses);
      this.historyLoaded.set(true);
      this.historyLoading.set(false);
    },
    error: () => {
      this.historyError.set('Impossible de charger l’historique. Réessaie.');
      this.historyLoading.set(false);
    },
  });
}

protected loadSavedAnalysis(value: string): void {
  if (this.pendingPromotion() || this.analysisState() === 'loading') {
    return;
  }

  const id = value.trim();
  this.savedAnalysisError.set('');

  if (!id) {
    this.savedAnalysisError.set('Saisis un identifiant d’analyse.');
    return;
  }

  const requestId = ++this.analysisRequestId;

  this.analysis.set(null);
  this.analysisId.set(null);
  this.analysisError.set('');
  this.analysisState.set('loading');

  this.chessApi.getAnalysis(id).subscribe({
    next: (saved) => {
      if (requestId !== this.analysisRequestId) {
        return;
      }

      // Restaurer d’abord la position sur l’échiquier.
      this.loadFen(saved.fen);

      if (this.fenError()) {
        this.savedAnalysisError.set(
          'La position enregistrée est invalide.'
        );
        this.analysisState.set('idle');
        return;
      }

      // Puis afficher l’analyse associée.
      this.analysis.set(saved.result);
      this.analysisId.set(saved._id);
      this.analysisState.set('ready');
    },

    error: (erreur: HttpErrorResponse) => {
      if (requestId !== this.analysisRequestId) {
        return;
      }

      const message =
        erreur.status === 404
          ? 'Analyse introuvable.'
          : erreur.status === 400
            ? 'Identifiant d’analyse invalide.'
            : 'Impossible de charger l’analyse. Réessaie.';

      this.savedAnalysisError.set(message);
      this.analysisState.set('idle');
    },
  });
}

}
