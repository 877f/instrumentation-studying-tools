/* Req block helpers that don't touch the DOM: walking the block tree, working out Req,
   word-only hints for a wrong guess, and the KCL / KVL check lines shown once Req is solved.

   Ids: inside a block, parts keep their own short ids ("R2"). Anywhere the whole circuit is
   meant (probes, solve results, issues) an inner part goes by its path: "Req1/R2". */

import { solve } from './solver.js';
import { buildNetlist } from './netlist.js';
import { registry } from '../components/registry.js';

const TWO_PIN = new Set(['resistor', 'reqblock']);

/** The circuit inside the block at `path` (['Req1', 'Req3']), the root for [], or null. */
export function scopeAt(root, path) {
  let c = root;
  for (const id of path) {
    const b = c && c.components.find((x) => x.id === id && x.type === 'reqblock');
    if (!b) return null;
    c = b.inner;
  }
  return c;
}

/** The block component at `path` (its last id), or null for the root. */
export function blockAt(root, path) {
  if (!path.length) return null;
  const parent = scopeAt(root, path.slice(0, -1));
  return parent ? parent.components.find((x) => x.id === path.at(-1) && x.type === 'reqblock') || null : null;
}

/** A component or wire by its global id ("Req1/R2", "Req1/W4"): { kind: 'comp'|'wire', item } or null. */
export function findGlobal(root, gid) {
  const parts = gid.split('/');
  const scope = scopeAt(root, parts.slice(0, -1));
  if (!scope) return null;
  const id = parts.at(-1);
  const comp = scope.components.find((x) => x.id === id);
  if (comp) return { kind: 'comp', item: comp };
  const wire = scope.wires.find((x) => x.id === id);
  return wire ? { kind: 'wire', item: wire } : null;
}

/** Every component id anywhere in the tree, so new resistors and blocks get names unique across all levels. */
export function allIds(root, out = new Set()) {
  for (const c of root.components) {
    out.add(c.id);
    if (c.type === 'reqblock' && c.inner) allIds(c.inner, out);
  }
  return out;
}

export function nextTreeId(root, prefix) {
  const used = allIds(root);
  let n = 1;
  while (used.has(`${prefix}${n}`)) n++;
  return `${prefix}${n}`;
}

/** The terminal a (global) probe attachment touches, in the flattened circuit's names. */
export function globalAttachTerm(root, att) {
  if (!att) return null;
  if (att.kind === 'pin') return att.term;
  const f = findGlobal(root, att.id);
  if (!f || f.kind !== 'wire') return null;
  return f.item.cut && att.t > 0.5 ? `${att.id}.b` : `${att.id}.a`;
}

/* ------------------------------------------------------------------ Req */

const electrical = (inner) => JSON.stringify(inner, (k, v) => (k === 'layout' || k === 'check' || k === 'expanded' ? undefined : v));
const reqCache = new Map();

/** Resistance between ports A and B: { R } with R a number (Infinity when A and B aren't joined),
    or { R: null, reason } when the inside can't be solved. */
export function equivalentR(inner) {
  const key = electrical(inner);
  if (reqCache.has(key)) return reqCache.get(key);
  const test = {
    components: [...inner.components, { id: '~t', type: 'isource', params: { I: 1 } }],
    wires: [...inner.wires, { id: '~ta', a: '~t.p', b: 'A.j' }, { id: '~tb', a: '~t.n', b: 'B.j' }],
  };
  const r = solve(test);
  let out;
  if (!r.ok) {
    out = r.issues.some((i) => i.code === 'no-return-path') ? { R: Infinity } : { R: null, reason: r.issues.find((i) => i.level === 'error')?.message };
  } else {
    const v = r.voltage('A.j', 'B.j');
    out = v === null ? { R: Infinity } : { R: Math.abs(v) < 1e-12 ? 0 : Math.abs(v) };
  }
  if (reqCache.size > 300) reqCache.clear();
  reqCache.set(key, out);
  return out;
}

/** Has the student checked (or been shown) this block's Req, and is it still the same circuit? */
export function isSolved(block) {
  const ch = block && block.check;
  if (!ch) return false;
  const { R } = equivalentR(block.inner);
  if (R === null) return false;
  if (!Number.isFinite(R) || !Number.isFinite(ch.R)) return R === ch.R;
  return Math.abs(R - ch.R) <= 1e-9 * Math.max(1, R);
}

/** The resistance of the easiest single path from A to B (Req can't be more than this). */
function easiestPath(inner) {
  const net = buildNetlist(inner, registry);
  const a = net.nodeOf('A.j'), b = net.nodeOf('B.j');
  if (a < 0 || b < 0) return Infinity;
  const dist = new Map([[a, 0]]);
  const todo = new Set([a]);
  while (todo.size) {
    let n = null;
    for (const x of todo) if (n === null || dist.get(x) < dist.get(n)) n = x;
    todo.delete(n);
    if (n === b) return dist.get(n);
    for (const c of net.comps) {
      if (c.type !== 'resistor') continue;
      const [p, q] = [c.pins.a, c.pins.b];
      const other = p === n ? q : q === n ? p : null;
      if (other === null) continue;
      const d = dist.get(n) + c.params.R;
      if (!dist.has(other) || d < dist.get(other)) { dist.set(other, d); todo.add(other); }
    }
  }
  return Infinity;
}

/** Grade a guess. Returns { ok, close, hint } — hints are words only, never the formula or the answer. */
export function gradeGuess(inner, guess) {
  const { R } = equivalentR(inner);
  if (!(guess >= 0) || R === null || !Number.isFinite(R)) return { ok: false, hint: '' };
  const err = R === 0 ? Math.abs(guess) : Math.abs(guess - R) / R;
  if (err <= 0.01) return { ok: true };
  if (err <= 0.05) return { ok: false, close: true, hint: 'Close, but not within 1%. Keep more digits in your working and round only at the end.' };
  if (guess > R) {
    const path = easiestPath(inner);
    if (guess >= path * 0.99) {
      return { ok: false, hint: 'Too big. Your answer is at least as big as one single path from A to B. '
        + 'Every extra path gives current another way through, so Req has to come out smaller than any one path on its own.' };
    }
    return { ok: false, hint: 'Too big. Check each branch: are you combining branches that sit side by side the right way? '
      + 'Side-by-side paths always bring the total down.' };
  }
  return { ok: false, hint: 'Too small. Parts one after another on the same path all add their resistance '
    + 'before that path joins the others. Did you leave a part out of a branch?' };
}

/* ----------------------------------------------------------- KCL / KVL */

/**
 * The check lines for the block at `path`, from a solve of the whole circuit:
 * { block: { v, i }, kcl: [{ at: 'A'|'B', terms: [{ id, i }], total }], kvl: [{ terms: [{ id, v }], total }], vab }.
 * Currents in each KCL term flow out of the port into that part; KVL terms are drops along a path A → B.
 */
export function blockChecks(root, path, result) {
  const block = blockAt(root, path);
  if (!block || !result || !result.ok) return null;
  const G = path.join('/'), P = `${G}/`;
  const br = result.components[G];
  if (!br) return null;
  const node = (t) => result.nodeName(P + t);
  const parts = block.inner.components.filter((c) => TWO_PIN.has(c.type) && result.components[P + c.id]);
  const nA = node('A.j'), nB = node('B.j');
  const kcl = [];
  for (const [at, n, sign] of [['A', nA, 1], ['B', nB, -1]]) {
    const terms = [];
    for (const c of parts) {
      const r = result.components[P + c.id];
      for (const pin of ['a', 'b']) if (node(`${c.id}.${pin}`) === n) terms.push({ id: c.id, i: sign * r.pins[pin].i });
    }
    kcl.push({ at, terms, total: terms.reduce((s, t) => s + t.i, 0) });
  }
  // Every simple path of parts from A to B (capped; these are small circuits).
  const vOf = (n) => result.nodes.find((x) => x.name === n)?.v ?? 0;
  const kvl = [];
  const walk = (n, seenNodes, terms) => {
    if (kvl.length >= 6 || terms.length > 8) return;
    if (n === nB && terms.length) { kvl.push({ terms, total: terms.reduce((s, t) => s + t.v, 0) }); return; }
    for (const c of parts) {
      if (terms.some((t) => t.id === c.id)) continue;
      const na = node(`${c.id}.a`), nb = node(`${c.id}.b`);
      const next = na === n ? nb : nb === n ? na : null;
      if (next === null || next === n || seenNodes.has(next)) continue;
      walk(next, new Set([...seenNodes, next]), [...terms, { id: c.id, v: vOf(n) - vOf(next) }]);
    }
  };
  if (nA && nB && nA !== nB) walk(nA, new Set([nA]), []);
  return { block: { v: br.v, i: br.i }, kcl, kvl, vab: nA && nB ? vOf(nA) - vOf(nB) : 0 };
}
