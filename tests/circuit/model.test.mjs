/* Units, complex math, netlist building, save/load and the component registry. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Complex } from '../../static/circuit/js/core/complex.js';
import { parseEng, formatEng } from '../../static/circuit/js/core/units.js';
import { createCircuit, addComponent, addWire, buildNetlist, serialize, deserialize, UnionFind } from '../../static/circuit/js/core/netlist.js';
import { createRegistry, registry } from '../../static/circuit/js/components/registry.js';
import { stampAdmittance } from '../../static/circuit/js/core/mna.js';
import { solve } from '../../static/circuit/js/core/solver.js';
import { close } from './helpers.mjs';

test('parseEng reads what students type', () => {
  const cases = {
    '4.7k': 4700, '4k7': 4700, '220': 220, '1M': 1e6, '1meg': 1e6, '100m': 0.1, '2R2': 2.2,
    '10u': 1e-5, '10µ': 1e-5, '4.7 kΩ': 4700, '100mA': 0.1, '12V': 12, '1e3': 1000, '.5': 0.5, '-3.3': -3.3,
    '2.2uF': 2.2e-6, '1,000': 1000, '470 ohms': 470,
  };
  for (const [s, v] of Object.entries(cases)) close(parseEng(s), v, 1e-12, s);
  for (const bad of ['', 'abc', '4.7x', '1..2', 'k', null, undefined, NaN]) assert.equal(parseEng(bad), null, String(bad));
});

test('formatEng uses SI prefixes and 3 significant figures', () => {
  assert.equal(formatEng(0.004, 'A'), '4.00 mA');
  assert.equal(formatEng(4700, 'Ω'), '4.70 kΩ');
  assert.equal(formatEng(1e6, 'Ω'), '1.00 MΩ');
  assert.equal(formatEng(-0.0123, 'V'), '-12.3 mV');
  assert.equal(formatEng(999.96, 'V'), '1.00 kV');
  assert.equal(formatEng(0, 'V'), '0 V');
  assert.equal(formatEng(NaN, 'V'), '—');
  assert.equal(formatEng(Infinity, 'V'), '—');
  assert.equal(formatEng(123.456, 'W'), '123 W');
});

test('Complex arithmetic', () => {
  const a = new Complex(3, 4), b = new Complex(1, -2);
  assert.equal(a.abs(), 5);
  assert.deepEqual({ ...a.mul(b) }, { re: 11, im: -2 });
  const q = a.div(b);
  close(q.re, -1); close(q.im, 2);
  assert.deepEqual({ ...a.add(2) }, { re: 5, im: 4 });
});

test('union-find joins and finds', () => {
  const uf = new UnionFind();
  uf.union('a', 'b'); uf.union('c', 'd');
  assert.equal(uf.find('a'), uf.find('b'));
  assert.notEqual(uf.find('a'), uf.find('c'));
  uf.union('b', 'd');
  assert.equal(uf.find('a'), uf.find('c'));
});

test('netlist: wires collapse pins into named nodes; auto-numbered ids', () => {
  const c = createCircuit();
  const v = addComponent(c, registry, 'vsource');
  const r1 = addComponent(c, registry, 'resistor');
  const r2 = addComponent(c, registry, 'resistor');
  const g = addComponent(c, registry, 'ground');
  assert.deepEqual([v, r1, r2, g], ['V1', 'R1', 'R2', 'GND1']);
  addWire(c, 'V1.p', 'R1.a');
  addWire(c, 'R1.b', 'R2.a');
  addWire(c, 'R2.b', 'V1.n');
  addWire(c, 'GND1.g', 'W3.b');      // a wire may attach to another wire's end
  const net = buildNetlist(c, registry);
  const name = (t) => net.nodes[net.nodeOf(t)].name;
  assert.equal(name('V1.n'), 'GND');
  assert.equal(name('R2.b'), 'GND');
  assert.equal(name('V1.p'), name('R1.a'));
  assert.notEqual(name('R1.a'), name('R1.b'));
  assert.equal(net.groundAuto, false);
  assert.equal(net.nodes.length, 3);
});

test('netlist: bad wire pin is an error', () => {
  const c = createCircuit();
  addComponent(c, registry, 'resistor');
  addWire(c, 'R1.x', 'R1.a');
  const net = buildNetlist(c, registry);
  assert.ok(net.issues.some((i) => i.code === 'bad-pin'));
});

test('save/load round trip gives the same solution', () => {
  const c = createCircuit();
  addComponent(c, registry, 'vsource', { V: 5, r: 0, ilimit: null });
  addComponent(c, registry, 'resistor', { R: 250 });
  addWire(c, 'V1.p', 'R1.a');
  addWire(c, 'R1.b', 'V1.n');
  const back = deserialize(serialize(c));
  assert.ok(back.circuit);
  close(solve(back.circuit).components.R1.i, 0.02);
  assert.ok(deserialize('{nope').error);
  assert.ok(deserialize('{"components": 5}').error);
  assert.ok(deserialize({ version: 99, components: [] }).error);
});

test('registry: a new part is one definition, no solver edits', () => {
  // A conductance element defined only here, in the test.
  const conductance = {
    type: 'conductance', prefix: 'G', pins: ['a', 'b'], defaults: { G: 0.01 },
    paths: () => [['a', 'b']],
    stamp: (A, rhs, ctx) => stampAdmittance(A, ctx.node('a'), ctx.node('b'), ctx.params.G),
    pinCurrents: (ctx) => { const i = ctx.v('a').sub(ctx.v('b')).scale(ctx.params.G); return { a: i, b: i.neg() }; },
  };
  const reg = createRegistry(registry.types().map((t) => registry.get(t))).register(conductance);
  const c = createCircuit();
  addComponent(c, reg, 'vsource', { V: 2, r: 0, ilimit: null });
  addComponent(c, reg, 'conductance', { G: 0.5 });
  addWire(c, 'V1.p', 'G1.a');
  addWire(c, 'G1.b', 'V1.n');
  close(solve(c, { registry: reg }).components.G1.i, 1);
  assert.throws(() => reg.register({ type: 'broken' }));
});

test('solver accepts a frequency (AC hook) and DC parts are unchanged by it', () => {
  const c = createCircuit();
  addComponent(c, registry, 'vsource', { V: 10, r: 0, ilimit: null });
  addComponent(c, registry, 'resistor', { R: 1000 });
  addWire(c, 'V1.p', 'R1.a');
  addWire(c, 'R1.b', 'V1.n');
  const res = solve(c, { freq: 60 });
  assert.equal(res.freq, 60);
  close(res.components.R1.i, 0.01);
});
