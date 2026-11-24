/* Req blocks: flattening, Req, live values inside, KCL/KVL lines, grading and probes inside. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { close, assertFinite } from './helpers.mjs';
import { registry } from '../../static/circuit/js/components/registry.js';
import { createCircuit, addComponent, addWire, emptyInner, flattenBlocks } from '../../static/circuit/js/core/netlist.js';
import { solve } from '../../static/circuit/js/core/solver.js';
import { equivalentR, isSolved, gradeGuess, blockChecks, scopeAt, findGlobal, nextTreeId, globalAttachTerm }
  from '../../static/circuit/js/core/blocks.js';
import { measure, initialMeter } from '../../static/circuit/js/meter/meter-model.js';

const profile = JSON.parse(readFileSync(new URL('../../static/circuit/meters/fluke-87v.json', import.meta.url), 'utf8'));

/** A block holding resistors in parallel between A and B. */
function parallelInner(values) {
  const inner = emptyInner();
  values.forEach((R, k) => {
    const id = addComponent(inner, registry, 'resistor', { R }, { id: `R${k + 1}` });
    addWire(inner, 'A.j', `${id}.a`);
    addWire(inner, `${id}.b`, 'B.j');
  });
  return inner;
}

/** The Series-Parallel Stepper circuit: 9 V, Req1 = R1‖R2‖R4, then R3 and R5 in series. */
function stepper() {
  const c = createCircuit();
  addComponent(c, registry, 'vsource', { V: 9, r: 0, ilimit: null });
  addComponent(c, registry, 'reqblock', {}, { id: 'Req1', inner: parallelInner([120, 680, 1000]) });
  addComponent(c, registry, 'resistor', { R: 680 }, { id: 'R3' });
  addComponent(c, registry, 'resistor', { R: 1000 }, { id: 'R5' });
  addWire(c, 'V1.p', 'Req1.a');
  addWire(c, 'Req1.b', 'R3.a');
  addWire(c, 'R3.b', 'R5.a');
  addWire(c, 'R5.b', 'V1.n');
  return c;
}

const Rp = 1 / (1 / 120 + 1 / 680 + 1 / 1000);
const I = 9 / (Rp + 680 + 1000);

test('flatten: inner parts get path ids and the ports are tied to the block pins', () => {
  const f = flattenBlocks(stepper());
  const ids = f.components.map((c) => c.id);
  assert.ok(ids.includes('Req1/R1') && ids.includes('Req1/A') && !ids.includes('Req1'));
  assert.ok(f.wires.some((w) => w.a === 'Req1.a' && w.b === 'Req1/A.j'));
  assert.deepEqual(f.blocks, [{ id: 'Req1' }]);
});

test('equivalentR: parallel, series inside, open and shorted', () => {
  close(equivalentR(parallelInner([120, 680, 1000])).R, Rp, 1e-9);
  const s = emptyInner();
  addComponent(s, registry, 'resistor', { R: 220 }, { id: 'R1' });
  addComponent(s, registry, 'resistor', { R: 330 }, { id: 'R2' });
  addWire(s, 'A.j', 'R1.a'); addWire(s, 'R1.b', 'R2.a'); addWire(s, 'R2.b', 'B.j');
  close(equivalentR(s).R, 550, 1e-9);
  assert.equal(equivalentR(emptyInner()).R, Infinity);
  const short = emptyInner();
  addWire(short, 'A.j', 'B.j');
  assert.equal(equivalentR(short).R, 0);
});

test('solve: series-parallel values match the hand calculation', () => {
  const r = solve(stepper());
  assert.ok(r.ok, JSON.stringify(r.issues));
  assertFinite(r);
  close(r.components.Req1.i, I, 1e-9);
  close(r.components.Req1.v, I * Rp, 1e-9);
  close(r.components['Req1/R1'].i, (I * Rp) / 120, 1e-9);
  close(r.components.R3.v, I * 680, 1e-9);
});

test('nested blocks flatten and solve', () => {
  const c = stepper();
  const outer = c.components.find((x) => x.id === 'Req1');
  addComponent(outer.inner, registry, 'reqblock', {}, { id: 'Req2', inner: parallelInner([1000, 1000]) });
  addWire(outer.inner, 'A.j', 'Req2.a');
  addWire(outer.inner, 'Req2.b', 'B.j');
  const want = 1 / (1 / Rp + 1 / 500);
  close(equivalentR(outer.inner).R, want, 1e-9);
  const r = solve(c);
  assert.ok(r.ok);
  close(r.components['Req1/Req2'].v, r.components.Req1.v, 1e-9);
  close(r.components['Req1/Req2/R1'].i, r.components.Req1.v / 1000, 1e-9);
  assert.equal(scopeAt(c, ['Req1', 'Req2']).components.length, 4);
  assert.equal(findGlobal(c, 'Req1/Req2/R2').item.params.R, 1000);
  assert.equal(nextTreeId(c, 'R'), 'R4');   // R1–R3 inside the blocks and R3, R5 outside are all taken
});

test('KCL and KVL lines balance', () => {
  const c = stepper();
  const k = blockChecks(c, ['Req1'], solve(c));
  for (const line of k.kcl) close(line.total, k.block.i, 1e-9);
  assert.equal(k.kcl[0].terms.length, 3);
  assert.equal(k.kvl.length, 3);
  for (const line of k.kvl) close(line.total, k.vab, 1e-9);
});

test('grading: right within 1%, wrong gives a word hint, solved re-locks when the inside changes', () => {
  const c = stepper();
  const b = c.components.find((x) => x.id === 'Req1');
  assert.ok(gradeGuess(b.inner, 92.6).ok);
  const big = gradeGuess(b.inner, 1800);
  assert.ok(!big.ok && /Too big/.test(big.hint) && !/[=+]/.test(big.hint));
  assert.ok(/Too small/.test(gradeGuess(b.inner, 10).hint));
  assert.ok(gradeGuess(b.inner, 94).close);
  assert.equal(isSolved(b), false);
  b.check = { R: equivalentR(b.inner).R, how: 'checked' };
  assert.equal(isSolved(b), true);
  b.inner.components.find((x) => x.id === 'R2').params.R = 470;
  assert.equal(isSolved(b), false);
});

test('meter probes reach inside a block', () => {
  const c = stepper();
  const meter = { ...initialMeter(), probes: { red: globalAttachTerm(c, { kind: 'pin', term: 'Req1/R1.a' }),
    black: globalAttachTerm(c, { kind: 'pin', term: 'Req1/R1.b' }) } };
  const m = measure(c, profile, meter);
  close(m.display.value, I * Rp, 1e-4);
  const wid = c.components.find((x) => x.id === 'Req1').inner.wires[0].id;
  assert.equal(globalAttachTerm(c, { kind: 'wire', id: `Req1/${wid}`, t: 0.2 }), `Req1/${wid}.a`);
});
