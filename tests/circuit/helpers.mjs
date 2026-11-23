import assert from 'node:assert/strict';
import { createCircuit, addComponent, addWire } from '../../static/circuit/js/core/netlist.js';
import { registry } from '../../static/circuit/js/components/registry.js';
import { solve } from '../../static/circuit/js/core/solver.js';

export { solve, registry };

/** Tiny builder: b.R('A', 'B', 1000) wires a resistor between named junctions A and B.
    Junction names are free terminal strings; 'gnd' gets a ground symbol. */
export function builder() {
  const c = createCircuit();
  const joined = new Set();
  const hook = (pin, at) => {
    addWire(c, pin, at);
    if (at === 'gnd' && !joined.has('gnd')) {
      joined.add('gnd');
      const g = addComponent(c, registry, 'ground');
      addWire(c, `${g}.g`, 'gnd');
    }
  };
  const two = (type, pins) => (a, b, params) => {
    const id = addComponent(c, registry, type, params);
    hook(`${id}.${pins[0]}`, a);
    hook(`${id}.${pins[1]}`, b);
    return id;
  };
  return {
    circuit: c,
    R: (a, b, R, extra = {}) => two('resistor', ['a', 'b'])(a, b, { R, ...extra }),
    V: (p, n, V, extra = {}) => two('vsource', ['p', 'n'])(p, n, { V, r: 0, ilimit: null, ...extra }),
    I: (p, n, I) => two('isource', ['p', 'n'])(p, n, { I }),
    S: (a, b, closed = true) => two('switch', ['a', 'b'])(a, b, { closed }),
    wire: (a, b) => addWire(c, a, b),
    solve: (opts) => solve(c, opts),
  };
}

export function close(actual, expected, tol = 1e-9, msg = '') {
  const ok = Math.abs(actual - expected) <= tol * Math.max(1, Math.abs(expected));
  assert.ok(ok, `${msg} expected ${expected}, got ${actual}`);
}

/** Every number anywhere in the result is finite. */
export function assertFinite(x, path = 'result') {
  if (typeof x === 'number') assert.ok(Number.isFinite(x), `${path} is ${x}`);
  else if (x && typeof x === 'object') for (const [k, v] of Object.entries(x)) assertFinite(v, `${path}.${k}`);
}

export const codes = (res) => res.issues.map((i) => i.code);
