/* Solver checks against hand-calculated values. Run from the repo root: node --test */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { builder, close, assertFinite, codes } from './helpers.mjs';

test('voltage divider: 12 V across 1k + 2k', () => {
  const b = builder();
  const v1 = b.V('top', 'gnd', 12);
  const r1 = b.R('top', 'mid', 1000);
  const r2 = b.R('mid', 'gnd', 2000);
  const res = b.solve();
  assert.ok(res.ok);
  // I = 12 / 3000 = 4 mA; Vmid = 4 mA × 2k = 8 V
  close(res.voltage('mid'), 8);
  close(res.voltage('top'), 12);
  close(res.components[r1].i, 0.004);
  close(res.components[r2].v, 8);
  close(res.components[v1].extra.supplyCurrent, 0.004);
  // P(R1) = I²R = 16 mW, P(R2) = 32 mW, supply delivers 48 mW
  close(res.components[r1].p, 0.016);
  close(res.components[r2].p, 0.032);
  close(res.components[v1].extra.delivered, 0.048);
  assertFinite(res);
});

test('series-parallel: 24 V, 100 Ω then 300 Ω ∥ (200 Ω + 400 Ω)', () => {
  const b = builder();
  b.V('s', 'gnd', 24);
  const r1 = b.R('s', 'A', 100);
  const r2 = b.R('A', 'gnd', 300);
  const r3 = b.R('A', 'B', 200);
  b.R('B', 'gnd', 400);
  const res = b.solve();
  // 300 ∥ 600 = 200; total 300 Ω; I = 80 mA; VA = 24 − 8 = 16 V
  close(res.components[r1].i, 0.08);
  close(res.voltage('A'), 16);
  close(res.components[r2].i, 16 / 300);
  close(res.components[r3].i, 16 / 600);
  close(res.voltage('B'), 16 * 400 / 600);
});

test('unbalanced Wheatstone bridge (no series/parallel shortcut)', () => {
  const b = builder();
  const v = b.V('T', 'gnd', 10);
  b.R('T', 'A', 100);
  b.R('A', 'gnd', 200);
  b.R('T', 'B', 300);
  b.R('B', 'gnd', 400);
  const r5 = b.R('A', 'B', 500);
  const res = b.solve();
  // Nodal equations by hand: 17·VA − 2·VB = 100, −12·VA + 47·VB = 200
  // → VA = 204/31, VB = 184/31, I(R5) = (20/31)/500 = 1/775 A
  close(res.voltage('A'), 204 / 31);
  close(res.voltage('B'), 184 / 31);
  close(res.components[r5].i, 1 / 775);
  // supply current = (10 − VA)/100 + (10 − VB)/300
  close(res.components[v].extra.supplyCurrent, (10 - 204 / 31) / 100 + (10 - 184 / 31) / 300);
});

test('two sources: result equals the superposition of each alone', () => {
  const make = (v1, v2) => {
    const b = builder();
    b.V('X', 'gnd', v1);
    b.R('X', 'M', 10);
    b.R('M', 'gnd', 20);
    b.R('M', 'Y', 5);
    b.V('Y', 'gnd', v2);
    return b.solve().voltage('M');
  };
  // By hand: (VM − 10)/10 + VM/20 + (VM − 5)/5 = 0 → 7·VM = 40
  const both = make(10, 5);
  close(both, 40 / 7);
  // V1 alone: 10 × (20∥5)/(10 + 20∥5) = 20/7; V2 alone: 5 × (10∥20)/(5 + 10∥20) = 20/7
  close(make(10, 0), 20 / 7);
  close(make(0, 5), 20 / 7);
  close(make(10, 0) + make(0, 5), both);
});

test('floating node: friendly message, no NaN, rest of circuit still solves', () => {
  const b = builder();
  b.V('s', 'gnd', 10);
  b.R('s', 'gnd', 1000);
  b.R('F1', 'F2', 470);           // a little loop that touches nothing else
  b.R('F2', 'F1', 220);
  const res = b.solve();
  assert.ok(res.ok);
  assert.ok(!codes(res).includes('unconnected'), 'the loop is connected, just not to ground');
  const f = res.issues.find((i) => i.code === 'floating');
  assert.ok(f, `expected a floating warning, got ${codes(res)}`);
  assert.match(f.message, /floating — nothing connects/);
  assert.equal(res.voltage('F1'), null, 'voltage to ground is undefined');
  close(res.voltage('F1', 'F2'), 0);
  close(res.voltage('s'), 10);
  assertFinite(res);

  // A single loose resistor gets one clear message, not two.
  const lone = builder();
  lone.V('s', 'gnd', 10);
  lone.R('s', 'gnd', 1000);
  lone.R('L1', 'L2', 470);
  assert.deepEqual(codes(lone.solve()).filter((c) => c !== 'auto-ground'), ['unconnected']);
});

test('current source with no return path is an error, not NaN', () => {
  const b = builder();
  b.V('s', 'gnd', 5);
  b.R('s', 'gnd', 100);
  b.I('X', 'gnd', 0.01);           // pushes 10 mA into X; X goes nowhere
  const res = b.solve();
  assert.equal(res.ok, false);
  assert.deepEqual(codes(res).filter((c) => c === 'no-return-path'), ['no-return-path']);
  assert.match(res.issues.find((i) => i.code === 'no-return-path').message, /node N\d+/);
  assertFinite(res);
});

test('shorted supply: internal resistance sets the current, no NaN', () => {
  const b = builder();
  const v = b.V('s', 'gnd', 12, { r: 0.01 });
  b.wire('s', 'gnd');
  const res = b.solve();
  assert.ok(res.ok);
  close(res.components[v].extra.supplyCurrent, 1200);    // 12 V / 0.01 Ω
  close(res.components[v].extra.terminalVoltage, 0);
  assert.ok(codes(res).includes('shorted-source'));
  assertFinite(res);
});

test('shorted ideal supply (r = 0) is a clear error', () => {
  const b = builder();
  b.V('s', 'gnd', 12, { r: 0 });
  b.wire('s', 'gnd');
  const res = b.solve();
  assert.equal(res.ok, false);
  assert.ok(codes(res).includes('ideal-short'));
});

test('CC-limited bench supply into a low-value load', () => {
  const b = builder();
  const v = b.V('s', 'gnd', 12, { r: 0.01, ilimit: 0.1 });
  const r = b.R('s', 'gnd', 10);
  const res = b.solve();
  // CV would push 12 / 10.01 ≈ 1.2 A, over the 100 mA limit → CC at 100 mA, output 100 mA × 10 Ω = 1 V
  const s = res.components[v].extra;
  assert.equal(s.mode, 'CC');
  close(s.supplyCurrent, 0.1);
  close(s.terminalVoltage, 1);
  close(res.components[r].i, 0.1);
  assert.ok(codes(res).includes('cc-mode'));
  assert.match(res.issues.find((i) => i.code === 'cc-mode').message, /sagged from 12\.0 V to 1\.00 V/);
});

test('CC supply stays in CV when the load is light', () => {
  const b = builder();
  const v = b.V('s', 'gnd', 12, { r: 0, ilimit: 0.1 });
  b.R('s', 'gnd', 1000);
  const res = b.solve();
  assert.equal(res.components[v].extra.mode, 'CV');
  close(res.components[v].extra.supplyCurrent, 0.012);
});

test('CC supply into a dead short holds the limit at 0 V', () => {
  const b = builder();
  const v = b.V('s', 'gnd', 12, { r: 0.01, ilimit: 0.5 });
  b.wire('s', 'gnd');
  const res = b.solve();
  assert.equal(res.components[v].extra.mode, 'CC');
  close(res.components[v].extra.supplyCurrent, 0.5);
  close(res.components[v].extra.terminalVoltage, 0);
  assertFinite(res);
});

test('internal resistance: default bench supply sags slightly under load', () => {
  const b = builder();
  const v = b.V('s', 'gnd', 12, { r: 0.01, ilimit: null });
  b.R('s', 'gnd', 100);
  const res = b.solve();
  close(res.components[v].extra.supplyCurrent, 12 / 100.01);
  close(res.voltage('s'), 12 * 100 / 100.01);
});

test('current source into a resistor: V = IR, direction out of +', () => {
  const b = builder();
  const i = b.I('X', 'gnd', 0.002);
  const r = b.R('X', 'gnd', 1500);
  const res = b.solve();
  close(res.voltage('X'), 3);
  close(res.components[r].i, 0.002);
  close(res.components[i].p, -0.006, 1e-9, 'source delivers 6 mW');
});

test('switch: closed conducts and reports its current, open breaks the circuit', () => {
  const on = builder();
  on.V('s', 'gnd', 9);
  const sw = on.S('s', 'x', true);
  on.R('x', 'gnd', 900);
  const r1 = on.solve();
  close(r1.components[sw].i, 0.01);
  close(r1.voltage('x'), 9);

  const off = builder();
  off.V('s', 'gnd', 9);
  off.S('s', 'x', false);
  const r = off.R('x', 'gnd', 900);
  const r2 = off.solve();
  assert.ok(r2.ok);
  close(r2.components[r].i, 0);
  close(r2.voltage('x'), 0);
});

test('wire currents: series wire carries the loop current, cut wire opens it', () => {
  const b = builder();
  b.V('s', 'gnd', 10);
  const w = b.wire('s', 'k');
  b.R('k', 'gnd', 1000);
  const res = b.solve();
  // builder wires go V1.p→s, then s→k (this one), then R1.a→k
  close(Math.abs(res.wires[w].i), 0.01);

  b.circuit.wires.find((x) => x.id === w).cut = true;
  const cut = b.solve();
  assert.ok(cut.ok);
  assert.equal(cut.wires[w].cut, true);
  close(cut.voltage('k'), 0);
  close(cut.voltage('s'), 10);
  assert.notEqual(cut.wires[w].ends[0], cut.wires[w].ends[1]);
});

test('parallel supplies with different voltages are flagged', () => {
  const b = builder();
  b.V('s', 'gnd', 12, { r: 0.01 });
  b.V('s', 'gnd', 5, { r: 0.01 });
  const res = b.solve();
  assert.ok(res.ok);
  const p = res.issues.find((i) => i.code === 'parallel-sources');
  assert.ok(p);
  assert.match(p.message, /350 A flows out of V1 into V2/);      // 7 V / 0.02 Ω
});

test('ideal supplies in parallel: error instead of a singular matrix', () => {
  const b = builder();
  b.V('s', 'gnd', 12);
  b.V('s', 'gnd', 5);
  const res = b.solve();
  assert.equal(res.ok, false);
  assert.ok(codes(res).includes('ideal-loop'));
});

test('over-power resistor warning', () => {
  const b = builder();
  b.V('s', 'gnd', 12);
  b.R('s', 'gnd', 100, { Pmax: 0.25 });     // 1.44 W
  const res = b.solve();
  const w = res.issues.find((i) => i.code === 'overpower');
  assert.match(w.message, /R1 is dissipating 1\.44 W, rated 250 mW — it'll cook/);
});

test('no ground symbol: auto-ground at the supply − terminal', () => {
  const b = builder();
  b.V('s', 'n', 6);
  b.R('s', 'n', 600);
  const res = b.solve();
  assert.ok(res.ground.auto);
  close(res.voltage('s'), 6);
  close(res.voltage('n'), 0);
  assert.ok(codes(res).includes('auto-ground'));
});

test('edge cases never crash and never leak NaN', () => {
  const cases = {
    empty: builder(),
    loneResistor: (() => { const b = builder(); b.R('a', 'b', 100); return b; })(),
    groundOnly: (() => { const b = builder(); b.R('gnd', 'gnd', 100); return b; })(),
    wireLoop: (() => { const b = builder(); b.V('s', 'gnd', 5); b.wire('s', 'q'); b.wire('q', 's'); b.R('q', 'gnd', 50); return b; })(),
    hugeAndTiny: (() => { const b = builder(); b.V('s', 'gnd', 1000); b.R('s', 'm', 1e-6); b.R('m', 'gnd', 1e12); return b; })(),
    zeroOhm: (() => { const b = builder(); b.V('s', 'gnd', 5); b.R('s', 'gnd', 0); return b; })(),
    negativeR: (() => { const b = builder(); b.V('s', 'gnd', 5); b.R('s', 'gnd', -5); return b; })(),
    nanV: (() => { const b = builder(); b.V('s', 'gnd', NaN); b.R('s', 'gnd', 5); return b; })(),
  };
  for (const [name, b] of Object.entries(cases)) {
    const res = b.solve();
    assertFinite(res, name);
    assert.ok(Array.isArray(res.issues), name);
    if (!res.ok) assert.ok(res.issues.some((i) => i.level === 'error' && i.message.length > 10), `${name} explains its error`);
  }
  assert.ok(cases.empty.solve().empty);
  assert.equal(cases.zeroOhm.solve().ok, false);
  assert.match(cases.zeroOhm.solve().issues[0].message, /use a wire/);
});

test('loop of wires splits current evenly and keeps KCL', () => {
  const b = builder();
  b.V('s', 'gnd', 10);
  const w1 = b.wire('s', 'k');
  const w2 = b.wire('s', 'k');
  b.R('k', 'gnd', 100);
  const res = b.solve();
  close(Math.abs(res.wires[w1].i) + Math.abs(res.wires[w2].i), 0.1);
  close(res.wires[w1].i, res.wires[w2].i);
});
