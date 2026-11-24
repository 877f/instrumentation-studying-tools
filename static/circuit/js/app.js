/* Circuit Bench editor: state, editing, panels, persistence. The model, solver and meter
   logic live in core/ and meter/; drawing lives in views/. */

import { registry } from './components/registry.js';
import { createCircuit, addComponent, addWire, deserialize, emptyInner } from './core/netlist.js';
import { scopeAt, blockAt, findGlobal, nextTreeId, globalAttachTerm, equivalentR, isSolved, gradeGuess, blockChecks } from './core/blocks.js';
import { parseEng, formatEng } from './core/units.js';
import { encodeShare, decodeShare } from './core/share.js';
import { measure, initialMeter, userIssues, dialOf, jackOf } from './meter/meter-model.js';
import { meterFace } from './views/meter-face.js';
import { renderBoard, indexCircuit, findTarget, attachPoint, bounds, short } from './views/schematic.js';
import { SHAPES, snap, pinDir, nearestOn, resistorBands, E12, E24 } from './views/symbols.js';
import { buildDemo, DEMO_STEPS } from './demo.js';

const STORE_KEY = 'circuit-bench:v1';
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const $ = (id) => document.getElementById(id);
const store = {
  get() { try { return JSON.parse(localStorage.getItem(STORE_KEY)); } catch { return null; } },
  set(v) { try { localStorage.setItem(STORE_KEY, JSON.stringify(v)); } catch { /* private mode */ } },
};

const PRESETS = registry.get('vsource').presets;
const PALETTE = [
  { key: 'select', label: 'Select', hint: 'Select and move (Esc)' },
  { key: 'wire', label: 'Wire', hint: 'Draw wires' },
  { key: 'resistor', label: 'Resistor', type: 'resistor' },
  { key: 'reqblock', label: 'Req block', type: 'reqblock', hint: 'Place a Req block: one resistor you build from other resistors' },
  { key: 'supply', label: 'DC supply', type: 'vsource', params: PRESETS.bench },
  { key: 'battery', label: 'Battery', type: 'vsource', params: PRESETS.battery9v, style: 'battery' },
  { key: 'switch', label: 'Switch', type: 'switch' },
  { key: 'ground', label: 'Ground', type: 'ground' },
];
const POWER = [0.125, 0.25, 0.5, 1, 2, 5, 10];
const IN_BLOCK = new Set(['select', 'wire', 'resistor', 'reqblock']);   // the tools offered inside a Req block
const TWO_PIN = new Set(['resistor', 'reqblock']);

let profile = null;
const S = {
  circuit: createCircuit(),
  meter: initialMeter(),
  probes: { red: null, black: null },     // attachments: { kind: 'pin', term } | { kind: 'wire', id, t }
  sel: null,                               // { kind: 'comp'|'wire', id }
  tool: 'select',                          // 'select' | 'wire' | palette key of a part
  ghostRot: 0,
  ghostAt: null,
  overlay: false,
  view: { x: -60, y: -40, scale: 1 },
  pending: null,                           // wire being drawn: { from: term, to: [x,y], fresh: junction id or null }
  probeDrag: null,
  armed: null,
  highlight: new Set(),
  blowEvent: null,
  series: 'E12',
  undo: [],
  redo: [],
  last: null,                              // last measurement, for tooltips and panels
  demo: null,                              // { step } while the teacher demo is running
  path: [],                                // open Req blocks, outermost first: ['Req1', 'Req3']
  viewStack: [],                           // each parent board's view, restored on close
  reqMsg: null,                            // { id, ok, text } after a Req check
  drafts: {},                              // typed-but-unchecked Req guesses, by block path
};

/* S.circuit is always the whole circuit. cur() is the one being edited: the root, or the inside
   of the open Req block. Selections and the editing helpers below work in cur(); probes, issues
   and solve results use global ids ("Req1/R2"), and pre() is the prefix for the open block. */
const cur = () => scopeAt(S.circuit, S.path) || S.circuit;
const pre = (path = S.path) => path.map((id) => `${id}/`).join('');
const pretty = (id) => String(id).replace(/\//g, ' › ');

/* ================================================================ model edits */

function snapshot() { return JSON.stringify({ circuit: S.circuit, probes: S.probes }); }
function pushUndo() {
  S.undo.push(snapshot());
  if (S.undo.length > 100) S.undo.shift();
  S.redo = [];
}
function restore(snap) {
  const d = JSON.parse(snap);
  S.circuit = d.circuit;
  S.probes = d.probes;
  S.pending = null;
  fixPath();
  if (S.sel && !findSel()) S.sel = null;
}

/** After an undo or load, close any open block that no longer exists. */
function fixPath() {
  while (S.path.length && !scopeAt(S.circuit, S.path)) { S.path.pop(); S.view = S.viewStack.pop() || S.view; }
}
function undo() { if (!S.undo.length) return; S.redo.push(snapshot()); restore(S.undo.pop()); afterChange(); }
function redo() { if (!S.redo.length) return; S.undo.push(snapshot()); restore(S.redo.pop()); afterChange(); }

/** Change the model: snapshot for undo, apply, then re-check, save and redraw. */
function commit(fn, { history = true } = {}) {
  if (history) pushUndo();
  fn(cur());
  afterChange();
}

function afterChange() {
  dropStaleProbes();
  checkFuse();
  save();
  render();
}

const comp = (id) => cur().components.find((c) => c.id === id);
const wire = (id) => cur().wires.find((w) => w.id === id);
function findSel() { return S.sel && (S.sel.kind === 'comp' ? comp(S.sel.id) : wire(S.sel.id)); }

function dropStaleProbes() {
  for (const k of ['red', 'black']) {
    const a = S.probes[k];
    if (!a) continue;
    const ok = !!findGlobal(S.circuit, a.kind === 'pin' ? a.term.split('.')[0] : a.id);
    if (!ok) S.probes[k] = null;
  }
}

function removeComponent(id) {
  const c = cur();
  c.components = c.components.filter((x) => x.id !== id);
  c.wires = c.wires.filter((w) => !w.a.startsWith(`${id}.`) && !w.b.startsWith(`${id}.`));
  pruneJunctions();
}
function removeWire(id) {
  cur().wires = cur().wires.filter((w) => w.id !== id);
  pruneJunctions();
}
/** Junctions with nothing attached are clutter; a junction joining exactly two wires in a line is kept (it's a corner). */
function pruneJunctions(keep = null) {
  const c = cur();
  const used = new Set(c.wires.flatMap((w) => [w.a, w.b]));
  c.components = c.components.filter((x) => x.type !== 'junction' || x.port || x.id === keep || used.has(`${x.id}.j`));
}

function placePart(key, at) {
  const p = PALETTE.find((x) => x.key === key);
  commit((c) => {
    // Resistors and blocks get names unique across every level, so "R2" means one part.
    const named = TWO_PIN.has(p.type) ? { id: nextTreeId(S.circuit, registry.get(p.type).prefix) } : {};
    const id = addComponent(c, registry, p.type, p.params ? { ...p.params } : {},
      { layout: { x: snap(at[0]), y: snap(at[1]), rot: S.ghostRot }, ...(p.style ? { style: p.style } : {}), ...named,
        ...(p.type === 'reqblock' ? { inner: emptyInner() } : {}) });
    S.sel = { kind: 'comp', id };
  });
}

/** Wire end at a board point: an existing pin, a new junction teed into a wire, or a new corner junction. */
function endAt(c, p, hitTerm) {
  if (hitTerm) return { term: hitTerm, kind: 'pin' };
  const ix = indexCircuit(c);
  const t = findTarget(ix, c, p, { pinRadius: 10, wireRadius: 8 });
  if (t && t.kind === 'pin') return { term: t.term, kind: 'pin' };
  if (t && t.kind === 'wire') {
    const w = c.wires.find((x) => x.id === t.id);
    if (!w.cut) {
      const pts = ix.route(w);
      let q = [snap(t.point[0]), snap(t.point[1])];
      if (nearestOn(pts, q).dist > 0.5) q = t.point;
      const j = addComponent(c, registry, 'junction', {}, { layout: { x: q[0], y: q[1], rot: 0 } });
      const oldB = w.b;
      w.b = `${j}.j`;
      addWire(c, `${j}.j`, oldB, { layout: { ...(w.layout || {}) } });
      return { term: `${j}.j`, kind: 'split' };
    }
  }
  const q = [snap(p[0]), snap(p[1])];
  const there = findTarget(indexCircuit(c), c, q, { pinRadius: 1, wireRadius: -1 });
  if (there) return { term: there.term, kind: 'pin' };
  const j = addComponent(c, registry, 'junction', {}, { layout: { x: q[0], y: q[1], rot: 0 } });
  return { term: `${j}.j`, kind: 'free' };
}

function bendFor(c, fromTerm, toPoint) {
  const [id, pin] = fromTerm.split('.');
  const part = c.components.find((x) => x.id === id);
  const d = part && pinDir(part, pin);
  if (d) return d === 'h' ? 'hv' : 'vh';
  const from = indexCircuit(c).termPos(fromTerm);
  if (!from || !toPoint) return 'hv';
  return Math.abs(toPoint[0] - from[0]) >= Math.abs(toPoint[1] - from[1]) ? 'hv' : 'vh';
}

/** Finish the wire being drawn at point p. Returns true if drawing continues from a new corner. */
function finishWire(p, hitTerm, { chain }) {
  const from = S.pending.from;
  let cont = null;
  commit((c) => {
    const end = endAt(c, p, hitTerm);
    if (end.term === from) { cont = from; return; }
    const to = indexCircuit(c).termPos(end.term);
    addWire(c, from, end.term, { layout: { bend: bendFor(c, from, to) } });
    if (end.kind === 'free' && chain) cont = end.term;
  });
  S.pending = cont ? { from: cont, to: p, fresh: null } : null;
  render();
}

function startWire(p, hitTerm) {
  let from = hitTerm, fresh = null;
  if (!from) {
    commit((c) => {
      const end = endAt(c, p, null);
      from = end.term;
      if (end.kind === 'free') fresh = from.split('.')[0];
    });
  }
  S.pending = { from, to: p, fresh };
  render();
}

function cancelWire() {
  if (!S.pending) return;
  const fresh = S.pending.fresh;
  S.pending = null;
  if (fresh && !cur().wires.some((w) => w.a === `${fresh}.j` || w.b === `${fresh}.j`)) {
    cur().components = cur().components.filter((x) => x.id !== fresh);
    S.undo.pop();
  }
  render();
}

/* ================================================================ measuring */

function probeTerm(which) {
  if (S.probeDrag && S.probeDrag.which === which) return S.probeDrag.target ? globalAttachTerm(S.circuit, toAtt(S.probeDrag.target)) : null;
  return globalAttachTerm(S.circuit, S.probes[which]);
}
/** A board hit in the open scope → a global probe attachment. */
const toAtt = (t) => (t.kind === 'pin' ? { kind: 'pin', term: pre() + t.term } : { kind: 'wire', id: pre() + t.id, t: t.t });

/** Where a (global) probe attachment shows on the board for `path`: on its pin or wire, on the closed
    block that holds it, or nowhere if it's outside this board. */
function probePoint(ix, circuit, path, att) {
  if (!att) return null;
  const P = pre(path);
  const gid = att.kind === 'pin' ? att.term : att.id;
  if (!gid.startsWith(P)) return null;
  const rest = gid.slice(P.length);
  const slash = rest.indexOf('/');
  if (slash < 0) return { point: attachPoint(ix, circuit, att.kind === 'pin' ? { kind: 'pin', term: rest } : { ...att, id: rest }) };
  const blk = circuit.components.find((c) => c.id === rest.slice(0, slash));
  // on the block's outline, clear of its body so the block stays easy to click
  if (!blk) return null;
  const side = att.kind === 'pin' && /\.b$/.test(gid) ? 1 : -1;
  const [dx, dy] = (blk.layout.rot || 0) % 2 ? [0, side * 33] : [side * 33, 0];
  return { point: [blk.layout.x + dx, blk.layout.y + dy], inside: true };
}

/** A solve result seen from inside the block at prefix P: inner ids without the prefix. */
function scoped(result, P) {
  if (!P || !result || !result.ok) return result;
  const rekey = (o) => Object.fromEntries(Object.entries(o).filter(([k]) => k.startsWith(P)).map(([k, v]) => [k.slice(P.length), v]));
  const out = { ...result, components: rekey(result.components), wires: rekey(result.wires),
    nodes: result.nodes.map((n) => ({ ...n, terminals: n.terminals.filter((t) => t.startsWith(P)).map((t) => t.slice(P.length)) })) };
  Object.defineProperties(out, {
    nodeName: { value: (t) => result.nodeName(P + t) },
    voltage: { value: (a, b) => result.voltage(P + a, b === undefined ? undefined : P + b) },
  });
  return out;
}

/** Inside a block whose Req hasn't been checked yet, the live I and V stay hidden. */
const lockedAt = (path = S.path) => path.length > 0 && !isSolved(blockAt(S.circuit, path));

function measureNow() {
  const meter = { ...S.meter, probes: { red: probeTerm('red'), black: probeTerm('black') } };
  return measure(S.circuit, profile, meter);
}

function checkFuse() {
  const m = measureNow();
  if (m.blows) {
    S.meter.fuses[m.blows] = 'blown';
    S.blowEvent = { fuse: m.blows, verdict: m.fuse, fault: m.fault };
    flash();
  }
}

function flash() {
  const card = $('meterCard');
  card.classList.remove('blowing');
  void card.offsetWidth;
  card.classList.add('blowing');
}

/* ================================================================ persistence */

let saveTimer = 0;
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => store.set({ circuit: S.circuit, probes: S.probes, meter: S.meter, overlay: S.overlay }), 250);
}

function loadState(d) {
  if (!d || !d.circuit) return false;
  const r = deserialize(d.circuit);
  if (r.error) return false;
  S.circuit = r.circuit;
  const fill = (circ) => {
    for (const c of circ.components) {
      c.layout = { x: 0, y: 0, rot: 0, ...(c.layout || {}) };
      if (c.type === 'reqblock') { if (!c.inner) c.inner = emptyInner(); fill(c.inner); }
    }
  };
  fill(S.circuit);
  S.path = [];
  S.viewStack = [];
  S.probes = d.probes || { red: null, black: null };
  if (d.meter) S.meter = { ...initialMeter(), ...d.meter, probes: { red: null, black: null } };
  if (typeof d.overlay === 'boolean') S.overlay = d.overlay;
  dropStaleProbes();
  return true;
}

async function share() {
  const code = await encodeShare({ circuit: S.circuit, probes: S.probes, meter: { dial: S.meter.dial, red: S.meter.red } });
  const url = `${location.origin}${location.pathname}#c=${code}`;
  try { await navigator.clipboard.writeText(url); toast('Link copied. Anyone with it sees this circuit.'); }
  catch { window.prompt('Copy this link:', url); }
}

/* ================================================================ examples */

function example(name) {
  const c = createCircuit();
  const add = (type, x, y, rot, params = {}, extra = {}) => addComponent(c, registry, type, params, { layout: { x, y, rot }, ...extra });
  const w = (a, b, bend = 'hv') => addWire(c, a, b, { layout: { bend } });
  if (name === 'divider') {
    add('vsource', 100, 200, 0, { ...PRESETS.bench });
    add('resistor', 200, 120, 0, { R: 1000, Pmax: 0.25 });
    add('resistor', 300, 200, 1, { R: 2000, Pmax: 0.25 });
    add('ground', 100, 300, 0);
    w('V1.p', 'R1.a', 'vh'); w('R1.b', 'R2.a', 'hv'); w('R2.b', 'V1.n'); w('GND1.g', 'V1.n');
  } else if (name === 'series-parallel') {
    add('vsource', 100, 220, 0, { ...PRESETS.bench, V: 24 });
    add('resistor', 180, 120, 0, { R: 100, Pmax: 1 });
    add('resistor', 300, 220, 1, { R: 300, Pmax: 1 });
    add('resistor', 380, 120, 0, { R: 200, Pmax: 0.25 });
    add('resistor', 480, 220, 1, { R: 400, Pmax: 0.25 });
    add('junction', 300, 120, 0);
    add('ground', 100, 320, 0);
    w('V1.p', 'R1.a', 'vh'); w('R1.b', 'J1.j'); w('J1.j', 'R3.a'); w('J1.j', 'R2.a');
    w('R3.b', 'R4.a', 'hv'); w('R4.b', 'R2.b'); w('R2.b', 'V1.n'); w('GND1.g', 'V1.n');
  }
  return c;
}

function clearBoard() {
  if (!S.circuit.components.length) return;
  if (S.pending) cancelWire();
  S.demo = null;
  closeTo(0, { quiet: true });
  commit(() => {
    S.circuit = createCircuit();
    S.probes = { red: null, black: null };
    S.sel = null;
    S.highlight = new Set();
  });
  S.tool = 'select';
  fit();
  render();
  toast('Board cleared. Undo (Ctrl+Z) brings it back.');
}

/* ================================================================ teacher demo */

function startDemo() {
  closeTo(0, { quiet: true });
  pushUndo();
  S.circuit = buildDemo(registry);
  S.demo = { step: 0 };
  applyDemoStep(0, { history: false });
  fit();
  render();
}

function applyDemoStep(i, { history = true } = {}) {
  const st = DEMO_STEPS[i];
  if (!st) return;
  if (history) pushUndo();
  for (const [id, closed] of Object.entries(st.switches)) { const c = comp(id); if (c) c.params.closed = closed; }
  for (const [id, cut] of Object.entries(st.cuts)) { const w = wire(id); if (w) w.cut = cut; }
  S.meter = { ...S.meter, dial: st.dial, red: st.red, fuses: { mA: 'ok', A: 'ok' } };
  S.blowEvent = null;
  S.probes = { red: st.probes[0], black: st.probes[1] };
  S.sel = st.select ? { kind: 'comp', id: st.select } : null;
  S.highlight = new Set();
  S.demo = { step: i };
  afterChange();
}

function renderDemo() {
  const el = $('demoCard');
  el.hidden = !S.demo;
  if (!S.demo) { el.innerHTML = ''; return; }
  const i = S.demo.step, st = DEMO_STEPS[i], last = i === DEMO_STEPS.length - 1;
  el.innerHTML = `<div class="card-head"><span class="label">Teacher demo · ${i + 1} of ${DEMO_STEPS.length}</span>
      <button class="close" data-act="demo-exit" aria-label="End the demo">×</button><h2>${esc(st.title)}</h2></div>
    <div class="steps" role="group" aria-label="Demo steps">${DEMO_STEPS.map((s, j) => `<button class="${j === i ? 'on' : ''}"
      data-demo-step="${j}" title="${esc(s.title)}" aria-label="Step ${j + 1}: ${esc(s.title)}" aria-current="${j === i}">${j + 1}</button>`).join('')}</div>
    <p class="look"><b>What happens</b>${esc(st.look)}</p>
    <p class="why"><b>Why it matters</b>${esc(st.why)}</p>
    <div class="row-btns">
      <button class="btn" data-act="demo-prev" ${i === 0 ? 'disabled' : ''}>Back</button>
      <button class="btn primary" data-act="demo-next">${last ? 'Start over' : 'Next step'}</button>
    </div>`;
}

/* ================================================================ view: board */

const svg = () => (S.path.length ? $('subBoard') : $('board'));
function toWorld(e) {
  const el = svg();
  const m = el.getScreenCTM();
  if (!m) return [0, 0];
  const pt = el.createSVGPoint();
  pt.x = e.clientX; pt.y = e.clientY;
  const q = pt.matrixTransform(m.inverse());
  return [q.x, q.y];
}
function setViewBox() {
  const el = svg();
  const w = el.clientWidth || 800, h = el.clientHeight || 600;
  el.setAttribute('viewBox', `${S.view.x} ${S.view.y} ${w / S.view.scale} ${h / S.view.scale}`);
}
function fit() {
  const b = bounds(cur());
  const el = svg();
  const w = el.clientWidth || 800, h = el.clientHeight || 600;
  if (!b) { S.view = { x: -40, y: -40, scale: 1 }; setViewBox(); return; }
  // On wide screens keep the left edge clear for the floating part editor.
  const reserve = S.sel && window.innerWidth > 960 && w > 700 ? 320 : 0;
  const scale = Math.max(0.4, Math.min((w - reserve) / (b.x1 - b.x0), h / (b.y1 - b.y0), 1.6));
  S.view = { scale, x: (b.x0 + b.x1) / 2 - (reserve + (w - reserve) / 2) / scale, y: (b.y0 + b.y1) / 2 - h / scale / 2 };
  setViewBox();
}
function zoomAt(factor, clientX, clientY) {
  const r = svg().getBoundingClientRect();
  const cx = clientX ?? r.left + r.width / 2, cy = clientY ?? r.top + r.height / 2;
  const scale = Math.max(0.3, Math.min(3, S.view.scale * factor));
  const wx = S.view.x + (cx - r.left) / S.view.scale, wy = S.view.y + (cy - r.top) / S.view.scale;
  S.view = { scale, x: wx - (cx - r.left) / scale, y: wy - (cy - r.top) / scale };
  setViewBox();
}

/** What renderBoard needs to draw the board for `path` ([] = main board). Only the open board
    (the innermost) is interactive; `passive` is for the small copy inside an expanded block's bubble. */
function boardState(m, path, { passive = false } = {}) {
  const circuit = scopeAt(S.circuit, path);
  const active = !passive && path.length === S.path.length;
  const P = pre(path);
  const ix = indexCircuit(circuit);
  const result = scoped(m.result, P);
  const probes = {};
  for (const which of ['red', 'black']) {
    if (passive) break;
    const d = S.probeDrag && S.probeDrag.which === which ? S.probeDrag : null;
    if (d) {
      if (active && d.overBoard) probes[which] = { point: d.target ? d.target.point : d.world, dragging: true, loose: !d.target };
    } else {
      const pp = probePoint(ix, circuit, path, S.probes[which]);
      if (pp && pp.point) probes[which] = { point: pp.point, armed: S.armed === which, loose: pp.inside, inside: pp.inside };
    }
  }
  const blockInfo = new Map();
  for (const c of circuit.components) if (c.type === 'reqblock') blockInfo.set(c.id, { R: equivalentR(c.inner).R, solved: isSolved(c) });
  // Current and voltage drop on each resistor and block: always inside a block, and on the main
  // board while "Show values" is on. A block whose Req isn't checked yet shows "?" (they'd give Req away).
  let values = null;
  if ((path.length || (S.overlay && !passive)) && result && result.ok) {
    const locked = lockedAt(path);
    values = new Map();
    for (const c of circuit.components) {
      const r = result.components[c.id];
      if (!TWO_PIN.has(c.type) || !r) continue;
      values.set(c.id, locked || (c.type === 'reqblock' && !isSolved(c)) ? 'locked' : { v: r.v, i: r.i });
    }
  }
  const hl = new Set();
  for (const id of S.highlight) if (id.startsWith(P)) hl.add(id.slice(P.length).split('/')[0]);
  const base = { circuit, result, blockInfo, values, highlight: hl, overlay: !path.length && !passive && S.overlay,
    bubble: (c) => renderBoard(boardState(m, [...path, c.id], { passive: true })) };
  if (!active) return { ...base, sel: null, probes, ghost: null, pending: null, target: null };
  let ghost = null;
  const pal = PALETTE.find((x) => x.key === S.tool && x.type);
  if (pal && S.ghostAt) {
    ghost = { id: '', type: pal.type, params: { ...registry.get(pal.type).defaults, ...(pal.params || {}) }, style: pal.style,
      layout: { x: snap(S.ghostAt[0]), y: snap(S.ghostAt[1]), rot: S.ghostRot } };
  }
  let pending = null;
  if (S.pending) {
    const from = ix.termPos(S.pending.from);
    if (from) pending = { from, to: [snap(S.pending.to[0]), snap(S.pending.to[1])], bend: bendFor(circuit, S.pending.from, S.pending.to) };
  }
  return { ...base, sel: S.sel, probes, ghost, pending, target: S.probeDrag && S.probeDrag.target ? S.probeDrag.target.point : null };
}

/* ================================================================ view: panels */

function render() {
  if (!profile) return;
  const m = measureNow();
  S.last = m;
  setViewBox();
  $('board').innerHTML = `<rect class="board-bg" x="-5000" y="-5000" width="10000" height="10000" fill="url(#grid)"/>${renderBoard(boardState(m, []))}`;
  const open = S.path.length > 0;
  $('subwin').hidden = !open;
  $('boardWrap').classList.toggle('dim', open);
  document.body.classList.toggle('in-block', open);
  if (open) {
    $('subBoard').innerHTML = `<rect class="board-bg" x="-5000" y="-5000" width="10000" height="10000" fill="url(#grid2)"/>${renderBoard(boardState(m, S.path))}`;
    renderSubwin(m);
  }
  $('emptyHint').hidden = S.circuit.components.length > 0;
  renderToolbar();
  renderPalette();
  renderInspector(m);
  renderDemo();
  renderMeter(m);
  renderIssues(m);
  renderStatus();
  const ghostEl = $('probeGhost');
  const d = S.probeDrag;
  ghostEl.hidden = !(d && d.moved && !d.overBoard);
  if (!ghostEl.hidden) {
    ghostEl.className = `probe-ghost ${d.which}`;
    ghostEl.style.transform = `translate(${d.client[0]}px, ${d.client[1]}px)`;
  }
}

function renderToolbar() {
  $('undoBtn').disabled = !S.undo.length;
  $('redoBtn').disabled = !S.redo.length;
  $('clearBtn').disabled = !S.circuit.components.length;
  $('overlayBtn').setAttribute('aria-pressed', String(S.overlay));
}

function paletteIcon(p) {
  if (p.key === 'select') return '<svg viewBox="0 0 24 24"><path d="M6 3l12 9-5.5 1.2L15.5 20l-2.6 1.2-3-6.6L6 18z"/></svg>';
  if (p.key === 'wire') return '<svg viewBox="0 0 24 24"><circle cx="4" cy="18" r="2.4"/><circle cx="20" cy="6" r="2.4"/><path class="ln" d="M4 18H13V6H20"/></svg>';
  const c = { type: p.type, params: { closed: false, ...(p.params || {}) }, style: p.style };
  return `<svg viewBox="-46 -46 92 92" class="sym">${SHAPES[p.type].draw(c)}</svg>`;
}
function renderPalette() {
  $('palette').innerHTML = PALETTE.filter((p) => !S.path.length || IN_BLOCK.has(p.key)).map((p) => `<button class="tool ${S.tool === p.key ? 'on' : ''}" data-tool="${p.key}"
    aria-pressed="${S.tool === p.key}" title="${esc(p.hint || `Place a ${p.label.toLowerCase()}`)}">${paletteIcon(p)}<span>${esc(p.label)}</span></button>`).join('');
}

function renderStatus() {
  const pal = PALETTE.find((x) => x.key === S.tool && x.type);
  let text;
  if (S.armed) text = `Tap a pin or wire for the ${S.armed} probe.`;
  else if (pal) text = `Click the board to place a ${pal.label.toLowerCase()}. R rotates. Esc cancels.`;
  else if (S.pending) text = 'Click a pin or a wire to connect. Click empty board for a corner. Esc to stop.';
  else if (S.tool === 'wire') text = 'Click a pin, a wire, or the board to start a wire.';
  else if (S.sel) text = 'Drag to move. R rotates, Delete removes. Drag from a pin to wire it.';
  else if (S.path.length) text = `Build ${S.path.at(-1)} between A and B. Drag from a pin to wire it. Esc closes the window.`;
  else text = 'Click a part to set its value. Drag from any pin to draw a wire. Drag the board to pan; scroll to zoom.';
  $('status').textContent = text;
}

/* ---------------------------------------------------------- inspector */

function field(label, param, value, opts = {}) {
  return `<label class="field"><span>${esc(label)}</span>
    <input class="num" data-param="${param}" data-unit="${opts.unit || ''}" value="${esc(value)}" placeholder="${esc(opts.placeholder || '')}"
      autocomplete="off" spellcheck="false" inputmode="text">${opts.help ? `<small>${esc(opts.help)}</small>` : ''}</label>`;
}

const RESULT_LOCKED = '<p class="help lockmsg">Live I and V for this part unlock once you check this block\'s Req.</p>';

function liveRows(rows) {
  return `<dl class="live">${rows.map(([k, v, cls]) => `<div class="${cls || ''}"><dt>${esc(k)}</dt><dd>${v}</dd></div>`).join('')}</dl>`;
}

function renderInspector(m) {
  const el = $('inspector');
  const item = findSel();
  const r = scoped(m.result, pre());
  const locked = lockedAt();
  el.hidden = !item;
  if (!item) { el.innerHTML = ''; return; }
  const close = '<button class="close" data-act="deselect" aria-label="Close">×</button>';
  if (S.sel.kind === 'wire') {
    const wr = r.ok ? r.wires[item.id] : null;
    el.innerHTML = `<div class="card-head"><span class="label">Selected</span>${close}<h2>${esc(item.id)} · Wire</h2></div>
      ${wr && !wr.cut && locked ? RESULT_LOCKED : ''}
      ${wr && !wr.cut && !locked ? liveRows([['Node', esc(wr.node)], ['Voltage', esc(short(r.nodes.find((n) => n.name === wr.node)?.v ?? 0, 'V')), 'q-v'],
        ['Current', esc(short(Math.abs(wr.i), 'A')), 'q-i']]) : ''}
      ${item.cut ? '<p class="help">This wire is cut. Put the probes on the two ends to measure the current that would flow through it.</p>'
        : '<p class="help">To measure current, cut this wire and put the meter in the gap.</p>'}
      <div class="row-btns">
        <button class="btn ${item.cut ? '' : 'primary'}" data-act="cut">${item.cut ? 'Reconnect wire' : 'Cut wire'}</button>
        <button class="btn" data-act="flip" title="Flip the bend (R)">Flip bend</button>
        <button class="link danger" data-act="delete">Delete</button>
      </div>`;
    return;
  }
  const c = item, p = c.params, cr = r.ok && !locked ? r.components[c.id] : null;
  let body = '';
  if (c.type === 'resistor') {
    const series = S.series === 'E24' ? E24 : E12;
    const opts = [];
    for (let dec = 1; dec <= 1e5; dec *= 10) {
      opts.push(`<optgroup label="${esc(short(dec, 'Ω'))} – ${esc(short(dec * 9.9, 'Ω'))}">${series.map((s) => {
        const v = Math.round(s * dec * 100) / 100;
        return `<option value="${v}" ${Math.abs(v - p.R) < 1e-9 * v ? 'selected' : ''}>${esc(short(v, 'Ω'))}</option>`;
      }).join('')}</optgroup>`);
    }
    opts.push(`<option value="1000000" ${p.R === 1e6 ? 'selected' : ''}>1 MΩ</option>`);
    const bands = resistorBands(p.R);
    const pct = cr ? (cr.p / p.Pmax) * 100 : 0;
    body = `${field('Resistance', 'R', short(p.R, 'Ω'), { unit: 'Ω', help: 'Type 4.7k, 4k7, 220, 1M…' })}
      <div class="field"><span>Standard values</span>
        <div class="pick"><div class="seg" role="group" aria-label="Value series">${['E12', 'E24'].map((x) => `<button class="${S.series === x ? 'on' : ''}"
          data-series="${x}" aria-pressed="${S.series === x}">${x}</button>`).join('')}</div>
        <select data-pick="R" aria-label="Standard resistor values"><option value="">Pick…</option>${opts.join('')}</select></div></div>
      <label class="field"><span>Power rating</span><select data-param-select="Pmax">${POWER.map((w) => `<option value="${w}" ${w === p.Pmax ? 'selected' : ''}>${
        w < 1 ? `${{ 0.125: '⅛', 0.25: '¼', 0.5: '½' }[w]} W` : `${w} W`}</option>`).join('')}</select></label>
      ${bands ? `<div class="bands" title="${esc(bands.names.join(', '))}"><svg viewBox="0 0 120 26" aria-hidden="true"><path class="lead" d="M0 13H120"/>
        <rect class="body" x="22" y="3" width="76" height="20" rx="9"/>${bands.colors.map((col, i, a) => `<rect x="${
        i === a.length - 1 ? 84 : 32 + i * 10}" y="3" width="5" height="20" fill="${col}"/>`).join('')}</svg>
        <span>${esc(bands.names.join(' · '))}</span></div>` : ''}
      ${locked ? RESULT_LOCKED : ''}
      ${cr ? liveRows([['Voltage drop', esc(short(Math.abs(cr.v), 'V')), 'q-v'], ['Current through', esc(short(Math.abs(cr.i), 'A')), 'q-i'],
        ['Power', `${esc(short(cr.p, 'W'))} <small>(${pct < 1 ? '<1' : Math.round(pct)}% of rating)</small>`, pct > 100 ? 'bad' : pct > 50 ? 'warm' : '']]) : ''}`;
  } else if (c.type === 'reqblock') {
    const solved = isSolved(c);
    const R = equivalentR(c.inner).R;
    body = solved
      ? liveRows([['Req', esc(R === Infinity ? 'open' : short(R, 'Ω')), 'q-r'],
        ...(cr ? [['Voltage drop', esc(short(Math.abs(cr.v), 'V')), 'q-v'], ['Current through', esc(short(Math.abs(cr.i), 'A')), 'q-i']] : [])])
      : '<p class="help">Req = ? Open the block, build its inside between A and B, then check your Req. Its I and V show here once it checks out.</p>';
    body += `<div class="row-btns"><button class="btn primary" data-act="open-block">Open</button>
      <button class="btn" data-act="expand" aria-pressed="${!!c.expanded}">${c.expanded ? 'Hide inside' : 'Show inside on board'}</button></div>`;
  } else if (c.type === 'vsource') {
    const battery = c.style === 'battery';
    const ex = cr && cr.extra;
    body = `<div class="field"><span>Preset</span><div class="seg wide">${[['bench', 'Bench supply'], ['battery9v', '9 V battery'], ['batteryAA', 'AA cell']]
      .map(([k, l]) => `<button data-preset="${k}">${l}</button>`).join('')}</div></div>
      ${field('Voltage', 'V', short(p.V, 'V'), { unit: 'V' })}
      ${battery ? '' : field('Current limit', 'ilimit', p.ilimit > 0 ? short(p.ilimit, 'A') : '', { unit: 'A', placeholder: 'none',
        help: 'Leave empty for no limit. A bench supply drops into CC mode at this current.' })}
      ${field('Internal resistance', 'r', short(p.r, 'Ω'), { unit: 'Ω', help: battery ? 'A 9 V alkaline is around 1–2 Ω; a car battery is about 0.01 Ω.' : '' })}
      ${ex ? liveRows([['Mode', `<span class="lamp ${ex.mode === 'CC' ? 'amber' : 'go'}"></span> ${ex.mode === 'CC' ? 'CC (current limit)' : 'CV'}`],
        ['Output', esc(short(ex.terminalVoltage, 'V')), 'q-v'], ['Current', esc(short(ex.supplyCurrent, 'A')), 'q-i'], ['Power out', esc(short(ex.delivered, 'W'))]]) : ''}`;
  } else if (c.type === 'switch') {
    body = `<div class="row-btns"><button class="btn primary" data-act="toggle">${p.closed ? 'Open the switch' : 'Close the switch'}</button></div>
      <p class="help">It's ${p.closed ? 'closed (conducting)' : 'open (no connection)'}. Double-click it on the board to flip it.</p>
      ${cr && p.closed ? liveRows([['Current through', esc(short(Math.abs(cr.i), 'A'))]]) : ''}`;
  } else if (c.type === 'ground') {
    body = '<p class="help">Ground is 0 V. Every voltage is measured from here.</p>';
  } else if (c.port) {
    body = `<p class="help">Port ${esc(c.id)} is where ${esc(S.path.at(-1))} meets the rest of the circuit. Wire the inside between A and B. Drag it to move.</p>`;
  } else if (c.type === 'junction') {
    body = `<p class="help">A connection point. Drag it to move; wires follow.</p>${cr ? '' : ''}`;
  }
  const label = c.port ? 'Port' : { resistor: 'Resistor', vsource: c.style === 'battery' ? 'Battery' : 'DC supply', isource: 'Current source',
    switch: 'Switch', ground: 'Ground', junction: 'Junction', reqblock: 'Req block' }[c.type];
  el.innerHTML = `<div class="card-head"><span class="label">Selected</span>${close}<h2>${esc(c.id)} · ${esc(label)}</h2></div>
    ${body}
    ${c.port ? '' : `<div class="row-btns">${c.type === 'junction' ? '' : '<button class="btn" data-act="rotate">Rotate (R)</button>'}
      <button class="link danger" data-act="delete">Delete</button></div>`}`;
}

/* ------------------------------------------------------------ Req window */

function renderSubwin(m) {
  const blk = blockAt(S.circuit, S.path);
  if (!blk) return;
  const gid = S.path.join('/');
  $('swCrumbs').innerHTML = `<button class="crumb" data-act="crumb" data-depth="0">Main board</button>${S.path.map((id, k) => `<span class="sep">›</span>${
    k === S.path.length - 1 ? `<b>${esc(id)}</b>` : `<button class="crumb" data-act="crumb" data-depth="${k + 1}">${esc(id)}</button>`}`).join('')}`;
  const eq = equivalentR(blk.inner);
  const solved = isSolved(blk);
  const msg = S.reqMsg && S.reqMsg.id === gid ? S.reqMsg : null;
  let html = `<div class="card-head"><span class="label">Req check</span><h2>${esc(blk.id)} = <span class="${solved ? 'q-r' : 'q'}">${
    solved ? esc(eq.R === Infinity ? 'open' : short(eq.R, 'Ω')) : '?'}</span></h2></div>`;
  if (eq.R === null) {
    html += `<p class="help">Fix the problem inside first: ${esc(eq.reason || 'it can’t be solved.')}</p>`;
  } else if (eq.R === Infinity && !solved) {
    html += '<p class="help">A and B aren’t connected yet. Wire resistors from A to B, using the parts on the left.</p>';
  } else if (!solved) {
    const draft = S.drafts[gid] ?? '';
    html += `<p class="help">Work out the resistance between A and B, then type it in.</p>
      <label class="field"><span>Your Req</span><input class="num" data-guess value="${esc(draft)}" placeholder="e.g. 92.6 or 4.7k"
        autocomplete="off" spellcheck="false"></label>
      <div class="row-btns"><button class="btn primary" data-act="req-check">Check</button>
        <button class="link" data-act="req-show">Show me</button></div>
      ${msg && !msg.ok ? `<div class="verdict ${msg.close ? 'amber' : 'stop'}"><span class="lamp ${msg.close ? 'amber' : 'stop'}"></span><div><b>${
        msg.close ? 'Close' : 'Not yet'}</b><p>${esc(msg.text)}</p></div></div>` : ''}
      <p class="help small">The meter works in here. Each part’s I and V unlock once your Req checks out.</p>`;
  } else {
    const how = blk.check.how === 'shown' ? 'Shown, not checked.' : 'Checked.';
    html += `<p class="okline"><span class="lamp go"></span> ${how} Change a value inside and it locks again, so you can predict the new Req.</p>`;
    html += checksHTML(blockChecks(S.circuit, S.path, m.result), blk.id);
  }
  const side = $('swSide');
  if (side.dataset.html !== html) { side.innerHTML = html; side.dataset.html = html; }
}

function checksHTML(k, name) {
  if (!k) return '<p class="help">Fix the circuit problems listed under Circuit check to see the live values.</p>';
  const A = (x) => `<span class="q-i">${esc(short(Math.abs(x), 'A'))}</span>`;
  const V = (x) => `<span class="q-v">${esc(short(Math.abs(x), 'V'))}</span>`;
  const same = (a, b) => Math.abs(a - b) <= 1e-6 * Math.max(Math.abs(a), Math.abs(b)) + 1e-12;
  const sum = (terms, f, key) => terms.map((t, j) => `${j ? (t[key] < 0 ? ' − ' : ' + ') : t[key] < 0 ? '− ' : ''}${f(t[key])}<small>${esc(t.id)}</small>`).join('');
  let h = liveRows([[`Drop across ${name}`, V(k.block.v), 'q-v'], [`Through ${name}`, A(k.block.i), 'q-i']]);
  if (Math.abs(k.block.i) < 1e-12) h += `<p class="help small">No current flows through ${esc(name)} right now. Connect it to a supply on the main board to see the checks fill in.</p>`;
  h += '<h3 class="eq-h">Current (KCL)</h3>';
  for (const line of k.kcl) {
    if (!line.terms.length) continue;
    h += `<div class="eq">At ${line.at}: ${sum(line.terms, A, 'i')} = ${A(line.total)} ${same(line.total, k.block.i)
      ? `<span class="okmark">✓ matches the current through ${esc(name)}</span>` : ''}</div>`;
  }
  if (k.kvl.length) {
    h += '<h3 class="eq-h">Voltage drops (KVL), each path A → B</h3>';
    for (const line of k.kvl) {
      h += `<div class="eq">${sum(line.terms, V, 'v')} = ${V(line.total)} ${same(line.total, k.vab) ? `<span class="okmark">✓ matches the drop across ${esc(name)}</span>` : ''}</div>`;
    }
  }
  return h;
}

function openBlock(id) {
  const c = comp(id);
  if (!c || c.type !== 'reqblock') return;
  if (S.pending) cancelWire();
  if (!c.inner) c.inner = emptyInner();
  S.viewStack.push(S.view);
  S.path = [...S.path, id];
  S.view = { x: -60, y: -40, scale: 1 };
  Object.assign(S, { sel: null, tool: 'select', armed: null, ghostAt: null, highlight: new Set() });
  render();
  fit();
  render();
}

/** Close open blocks down to `depth` (0 = back to the main board), selecting the block just closed. */
function closeTo(depth, { quiet = false } = {}) {
  if (S.path.length <= depth) return;
  if (S.pending) cancelWire();
  let last = null;
  while (S.path.length > depth) { last = S.path.pop(); S.view = S.viewStack.pop() || S.view; }
  Object.assign(S, { sel: quiet ? null : { kind: 'comp', id: last }, tool: 'select', armed: null, ghostAt: null });
  if (!quiet) { setViewBox(); render(); }
}

/* -------------------------------------------------------------- meter */

function attLabel(att) {
  if (!att) return null;
  const term = globalAttachTerm(S.circuit, att);
  const node = S.last && S.last.base.ok ? S.last.base.nodeName(term) : null;
  if (att.kind === 'pin') {
    const [id, pin] = att.term.split('.');
    const f = findGlobal(S.circuit, id);
    const c = f && f.item;
    const pinName = c && (c.type === 'vsource' || c.type === 'isource') ? (pin === 'p' ? '+' : '−')
      : c && c.type === 'junction' ? '' : c && c.type === 'ground' ? '' : ` pin ${pin}`;
    return `${pretty(c && c.port ? `${id} port` : id)}${pinName && !(c && c.port) ? ` ${pinName}` : ''}${node ? ` · ${node}` : ''}`;
  }
  const fw = findGlobal(S.circuit, att.id);
  const w = fw && fw.item;
  return `${pretty(att.id)}${w && w.cut ? ` (cut, ${att.t > 0.5 ? 'right' : 'left'} end)` : ''}${node ? ` · ${node}` : ''}`;
}

function renderMeter(m) {
  const tone = m.fuse ? m.fuse.tone : m.warnings.some((x) => x.level === 'danger') ? 'stop' : null;
  const dragging = S.probeDrag && S.probeDrag.moved;
  const chips = ['red', 'black'].map((which) => {
    const placed = S.probes[which];
    const status = S.armed === which ? 'Tap the circuit to place it'
      : placed ? `on ${esc(attLabel(placed))}` : 'Drag onto the circuit';
    return `<button class="probe-chip ${which} ${placed ? 'placed' : ''} ${S.armed === which ? 'armed' : ''}" data-probe-chip="${which}">
      <span class="tipdot"></span><b>${which === 'red' ? 'Red' : 'Black'} probe</b><small>${status}</small></button>`;
  }).join('');

  let verdict = '';
  const blown = Object.entries(S.meter.fuses).filter(([, v]) => v === 'blown').map(([k]) => k);
  if (S.blowEvent) {
    const v = S.blowEvent.verdict;
    verdict = `<div class="verdict stop big"><span class="lamp stop strike"></span><div><b>FUSE BLOWN</b>
      <p>${esc(v.message)}</p></div></div>`;
  } else if (m.fuse) {
    const pre = dragging && m.fuse.tier === 'blows' ? 'Drop here and the fuse blows. ' : '';
    verdict = `<div class="verdict ${m.fuse.tone}"><span class="lamp ${m.fuse.tone}"></span><div><b>${esc(m.fuse.label)}</b>
      <p>${esc(pre + m.fuse.message)}</p></div></div>`;
  } else if (!m.placed) {
    verdict = `<p class="help">${S.probes.red || S.probes.black ? 'Place the other probe to measure.'
      : 'Drag the red and black probes onto the circuit, or tap a probe and then tap the circuit.'}</p>`;
  }

  const warnings = m.warnings.filter((x) => x.code !== 'fuse-blown' || !S.blowEvent).map((x) => `<div class="mwarn ${x.level}">
    <span class="lamp ${x.level === 'danger' ? 'stop' : x.level === 'warning' ? 'amber' : 'go'}"></span>
    <div><b>${esc(x.title)}</b><p>${esc(x.message)}</p></div></div>`).join('');

  $('meterInner').innerHTML = `<div class="card-head"><span class="label">Multimeter</span>
      <span class="model">${esc(profile.name)}</span></div>
    <div class="dmm-wrap">${meterFace({ profile, meter: S.meter, display: m.display, tone, blownNow: !!S.blowEvent })}</div>
    <p class="help center small">Click the dial to change setting. Click a jack to move the red lead.</p>
    <div class="probe-row">${chips}</div>
    ${verdict}
    ${warnings}
    <div class="row-btns">
      ${blown.length ? `<button class="btn primary" data-act="replace-fuse">Replace ${blown.map((f) => profile.fuses[f].label.split(' 1000')[0]).join(' and ')} fuse</button>` : ''}
      ${S.probes.red || S.probes.black ? '<button class="link" data-act="park">Remove probes</button>' : ''}
    </div>`;
}

/* -------------------------------------------------------------- issues */

function renderIssues(m) {
  const res = m.result;
  const list = userIssues(res).filter((i) => i.code !== 'empty');
  const el = $('issues');
  if (!S.circuit.components.length) { el.innerHTML = ''; el.hidden = true; return; }
  el.hidden = false;
  const lvl = (l) => (l === 'error' ? 'stop' : l === 'warning' ? 'amber' : 'go');
  el.innerHTML = `<div class="card-head"><span class="label">Circuit check</span></div>
    ${list.length ? list.map((i) => `<button class="issue ${i.level}" data-ids="${esc((i.ids || []).join(','))}">
      <span class="lamp ${lvl(i.level)}"></span><span>${esc(i.message.replace(/\b((?:Req\d+\/)+)/g, (x) => x.replace(/\//g, ' › ')))}</span></button>`).join('')
    : '<p class="ok"><span class="lamp go"></span> No problems found.</p>'}`;
}

/* -------------------------------------------------------------- tooltip */

function showTip(e) {
  const tip = $('tip');
  const hit = e.target.closest && e.target.closest('[data-hit]');
  const m = S.last;
  if (!hit || !m || !m.result.ok || S.probeDrag || S.pending) { tip.hidden = true; return; }
  const r = scoped(m.result, pre());
  const locked = lockedAt();
  let html = '';
  if (hit.dataset.hit === 'comp') {
    const c = comp(hit.dataset.id), cr = r.components[hit.dataset.id];
    if (!c || !cr || c.type === 'ground') { tip.hidden = true; return; }
    if (c.type === 'reqblock' && !isSolved(c)) html = `<b>${esc(c.id)}</b> Req = ?<br>Double-click to open it`;
    else if (locked) html = `<b>${esc(c.id)}</b> <span class="t-r">${esc(c.type === 'resistor' ? short(c.params.R, 'Ω') : '')}</span><br>I and V unlock after the Req check`;
    else {
      const R = c.type === 'resistor' ? c.params.R : c.type === 'reqblock' ? equivalentR(c.inner).R : null;
      html = `<b>${esc(c.id)}</b> <span class="t-r">${esc(R !== null ? short(R, 'Ω') : '')}</span><br>
      <span class="t-v">${esc(short(Math.abs(cr.v), 'V'))}</span> drop · <span class="t-i">${esc(short(Math.abs(cr.i), 'A'))}</span>${
  cr.type === 'resistor' ? ` · ${esc(short(cr.p, 'W'))}` : ''}`;
    }
  } else if (locked) {
    tip.hidden = true; return;
  } else if (hit.dataset.hit === 'wire') {
    const wr = r.wires[hit.dataset.id];
    if (!wr) { tip.hidden = true; return; }
    if (wr.cut) html = `<b>${esc(wr.id)}</b> cut · ${esc(wr.ends.join(' | '))}`;
    else {
      const n = r.nodes.find((x) => x.name === wr.node);
      html = `<b>${esc(wr.node)}</b> <span class="t-v">${n && !n.floating ? esc(short(n.v, 'V')) : 'floating'}</span><br><span class="t-i">${esc(short(Math.abs(wr.i), 'A'))}</span> in ${esc(wr.id)}`;
    }
  } else if (hit.dataset.hit === 'pin') {
    const name = r.nodeName(hit.dataset.term);
    const n = r.nodes.find((x) => x.name === name);
    if (!n) { tip.hidden = true; return; }
    html = `<b>${esc(name)}</b> <span class="t-v">${n.floating ? 'floating' : esc(short(n.v, 'V'))}</span>`;
  } else { tip.hidden = true; return; }
  const box = $('boardWrap').getBoundingClientRect();
  tip.innerHTML = html;
  tip.hidden = false;
  tip.style.transform = `translate(${Math.min(e.clientX - box.left + 14, box.width - 190)}px, ${e.clientY - box.top + 16}px)`;
}

/* ================================================================ input */

function track(handlers) {
  const move = (e) => handlers.move && handlers.move(e);
  const up = (e) => {
    window.removeEventListener('pointermove', move);
    window.removeEventListener('pointerup', up);
    window.removeEventListener('pointercancel', up);
    handlers.up && handlers.up(e);
  };
  window.addEventListener('pointermove', move);
  window.addEventListener('pointerup', up);
  window.addEventListener('pointercancel', up);
}

const hitUnder = (e) => {
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const h = el && el.closest('[data-hit]');
  return h && svg().contains(h) ? h.dataset : {};
};

function onBoardDown(e) {
  if (e.pointerType === 'mouse' && e.button !== 0) return;
  $('tip').hidden = true;
  const p = toWorld(e);
  const hitEl = e.target.closest('[data-hit]');
  const hit = hitEl ? hitEl.dataset : {};
  const start = [e.clientX, e.clientY];
  const movedFar = (ev) => Math.hypot(ev.clientX - start[0], ev.clientY - start[1]) > 5;

  if (S.armed) {
    const t = findTarget(indexCircuit(cur()), cur(), p, { pinRadius: 22 / S.view.scale, wireRadius: 16 / S.view.scale });
    const which = S.armed;
    S.armed = null;
    if (t) commit(() => { S.probes[which] = toAtt(t); });
    else render();
    return;
  }
  const pal = PALETTE.find((x) => x.key === S.tool && x.type);
  if (pal) { placePart(pal.key, p); S.tool = 'select'; S.ghostAt = null; render(); return; }

  if (hit.hit === 'probe') { startProbeDrag(hit.probe, e); return; }

  if (S.pending) {
    finishWire(p, hit.hit === 'pin' ? hit.term : null, { chain: true });
    return;
  }

  if (hit.hit === 'pin' && hit.junction && S.tool !== 'wire') {
    // a junction: drag to move it, click to start a wire from it
    const j = comp(hit.junction);
    const orig = { ...j.layout };
    let moved = false;
    track({
      move(ev) {
        if (!moved && !movedFar(ev)) return;
        if (!moved) { moved = true; pushUndo(); }
        const q = toWorld(ev);
        j.layout.x = snap(orig.x + q[0] - p[0]);
        j.layout.y = snap(orig.y + q[1] - p[1]);
        render();
      },
      up() { if (moved) afterChange(); else startWire(p, hit.term); },
    });
    return;
  }

  if (hit.hit === 'pin' || S.tool === 'wire') {
    startWire(p, hit.hit === 'pin' ? hit.term : null);
    track({
      move(ev) { if (S.pending) { S.pending.to = toWorld(ev); render(); } },
      up(ev) {
        if (!S.pending || !movedFar(ev)) return;          // a click: keep drawing until the next click
        const h = hitUnder(ev);
        finishWire(toWorld(ev), h.hit === 'pin' ? h.term : null, { chain: false });
      },
    });
    return;
  }

  if (hit.hit === 'comp') {
    // Double-click, detected here: each click redraws the board, so the browser's own dblclick never fires.
    const now = performance.now();
    const again = S.lastDown && S.lastDown.id === hit.id && S.lastDown.depth === S.path.length && now - S.lastDown.t < 450;
    S.lastDown = again ? null : { id: hit.id, depth: S.path.length, t: now };
    if (again) { partDoubleClick(hit.id); return; }
    S.sel = { kind: 'comp', id: hit.id };
    S.highlight = new Set();
    const c = comp(hit.id);
    const orig = { ...c.layout };
    let moved = false;
    render();
    track({
      move(ev) {
        if (!moved && !movedFar(ev)) return;
        if (!moved) { moved = true; pushUndo(); }
        const q = toWorld(ev);
        c.layout.x = snap(orig.x + q[0] - p[0]);
        c.layout.y = snap(orig.y + q[1] - p[1]);
        render();
      },
      up() { if (moved) afterChange(); },
    });
    return;
  }
  if (hit.hit === 'wire') {
    S.sel = { kind: 'wire', id: hit.id };
    S.highlight = new Set();
    render();
    return;
  }

  // empty board: deselect and pan
  S.sel = null;
  S.highlight = new Set();
  render();
  const v0 = { ...S.view };
  track({
    move(ev) {
      S.view.x = v0.x - (ev.clientX - start[0]) / S.view.scale;
      S.view.y = v0.y - (ev.clientY - start[1]) / S.view.scale;
      setViewBox();
    },
  });
}

function partDoubleClick(id) {
  const c = comp(id);
  if (!c) return;
  S.sel = { kind: 'comp', id };
  if (c.type === 'switch') { act('toggle'); return; }
  if (c.type === 'reqblock') { openBlock(c.id); return; }
  render();
  const input = $('inspector').querySelector('input.num');
  if (input) { input.focus(); input.select(); }
}

function startProbeDrag(which, e) {
  const start = [e.clientX, e.clientY];
  S.probeDrag = { which, client: start, moved: false, target: null, overBoard: false, world: null };
  track({
    move(ev) {
      const d = S.probeDrag;
      if (!d) return;
      if (!d.moved && Math.hypot(ev.clientX - start[0], ev.clientY - start[1]) < 5) return;
      d.moved = true;
      d.client = [ev.clientX, ev.clientY];
      const r = svg().getBoundingClientRect();
      d.overBoard = ev.clientX >= r.left && ev.clientX <= r.right && ev.clientY >= r.top && ev.clientY <= r.bottom;
      d.world = d.overBoard ? toWorld(ev) : null;
      d.target = d.overBoard ? findTarget(indexCircuit(cur()), cur(), d.world, { pinRadius: 16 / S.view.scale, wireRadius: 12 / S.view.scale }) : null;
      render();
    },
    up() {
      const d = S.probeDrag;
      S.probeDrag = null;
      if (!d) return;
      if (!d.moved) { S.armed = S.armed === which ? null : which; render(); return; }
      S.armed = null;
      commit(() => { S.probes[which] = d.target ? toAtt(d.target) : null; });
    },
  });
  render();
}

function onBoardMove(e) {
  if (S.probeDrag) return;
  const pal = PALETTE.find((x) => x.key === S.tool && x.type);
  if (pal) { S.ghostAt = toWorld(e); render(); return; }
  if (S.pending && e.buttons === 0) { S.pending.to = toWorld(e); render(); return; }
  if (e.pointerType === 'mouse' && e.buttons === 0) showTip(e);
}

function onKey(e) {
  if (e.target.closest('input, select, textarea')) {
    if (e.key === 'Escape') e.target.blur();
    return;
  }
  const mod = e.ctrlKey || e.metaKey;
  if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
  if (mod && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); return; }
  if (mod) return;
  if (e.key === 'Escape') {
    if (S.path.length && !S.pending && !S.sel && !S.armed && S.tool === 'select') { closeTo(S.path.length - 1); return; }
    if (S.pending) cancelWire();
    S.tool = 'select'; S.ghostAt = null; S.armed = null; S.sel = null; S.highlight = new Set();
    render();
  } else if (e.key === 'r' || e.key === 'R') {
    const pal = PALETTE.find((x) => x.key === S.tool && x.type);
    if (pal) { S.ghostRot = (S.ghostRot + 1) % 4; render(); } else act('rotate');
  } else if (e.key === 'Delete' || e.key === 'Backspace') {
    if (S.sel) { e.preventDefault(); act('delete'); }
  } else if (e.key === 'w' || e.key === 'W') { setTool('wire'); }
}

function setTool(key) {
  if (S.pending) cancelWire();
  S.tool = S.tool === key && key !== 'select' ? 'select' : key;
  S.ghostAt = null;
  S.armed = null;
  if (S.tool !== 'select') S.sel = null;
  render();
}

/** Actions from buttons and keys. */
function act(name, el) {
  const item = findSel();
  switch (name) {
    case 'rotate':
      if (!item) return;
      if (S.sel.kind === 'wire') return act('flip');
      if (item.type === 'junction') return;
      commit(() => { item.layout.rot = ((item.layout.rot || 0) + 1) % 4; });
      return;
    case 'flip':
      if (S.sel && S.sel.kind === 'wire') commit(() => { item.layout = { ...(item.layout || {}), bend: (item.layout && item.layout.bend) === 'vh' ? 'hv' : 'vh' }; });
      return;
    case 'delete':
      if (!item) return;
      if (item.port) { toast(`Ports A and B are ${S.path.at(-1)}'s two ends. They stay.`); return; }
      commit(() => { if (S.sel.kind === 'wire') removeWire(item.id); else removeComponent(item.id); S.sel = null; });
      return;
    case 'cut':
      commit(() => { item.cut = !item.cut; });
      return;
    case 'toggle':
      commit(() => { item.params.closed = !item.params.closed; });
      return;
    case 'replace-fuse':
      // Changing a fuse means opening the meter, so the leads come off the circuit first.
      S.meter.fuses = { mA: 'ok', A: 'ok' };
      S.blowEvent = null;
      S.probes = { red: null, black: null };
      afterChange();
      toast('New fuse in. The probes came off the circuit; place them again.');
      return;
    case 'deselect':
      S.sel = null;
      render();
      return;
    case 'demo-prev':
      if (S.demo && S.demo.step > 0) applyDemoStep(S.demo.step - 1);
      return;
    case 'demo-next':
      if (S.demo) applyDemoStep((S.demo.step + 1) % DEMO_STEPS.length);
      return;
    case 'demo-exit':
      S.demo = null;
      render();
      return;
    case 'park':
      commit(() => { S.probes = { red: null, black: null }; });
      return;
    case 'open-block':
      if (item && item.type === 'reqblock') openBlock(item.id);
      return;
    case 'expand':
      if (item && item.type === 'reqblock') commit(() => { if (item.expanded) delete item.expanded; else item.expanded = true; });
      return;
    case 'close-block':
      closeTo(S.path.length - 1);
      return;
    case 'crumb':
      closeTo(Number(el.dataset.depth));
      return;
    case 'sw-fit':
      fit();
      return;
    case 'req-check': {
      const blk = blockAt(S.circuit, S.path);
      if (!blk) return;
      const gid = S.path.join('/');
      const input = $('swSide').querySelector('[data-guess]');
      const raw = input ? input.value.trim() : '';
      S.drafts[gid] = raw;
      const g = parseEng(raw);
      if (g === null || g < 0) { S.reqMsg = { id: gid, ok: false, text: 'Type a resistance like 92.6, 4.7k or 1M.' }; render(); return; }
      const res = gradeGuess(blk.inner, g);
      if (res.ok) {
        S.reqMsg = { id: gid, ok: true };
        delete S.drafts[gid];
        commit(() => { blk.check = { R: equivalentR(blk.inner).R, how: 'checked' }; });
        toast(`Correct: ${blk.id} = ${short(equivalentR(blk.inner).R, 'Ω')}. I and V are unlocked inside.`);
      } else {
        S.reqMsg = { id: gid, ok: false, close: !!res.close, text: res.hint };
        render();
      }
      return;
    }
    case 'req-show': {
      const blk = blockAt(S.circuit, S.path);
      if (!blk) return;
      S.reqMsg = null;
      commit(() => { blk.check = { R: equivalentR(blk.inner).R, how: 'shown' }; });
      return;
    }
    default:
  }
  void el;
}

function onPanelClick(e) {
  const t = e.target;
  const btn = t.closest('[data-act]');
  if (btn) { act(btn.dataset.act, btn); return; }
  const dialEl = t.closest('[data-dial]');
  if (dialEl) { setDial(dialEl.dataset.dial); return; }
  const jackEl = t.closest('[data-jack]');
  if (jackEl) { setJack(jackEl.dataset.jack); return; }
  const step = t.closest('[data-demo-step]');
  if (step) { applyDemoStep(Number(step.dataset.demoStep)); return; }
  const ser = t.closest('[data-series]');
  if (ser) { S.series = ser.dataset.series; render(); return; }
  const pre = t.closest('[data-preset]');
  if (pre) {
    const c = findSel();
    commit(() => {
      Object.assign(c.params, PRESETS[pre.dataset.preset]);
      c.style = pre.dataset.preset === 'bench' ? undefined : 'battery';
      if (!c.style) delete c.style;
    });
    return;
  }
  const issue = t.closest('.issue[data-ids]');
  if (issue) { S.highlight = new Set(issue.dataset.ids.split(',').filter(Boolean)); render(); }
}

function setDial(id) {
  S.meter.dial = id;
  S.blowEvent = null;
  afterChange();
}
function setJack(id) {
  if (jackOf(profile, id).kind === 'common') { toast('The black lead stays in COM. Click another jack to move the red lead.'); return; }
  S.meter.red = id;
  S.blowEvent = null;
  afterChange();
}

function onPanelChange(e) {
  const t = e.target;
  const c = findSel();
  if (!c) return;
  if (t.matches('input.num')) {
    const raw = t.value.trim();
    const key = t.dataset.param;
    if (key === 'ilimit' && raw === '') { commit(() => { c.params.ilimit = null; }); return; }
    const v = parseEng(raw);
    const bad = v === null || ((key === 'R' || key === 'ilimit') && !(v > 0)) || (key === 'r' && v < 0);
    if (bad) {
      t.classList.add('bad');
      t.setCustomValidity('Use a number like 4.7k, 220 or 1M');
      t.reportValidity();
      return;
    }
    commit(() => { c.params[key] = v; });
  } else if (t.matches('[data-pick]')) {
    if (t.value) commit(() => { c.params.R = Number(t.value); });
  } else if (t.matches('[data-param-select]')) {
    commit(() => { c.params[t.dataset.paramSelect] = Number(t.value); });
  }
}

let toastTimer = 0;
function toast(text) {
  const el = $('toast');
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 3200);
}

/* ================================================================ boot */

async function boot() {
  try {
    profile = await (await fetch('/static/circuit/meters/fluke-87v.json')).json();
  } catch {
    $('status').textContent = "Couldn't load the meter profile. Check your connection and reload.";
    return;
  }
  let loaded = false;
  const hash = location.hash.match(/^#c=(.+)$/);
  if (hash) {
    loaded = loadState(await decodeShare(hash[1]));
    if (!loaded) toast("That share link didn't contain a circuit.");
    history.replaceState(null, '', location.pathname);
  }
  if (!loaded) loaded = loadState(store.get());
  const wantDemo = location.hash === '#demo';
  if (wantDemo) history.replaceState(null, '', location.pathname);

  for (const board of [$('board'), $('subBoard')]) {
    board.addEventListener('pointerdown', onBoardDown);
    board.addEventListener('pointermove', onBoardMove);
    board.addEventListener('pointerleave', () => { $('tip').hidden = true; if (S.ghostAt) { S.ghostAt = null; render(); } });
    board.addEventListener('wheel', (e) => { e.preventDefault(); zoomAt(Math.exp(-e.deltaY * 0.0015), e.clientX, e.clientY); }, { passive: false });
    new ResizeObserver(() => setViewBox()).observe(board);
  }
  $('swHead').addEventListener('click', onPanelClick);
  $('swSide').addEventListener('click', onPanelClick);
  $('swSide').addEventListener('input', (e) => { if (e.target.matches('[data-guess]')) S.drafts[S.path.join('/')] = e.target.value; });
  $('swSide').addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.matches('[data-guess]')) { e.preventDefault(); act('req-check'); } });
  $('palette').addEventListener('click', (e) => { const b = e.target.closest('[data-tool]'); if (b) setTool(b.dataset.tool); });
  for (const id of ['inspector', 'demoCard', 'meterCard', 'issues']) {
    $(id).addEventListener('click', onPanelClick);
    $(id).addEventListener('change', onPanelChange);
    $(id).addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && e.target.matches('input.num')) e.target.blur();
      if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[data-dial], [data-jack]')) { e.preventDefault(); onPanelClick(e); }
    });
    $(id).addEventListener('input', (e) => { if (e.target.matches('input.num')) { e.target.classList.remove('bad'); e.target.setCustomValidity(''); } });
  }
  $('meterCard').addEventListener('pointerdown', (e) => {
    const chip = e.target.closest('[data-probe-chip]');
    if (chip) { e.preventDefault(); startProbeDrag(chip.dataset.probeChip, e); }
  });
  $('meterCard').addEventListener('animationend', () => $('meterCard').classList.remove('blowing'));
  $('undoBtn').onclick = undo;
  $('redoBtn').onclick = redo;
  $('overlayBtn').onclick = () => { S.overlay = !S.overlay; save(); render(); };
  $('shareBtn').onclick = share;
  $('clearBtn').onclick = clearBoard;
  $('fitBtn').onclick = fit;
  $('zoomIn').onclick = () => zoomAt(1.25);
  $('zoomOut').onclick = () => zoomAt(0.8);
  $('examples').onchange = (e) => {
    const v = e.target.value;
    e.target.value = '';
    if (!v) return;
    if (S.circuit.components.length && !window.confirm('Replace the circuit on the board?')) return;
    if (v === 'demo') { startDemo(); return; }
    S.demo = null;
    closeTo(0, { quiet: true });
    commit(() => { S.circuit = example(v); S.probes = { red: null, black: null }; S.sel = null; });
    fit();
    render();
  };
  window.addEventListener('keydown', onKey);

  if (wantDemo) { startDemo(); return; }
  render();
  fit();
  render();
}

boot();
