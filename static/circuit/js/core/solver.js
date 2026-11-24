/* Modified Nodal Analysis.

   solve(circuit, { freq }) builds nodes, stamps every component into one complex system,
   solves it, and lets components that change state (a supply going into current limit)
   ask for a re-solve. freq = 0 is DC; AC only needs new stamps that read ctx.omega.

   The result never contains NaN or Infinity. Anything the math can't answer comes back as an
   issue with a plain-English message instead: { level: 'error'|'warning'|'info', code, message, ids }. */

import { Complex } from './complex.js';
import { System, rhsOf, gaussSolve } from './mna.js';
import { buildNetlist, UnionFind } from './netlist.js';
import { formatEng } from './units.js';
import { registry as defaultRegistry } from '../components/registry.js';

const MAX_ITER = 20;
const issue = (level, code, message, ids = []) => ({ level, code, message, ids });
const list = (names) => (names.length < 3 ? names.join(' and ') : `${names.slice(0, -1).join(', ')} and ${names.at(-1)}`);
const pinLabel = (def, pin) => (def.type === 'vsource' || def.type === 'isource' ? (pin === 'p' ? '+' : '−') : pin);

export function solve(circuit, opts = {}) {
  const registry = opts.registry || defaultRegistry;
  const freq = opts.freq || 0;
  const omega = 2 * Math.PI * freq;
  const net = buildNetlist(circuit, registry);
  const issues = [...net.issues];

  if (issues.some((i) => i.level === 'error')) return fail(net, issues, freq);
  if (!net.comps.length) {
    return finish(net, { ok: true, empty: true, freq, nodes: [], components: {}, wires: {},
      issues: [issue('info', 'empty', 'The circuit is empty. Add a supply and some parts.')] });
  }

  const states = new Map(net.comps.map((c) => [c.id, c.def.initState ? c.def.initState(c.params) : {}]));
  let sol = null, settled = false;
  for (let iter = 0; iter < MAX_ITER; iter++) {
    sol = solveOnce(net, states, omega);
    if (sol.error) return fail(net, [...issues, sol.error], freq);
    let changed = false;
    for (const c of net.comps) {
      if (c.def.update && c.def.update(ctxFor(c, states.get(c.id), omega, sol))) changed = true;
    }
    if (!changed) { settled = true; break; }
  }
  if (!settled) {
    issues.push(issue('warning', 'no-settle', 'The current-limited supplies in this circuit keep switching between CV and CC mode, '
      + 'so these values are a best guess.'));
  }
  return results(net, states, omega, sol, issues, freq);
}

/* ------------------------------------------------------------ one solve */

function solveOnce(net, states, omega) {
  const { comps, nodes, ground } = net;

  // Ideal voltage sources in a loop (or shorted) have no answer at all.
  const ideal = new UnionFind();
  const seen = [];
  for (const c of comps) {
    if (!c.def.idealVoltage || !c.def.idealVoltage(c.params, states.get(c.id))) continue;
    const [a, b] = c.def.pins.map((p) => c.pins[p]);
    if (a === b) {
      return { error: issue('error', 'ideal-short', `${c.id} is shorted and has no internal resistance, so the current would be infinite. `
        + 'Give it some internal resistance, or remove the short.', [c.id]) };
    }
    if (!ideal.union(a, b)) {
      const others = seen.filter((s) => ideal.find(s.a) === ideal.find(a)).map((s) => s.id);
      return { error: issue('error', 'ideal-loop', `Ideal voltage sources ${list([...others, c.id])} are connected in parallel or in a loop, `
        + 'with nothing to limit the current between them. Give them internal resistance.', [...others, c.id]) };
    }
    seen.push({ id: c.id, a });
  }

  // Islands: groups of nodes joined by DC-conducting paths.
  const isl = new UnionFind();
  nodes.forEach((n) => isl.add(n.index));
  for (const c of comps) {
    for (const [p, q] of c.def.paths ? c.def.paths(c.params, states.get(c.id)) : []) isl.union(c.pins[p], c.pins[q]);
  }
  const groundIsland = isl.find(ground);
  const islands = new Map();
  for (const n of nodes) {
    const r = isl.find(n.index);
    if (!islands.has(r)) islands.set(r, []);
    islands.get(r).push(n.index);
  }

  // A floating island must have zero net current pushed into it, or KCL can't hold.
  const inject = new Map();
  for (const c of comps) {
    const inj = c.def.injections && c.def.injections(c.params, states.get(c.id));
    if (!inj) continue;
    for (const [p, i] of Object.entries(inj)) {
      const r = isl.find(c.pins[p]);
      if (r === groundIsland) continue;
      const e = inject.get(r) || { total: 0, ids: new Set() };
      e.total += i;
      e.ids.add(c.id);
      inject.set(r, e);
    }
  }
  for (const [r, e] of inject) {
    if (Math.abs(e.total) <= 1e-12) continue;
    const names = islands.get(r).map((i) => nodes[i].name);
    const who = list([...e.ids]);
    return { error: issue('error', 'no-return-path', `${who} ${e.ids.size > 1 ? 'are' : 'is'} pushing current into `
      + `${names.length > 1 ? 'nodes' : 'node'} ${list(names)}, but nothing gives that current a path back. `
      + 'A real current source would drive the voltage there up until something breaks down. Add a return path.', [...e.ids]) };
  }

  // Reference nodes: ground, plus the first node of each floating island.
  const ref = new Set([ground]);
  const floating = new Map();     // node index → island root, for nodes not tied to ground
  for (const [r, members] of islands) {
    if (r === groundIsland) continue;
    ref.add(members[0]);
    members.forEach((m) => floating.set(m, r));
  }

  const idx = new Map();
  let size = 0;
  for (const n of nodes) if (!ref.has(n.index)) idx.set(n.index, size++);
  const branchBase = new Map();
  const branchOwner = new Map();    // matrix column → component id, for error messages
  for (const c of comps) {
    const k = c.def.branches ? c.def.branches(c.params, states.get(c.id)) : 0;
    branchBase.set(c.id, size);
    for (let j = 0; j < k; j++) branchOwner.set(size + j, c.id);
    size += k;
  }

  const A = new System(size);
  const rhs = rhsOf(A);
  const sol = { idx, branchBase, branchOwner, floating, islands, groundIsland, x: [], residual: 0 };
  for (const c of comps) c.def.stamp(A, rhs, ctxFor(c, states.get(c.id), omega, sol));
  if (size === 0) return sol;

  const out = gaussSolve(A);
  if (out.singular !== undefined) return { error: singularIssue(net, sol, out.singular) };
  sol.x = out.x;
  sol.residual = out.residual;
  return sol;
}

function singularIssue(net, sol, col) {
  for (const [node, i] of sol.idx) {
    if (i === col) {
      const name = net.nodes[node].name;
      return issue('error', 'singular', `Node ${name}'s voltage can't be pinned down. Look for a part that's connected to nothing `
        + 'but other ideal parts, or sources fighting each other.');
    }
  }
  const id = sol.branchOwner.get(col);
  if (id) {
    return issue('error', 'singular', `${id}'s current can't be pinned down. It may be in parallel with another source `
      + 'or shorted by ideal parts.', [id]);
  }
  return issue('error', 'singular', "This circuit doesn't have a unique answer. Check for floating parts or sources in a loop.");
}

/* ---------------------------------------------------------------- ctx */

function ctxFor(c, state, omega, sol) {
  const node = (pin) => {
    const n = c.pins[pin];
    return sol.idx.has(n) ? sol.idx.get(n) : -1;
  };
  const base = sol.branchBase.get(c.id);
  return {
    id: c.id,
    params: c.params,
    state,
    omega,
    node,
    branch: (k) => base + k,
    v: (pin) => { const i = node(pin); return i < 0 ? new Complex(0, 0) : (sol.x[i] || new Complex(0, 0)); },
    x: (k) => sol.x[base + k] || new Complex(0, 0),
    complex: (re, im = 0) => new Complex(re, im),
  };
}

/* ------------------------------------------------------------ results */

function results(net, states, omega, sol, issues, freq) {
  const { comps, nodes, ground } = net;
  const vNode = nodes.map((n) => (sol.idx.has(n.index) ? sol.x[sol.idx.get(n.index)] : new Complex(0, 0)));

  // Pin currents (current entering each part at each pin) for parts with a stamp.
  const pinI = new Map();
  for (const c of comps) {
    if (c.def.pinCurrents) pinI.set(c.id, c.def.pinCurrents(ctxFor(c, states.get(c.id), omega, sol)));
  }
  const edgeI = wiringFlow(net, pinI);
  for (const c of comps) {
    if (pinI.has(c.id) || !c.def.shorts) continue;
    const e = edgeI.get(c.id);
    const [p, q] = c.def.pins;
    pinI.set(c.id, { [p]: e || new Complex(0, 0), [q]: (e || new Complex(0, 0)).neg() });
  }

  const nodeOut = nodes.map((n, i) => ({
    name: n.name,
    v: sol.floating.has(i) ? null : vNode[i].re,
    vc: vNode[i],
    floating: sol.floating.has(i),
    island: sol.floating.get(i) ?? null,
    terminals: n.terminals,
  }));

  const components = {};
  for (const c of comps) {
    const ctx = ctxFor(c, states.get(c.id), omega, sol);
    const pi = pinI.get(c.id) || {};
    const pins = {};
    let pc = new Complex(0, 0);
    for (const p of c.def.pins) {
      const n = c.pins[p];
      const i = pi[p] || new Complex(0, 0);
      pins[p] = { node: nodes[n].name, v: nodeOut[n].v, i };
      pc = pc.add(vNode[n].mul(i.conj()));
    }
    const [p0, p1] = c.def.pins;
    const vc = p1 ? vNode[c.pins[p0]].sub(vNode[c.pins[p1]]) : new Complex(0, 0);
    const ic = pins[p0].i;
    const r = { id: c.id, type: c.type, pins, v: vc.re, vc, i: ic.re, ic, p: c.def.isGround ? 0 : pc.re, extra: {} };
    if (c.def.extra) r.extra = c.def.extra(ctx, r);
    for (const p of c.def.pins) pins[p].i = pins[p].i.re;   // DC view as plain numbers; phasors stay on vc/ic
    if (c.def.checks) issues.push(...c.def.checks(ctx, r));
    components[c.id] = r;
  }

  // Req blocks: voltage across the block, and the current its inner parts draw from port A.
  for (const b of net.blocks) {
    const na = net.nodeOf(`${b.id}.a`), nb = net.nodeOf(`${b.id}.b`);
    if (na < 0 || nb < 0) continue;
    const P = `${b.id}/`;
    let ic = new Complex(0, 0);
    for (const c of comps) {
      if (!c.id.startsWith(P)) continue;
      const pi = pinI.get(c.id) || {};
      for (const p of c.def.pins) if (c.pins[p] === na && pi[p]) ic = ic.add(pi[p]);
    }
    if (na === nb) ic = new Complex(0, 0);
    const vc = vNode[na].sub(vNode[nb]);
    components[b.id] = {
      id: b.id, type: 'reqblock', vc, v: vc.re, ic, i: ic.re, p: vc.mul(ic.conj()).re, extra: {},
      pins: { a: { node: nodes[na].name, v: nodeOut[na].v, i: ic.re }, b: { node: nodes[nb].name, v: nodeOut[nb].v, i: -ic.re } },
    };
  }

  const wires = {};
  for (const w of circuitWires(net, edgeI)) wires[w.id] = w;

  issues.push(...circuitChecks(net, components, states, sol));
  if (net.groundAuto && nodes.length > 1) {
    issues.push(issue('info', 'auto-ground', `No ground symbol, so GND is ${net.groundNote}. All voltages are measured from there.`));
  }
  if (sol.residual > 1e-6) {
    issues.push(issue('warning', 'ill-conditioned', 'The values in this circuit span a huge range (like milliohms next to teraohms), '
      + 'so these numbers may be slightly off.'));
  }

  const out = { ok: true, freq, ground: { node: 'GND', auto: net.groundAuto, note: net.groundNote }, nodes: nodeOut, components, wires, issues };
  if (!allFinite(out)) {
    return fail(net, [...issues.filter((i) => i.level !== 'warning'), issue('error', 'numeric',
      'The numbers in this circuit overflowed. Check for extreme values (huge voltages or tiny resistances).')], freq);
  }
  return finish(net, out);
}

/* Current through each ideal connection (wire, closed switch). Inside one node the wires form
   a small graph; each part pin injects its current there. Solving that graph with every wire
   equal gives the unique flow when the wiring is a tree, and an even split around wire loops. */
function wiringFlow(net, pinI) {
  const flows = new Map();
  const byNode = new Map();
  for (const e of net.edges) {
    const n = net.nodeOf(e.a);
    if (!byNode.has(n)) byNode.set(n, []);
    byNode.get(n).push(e);
  }
  for (const [, edges] of byNode) {
    const terms = new Map();
    const t = (x) => { if (!terms.has(x)) terms.set(x, terms.size); return terms.get(x); };
    edges.forEach((e) => { t(e.a); t(e.b); });
    const m = terms.size;
    if (m < 2) continue;
    const A = new System(m - 1);
    const at = (x) => terms.get(x) - 1;          // terminal 0 is the local reference
    for (const e of edges) {
      const a = at(e.a), b = at(e.b);
      A.add(a, a, 1); A.add(b, b, 1); A.add(a, b, -1); A.add(b, a, -1);
    }
    for (const [term, k] of terms) {
      const mm = /^(.*)\.([^.]+)$/.exec(term);
      const cur = mm && pinI.get(mm[1]);
      const i = cur && cur[mm[2]];
      if (i && k > 0) A.addRhs(k - 1, i.neg());   // current leaving the wiring into the part
    }
    const out = gaussSolve(A);
    if (!out.x) continue;
    const phi = (x) => (terms.get(x) === 0 ? new Complex(0, 0) : out.x[terms.get(x) - 1]);
    for (const e of edges) if (e.id) flows.set(e.id, phi(e.a).sub(phi(e.b)));
  }
  return flows;
}

function circuitWires(net, edgeI) {
  return (net.edges.filter((e) => e.kind === 'wire').map((e) => ({ id: e.id, i: (edgeI.get(e.id) || new Complex(0, 0)).re,
    ic: edgeI.get(e.id) || new Complex(0, 0), cut: false, node: net.nodes[net.nodeOf(e.a)].name })))
    .concat(net.cutWires.map((w) => ({ id: w.id, i: 0, ic: new Complex(0, 0), cut: true, node: null,
      ends: [net.nodes[net.nodeOf(w.a)].name, net.nodes[net.nodeOf(w.b)].name] })));
}

function circuitChecks(net, components, states, sol) {
  const out = [];
  const { comps, nodes } = net;

  // Unconnected pins: a node holding exactly one part pin and nothing else to reach.
  const pinCount = nodes.map(() => 0);
  for (const c of comps) if (!c.def.isGround && !c.def.isJunction) for (const p of c.def.pins) pinCount[c.pins[p]]++;
  const groundNode = net.ground;
  const hasGroundSymbol = (n) => nodes[n].terminals.some((t) => comps.some((c) => c.def.isGround && t.startsWith(`${c.id}.`)));
  const loose = new Set();      // parts with every pin unconnected
  for (const c of comps) {
    if (c.def.isGround || c.def.isJunction) continue;
    const open = c.def.pins.filter((p) => pinCount[c.pins[p]] === 1 && !(c.pins[p] === groundNode && hasGroundSymbol(groundNode)));
    if (!open.length) continue;
    if (open.length === c.def.pins.length) {
      loose.add(c.id);
      out.push(issue('warning', 'unconnected', `${c.id} isn't connected to anything.`, [c.id]));
    } else if (c.type === 'vsource' || c.type === 'isource') {
      out.push(issue('warning', 'unconnected', `${c.id}'s ${pinLabel(c.def, open[0])} terminal isn't connected to anything, so it can't drive any current.`, [c.id]));
    } else {
      out.push(issue('warning', 'unconnected', `One end of ${c.id} isn't connected to anything, so no current flows through it.`, [c.id]));
    }
  }

  // Floating sub-circuits.
  for (const [r, members] of sol.islands) {
    if (r === sol.groundIsland) continue;
    const inside = comps.filter((c) => !c.def.isGround && !loose.has(c.id) && c.def.paths
      && c.def.paths(c.params, states.get(c.id)).length && c.def.pins.every((p) => members.includes(c.pins[p])));
    if (!inside.length) continue;    // a dead-end pin, already reported as unconnected
    const names = members.map((i) => nodes[i].name);
    out.push(issue('warning', 'floating', names.length === 1
      ? `Node ${names[0]} is floating — nothing connects it to the rest of the circuit. Its voltage relative to ground is undefined.`
      : `Nodes ${list(names)} are floating — nothing connects them to the rest of the circuit, so their voltage relative to ground `
        + 'is undefined. Voltages between them are still correct.', inside.map((c) => c.id)));
  }

  // Supplies: shorted, or fighting another supply in parallel.
  const supplies = comps.filter((c) => c.type === 'vsource');
  for (const c of supplies) {
    const r = components[c.id];
    if (c.pins.p !== c.pins.n) continue;
    const cc = r.extra.mode === 'CC';
    out.push(issue('warning', 'shorted-source', `${c.id} is shorted: its + and − terminals are wired straight together. `
      + (cc ? `Its current limit holds it at ${formatEng(Math.abs(r.extra.supplyCurrent), 'A')} and the output sits at 0 V. `
        + "That's the limit doing its job, but nothing else in the circuit gets any voltage."
        : `Only its ${formatEng(c.params.r, 'Ω')} internal resistance limits the current, so ${formatEng(Math.abs(r.extra.supplyCurrent), 'A')} flows. `
        + 'A bench supply would hit its limit or blow a fuse; a battery gets dangerously hot.'), [c.id]));
  }
  for (let i = 0; i < supplies.length; i++) {
    for (let j = i + 1; j < supplies.length; j++) {
      const a = supplies[i], b = supplies[j];
      const ra = components[a.id], rb = components[b.id];
      if (ra.extra.mode !== 'CV' || rb.extra.mode !== 'CV' || a.pins.p === a.pins.n) continue;
      const same = a.pins.p === b.pins.p && a.pins.n === b.pins.n;
      const flipped = a.pins.p === b.pins.n && a.pins.n === b.pins.p;
      const vb = flipped ? -b.params.V : b.params.V;
      if (!(same || flipped) || Math.abs(a.params.V - vb) < 1e-9) continue;
      const [hi, lo] = a.params.V > vb ? [a, b] : [b, a];
      const ihi = components[hi.id].extra.supplyCurrent;
      out.push(issue('warning', 'parallel-sources', `${a.id} (${formatEng(a.params.V, 'V')}) and ${b.id} (${formatEng(vb, 'V')}) are in parallel `
        + `with different voltages. They fight: ${formatEng(Math.abs(ihi), 'A')} flows out of ${hi.id} into ${lo.id}, limited only by their `
        + 'internal resistance. Never connect two supplies straight across each other.', [a.id, b.id]));
    }
  }
  return out;
}

/* ------------------------------------------------------------ helpers */

function allFinite(x, depth = 0) {
  if (depth > 6 || x === null || x === undefined) return true;
  if (typeof x === 'number') return Number.isFinite(x);
  if (x instanceof Complex) return x.isFinite();
  if (typeof x === 'object') return Object.values(x).every((v) => allFinite(v, depth + 1));
  return true;
}

function fail(net, issues, freq) {
  return finish(net, { ok: false, freq, nodes: [], components: {}, wires: {}, issues });
}

/** Attach lookups that need the netlist: voltage at or between terminals. */
function finish(net, out) {
  const nodeIndex = (t) => net.nodeOf(t);
  Object.defineProperties(out, {
    nodeName: { value: (t) => { const n = nodeIndex(t); return n >= 0 && out.nodes[n] ? out.nodes[n].name : null; } },
    /** Voltage of terminal a relative to terminal b (b defaults to ground). null when undefined. */
    voltage: {
      value: (a, b) => {
        const na = nodeIndex(a), nb = b === undefined ? net.ground : nodeIndex(b);
        const A = out.nodes[na], B = out.nodes[nb];
        if (!A || !B) return null;
        if (A.island !== B.island) return null;     // different floating pieces: no defined difference
        return A.vc.sub(B.vc).re;
      },
    },
  });
  return out;
}
