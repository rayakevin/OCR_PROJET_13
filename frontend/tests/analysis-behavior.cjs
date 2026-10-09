// Teste le composant réel avec des services HTTP contrôlés, sans navigateur ni réseau.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const { Subject, of } = require('rxjs');
const { Chess } = require('chess.js');

function setup() {
  const previews = [], saves = [], timers = new Map();
  let timerId = 0;
  const api = {
    previewAnalysis: (...args) => { const stream = new Subject(); previews.push({ args, stream }); return stream; },
    saveAnalysis: result => { const stream = new Subject(); saves.push({ result, stream }); return stream; },
    listAnalyses: () => of([]),
    getAnalysis: () => of({ _id: 'saved', fen: new Chess().fen(), result: { fen: new Chess().fen(), moves: [] } }),
  };
  const DestroyRef = {};
  const angular = {
    Component: () => value => value, DestroyRef,
    inject: token => token === DestroyRef ? { onDestroy() {} } : api,
    signal: initial => { let value = initial; const read = () => value; read.set = next => value = next; return read; },
    viewChild: { required: () => () => null }, afterNextRender() {},
  };
  const code = ts.transpileModule(fs.readFileSync('src/app/app.ts', 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, experimentalDecorators: true },
  }).outputText;
  const exports = {};
  vm.runInNewContext(code, { exports, Map, Intl, Date,
    setTimeout: callback => { timers.set(++timerId, callback); return timerId; },
    clearTimeout: id => timers.delete(id),
    require: name => name === '@angular/core' ? angular
      : name === './services/chess-api' ? { ChessApi: {} }
      : name === './data/coach-demo' ? { coachDemoScenarios: [] }
      : name === './data/rag-corpus' ? { ragCorpusOpenings: [] }
      : name.startsWith('@') ? {} : require(name),
  });
  const app = new exports.App();
  const flush = () => { const callbacks = [...timers.values()]; timers.clear(); callbacks.forEach(fn => fn()); };
  return { app, previews, saves, flush };
}

test('un coup analyse sans sauvegarder ; les réponses périmées sont ignorées', () => {
  const { app, previews, saves, flush } = setup();
  app.playMove('e2', 'e4'); flush();
  assert.equal(previews.length, 1);
  assert.equal(saves.length, 0);
  app.playMove('e7', 'e5'); flush();
  app.playMove('g1', 'f3'); flush();
  assert.equal(previews.length, 1);
  previews[0].stream.next({ fen: previews[0].args[0], moves: [] });
  assert.equal(app.analysis(), null);
  previews[0].stream.complete();
  assert.equal(previews.length, 2);
  assert.equal(previews[1].args[0], app.fen());
  assert.deepEqual(Array.from(previews[1].args[2]), ['e2e4', 'e7e5', 'g1f3']);
});

test('une ouverture du corpus rejoue ses coups depuis le début puis lance une analyse', () => {
  const { app, previews, flush } = setup();
  app.playMove('d2', 'd4'); flush();
  app.loadCorpusOpening({ title: 'Défense française', moves: ['e4', 'e6'] }); flush();
  previews[0].stream.complete();
  assert.equal(previews.length, 2);
  const last = previews[previews.length - 1];
  assert.equal(last.args[0], 'rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2');
  assert.equal(last.args[1], new Chess().fen());
  assert.deepEqual(Array.from(last.args[2]), ['e2e4', 'e7e6']);
  assert.equal(app.moveCount(), 2);
});

test('sauvegarder conserve le résultat et résiste au double clic et au changement de position', () => {
  const { app, previews, saves, flush } = setup();
  app.playMove('e2', 'e4'); flush();
  const result = { fen: app.fen(), moves: [] };
  previews[0].stream.next(result); previews[0].stream.complete();
  app.savePosition(); app.savePosition();
  assert.equal(saves.length, 1);
  assert.equal(saves[0].result, result);
  app.playMove('e7', 'e5');
  saves[0].stream.next({ id: 'old' });
  assert.equal(app.analysisId(), null);
});

test('charger une sauvegarde ne relance pas d’analyse ; une promotion attend le choix', () => {
  const { app, previews, flush } = setup();
  app.loadSavedAnalysis('saved'); flush();
  assert.equal(previews.length, 0);
  assert.equal(app.analysisId(), 'saved');
  app.loadFen('7k/P7/8/8/8/8/8/7K w - - 0 1', false);
  app.playMove('a7', 'a8'); flush();
  assert.equal(previews.length, 0);
  app.choosePromotion('q'); flush();
  assert.equal(previews.length, 1);
});
