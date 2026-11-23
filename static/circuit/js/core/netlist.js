/* The circuit model: the single source of truth both views edit.

   circuit = {
     version: 1,
     components: [{ id: 'R1', type: 'resistor', params: { R: 1000, Pmax: 0.25 }, layout: {…} }],
     wires:      [{ id: 'W1', a: 'V1.p', b: 'R1.a', cut: false, layout: {…} }],
   }

   Terminals are strings. A component pin is "R1.a"; a wire's own ends are "W1.a" / "W1.b".
   A wire endpoint may name a pin, another wire's end, or any other string (a junction point or,
   later, a breadboard hole). Wires and closed switches are ideal: the terminals they join collapse
   into one node (union-find). Cutting a wire leaves its two ends open. */

export const VERSION = 1;

export class UnionFind {
  constructor() { this.parent = new Map(); }
  add(x) { if (!this.parent.has(x)) this.parent.set(x, x); return x; }
  find(x) {
    this.add(x);
    let r = x;
    while (this.parent.get(r) !== r) r = this.parent.get(r);
    while (this.parent.get(x) !== r) { const nx = this.parent.get(x); this.parent.set(x, r); x = nx; }
    return r;
  }
  union(a, b) {
    const ra = this.find(a), rb = this.find(b);
    if (ra !== rb) this.parent.set(rb, ra);
    return ra !== rb;
  }
}

/* --------------------------------------------------------------- editing */

export function createCircuit() {
  return { version: VERSION, components: [], wires: [] };
}

export function nextId(circuit, prefix) {
  const used = new Set([...circuit.components, ...circuit.wires].map((x) => x.id));
  let n = 1;
  while (used.has(`${prefix}${n}`)) n++;
  return `${prefix}${n}`;
}

/** Add a part with auto-numbered id (R1, R2, V1…). Returns the id. */
export function addComponent(circuit, registry, type, params = {}, extra = {}) {
  const def = registry.get(type);
  if (!def) throw new Error(`unknown component type "${type}"`);
  const id = extra.id || nextId(circuit, def.prefix);
  circuit.components.push({ id, type, params: { ...def.defaults, ...params }, ...extra, id });
  return id;
}

/** Add a wire between two terminals. Returns the id. */
export function addWire(circuit, a, b, extra = {}) {
  const id = extra.id || nextId(circuit, 'W');
  circuit.wires.push({ id, a, b, cut: false, ...extra, id });
  return id;
}

/* ------------------------------------------------------------ save / load */

export function serialize(circuit) {
  return JSON.stringify(circuit);
}

/** Parse saved JSON. Returns { circuit } or { error } with a plain-English reason. */
export function deserialize(text) {
  let data;
  try { data = typeof text === 'string' ? JSON.parse(text) : text; } catch {
    return { error: "That isn't valid circuit JSON." };
  }
  if (!data || typeof data !== 'object') return { error: "That isn't a circuit." };
  if (data.version !== undefined && data.version > VERSION) {
    return { error: 'This circuit was saved by a newer version of the tool.' };
  }
  const components = Array.isArray(data.components) ? data.components : null;
  const wires = Array.isArray(data.wires) ? data.wires : [];
  if (!components) return { error: 'The circuit has no component list.' };
  for (const c of components) {
    if (!c || typeof c.id !== 'string' || typeof c.type !== 'string') return { error: 'A component is missing its id or type.' };
    if (c.params !== undefined && (typeof c.params !== 'object' || c.params === null)) return { error: `${c.id} has bad parameters.` };
  }
  for (const w of wires) {
    if (!w || typeof w.id !== 'string' || typeof w.a !== 'string' || typeof w.b !== 'string') {
      return { error: 'A wire is missing its id or ends.' };
    }
  }
  return { circuit: { ...data, version: VERSION, components, wires } };
}

/* ------------------------------------------------------- node building */

const issue = (level, code, message, ids = []) => ({ level, code, message, ids });

/**
 * Collapse terminals into nodes.
 * Returns { comps, nodes, ground, groundAuto, edges, nodeOf(term), canon(term), issues }.
 *   comps: [{ id, type, def, params, pins: { pin: nodeIndex } }]
 *   nodes: [{ index, name, terminals: [...] }]; ground is an index into nodes (or −1 if empty)
 *   edges: ideal connections for the wiring-flow pass [{ id, kind: 'wire'|'switch'|'gbus', a, b }]
 *   cutWires: [{ id, a, b }], the terminals on each side of a cut
 */
export function buildNetlist(circuit, registry) {
  const issues = [];
  const uf = new UnionFind();
  const order = [];                       // terminals in first-seen order, for stable node names
  const see = (t) => { if (!uf.parent.has(t)) order.push(t); uf.add(t); return t; };

  const comps = [];
  const ids = new Set();
  for (const c of circuit.components || []) {
    if (ids.has(c.id)) { issues.push(issue('error', 'duplicate-id', `Two parts are both named ${c.id}.`, [c.id])); continue; }
    ids.add(c.id);
    const def = registry.get(c.type);
    if (!def) { issues.push(issue('error', 'unknown-type', `${c.id} is a "${c.type}", which this tool doesn't know.`, [c.id])); continue; }
    const params = { ...def.defaults, ...(c.params || {}) };
    for (const msg of def.validate ? def.validate(params, c.id) : []) issues.push(issue('error', 'bad-value', msg, [c.id]));
    for (const p of def.pins) see(`${c.id}.${p}`);
    comps.push({ id: c.id, type: c.type, def, params, hidden: !!c.hidden });   // hidden: the meter's own parts
  }

  // A wire's own ends ("W1.a") are aliases for whatever they're attached to.
  const wires = (circuit.wires || []).filter((w) => {
    if (ids.has(w.id)) { issues.push(issue('error', 'duplicate-id', `Two items are both named ${w.id}.`, [w.id])); return false; }
    ids.add(w.id);
    return true;
  });
  const wireById = new Map(wires.map((w) => [w.id, w]));
  const compById = new Map(comps.map((c) => [c.id, c]));
  const canon = (t, guard = new Set()) => {
    const m = /^(.*)\.(a|b)$/.exec(t);
    const w = m && wireById.get(m[1]);
    if (!w || guard.has(t)) return t;
    guard.add(t);
    return canon(w[m[2]], guard);
  };

  const edges = [];
  const cutWires = [];
  for (const w of wires) {
    for (const end of [w.a, w.b]) {
      const m = /^(.*)\.([^.]+)$/.exec(end);
      const c = m && compById.get(m[1]);
      if (c && !c.def.pins.includes(m[2])) {
        issues.push(issue('error', 'bad-pin', `Wire ${w.id} is attached to ${end}, but ${c.id} has no pin "${m[2]}".`, [w.id]));
      }
    }
    const a = see(canon(w.a)), b = see(canon(w.b));
    if (!w.cut) {
      uf.union(a, b);
      if (a !== b) edges.push({ id: w.id, kind: 'wire', a, b });
    } else cutWires.push({ id: w.id, a, b });
  }

  let lastGround = null;
  for (const c of comps) {
    for (const [p, q] of c.def.shorts ? c.def.shorts(c.params) : []) {
      const a = `${c.id}.${p}`, b = `${c.id}.${q}`;
      uf.union(a, b);
      edges.push({ id: c.id, kind: 'switch', a, b });
    }
    if (c.def.isGround) {
      for (const p of c.def.pins) {
        const t = `${c.id}.${p}`;
        if (lastGround) { uf.union(lastGround, t); edges.push({ id: null, kind: 'gbus', a: lastGround, b: t }); }
        lastGround = t;
      }
    }
  }

  // Nodes, numbered by first appearance.
  const rootIndex = new Map();
  const nodes = [];
  for (const t of order) {
    const r = uf.find(t);
    if (!rootIndex.has(r)) { rootIndex.set(r, nodes.length); nodes.push({ index: nodes.length, name: '', terminals: [] }); }
    nodes[rootIndex.get(r)].terminals.push(t);
  }
  const nodeOf = (t) => {
    const c = canon(t);
    return uf.parent.has(c) ? rootIndex.get(uf.find(c)) : -1;
  };
  for (const c of comps) c.pins = Object.fromEntries(c.def.pins.map((p) => [p, nodeOf(`${c.id}.${p}`)]));

  // Ground: the node with the ground symbol, else auto-assigned.
  let ground = -1, groundAuto = false, groundNote = '';
  if (lastGround) ground = nodeOf(lastGround);
  else if (comps.length) {
    groundAuto = true;
    const src = comps.find((c) => c.def.groundPin && !c.def.isGround && !c.hidden)
      || comps.find((c) => c.def.groundPin && !c.def.isGround);
    if (src) {
      ground = src.pins[src.def.groundPin];
      groundNote = `${src.id}'s ${src.def.groundPin === 'n' ? '−' : src.def.groundPin} terminal`;
    } else {
      const c = comps.find((x) => !x.hidden) || comps[0];
      ground = c.pins[c.def.pins[c.def.pins.length - 1]];
      groundNote = `${c.id}'s pin ${c.def.pins[c.def.pins.length - 1]}`;
    }
  }
  let k = 1;
  for (const n of nodes) n.name = n.index === ground ? 'GND' : `N${k++}`;

  return { comps, nodes, ground, groundAuto, groundNote, edges, cutWires, nodeOf, canon, issues };
}
