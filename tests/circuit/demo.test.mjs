/* The teacher demo's on-screen claims must match what the engine actually does. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registry } from '../../static/circuit/js/components/registry.js';
import { buildDemo, DEMO_STEPS } from '../../static/circuit/js/demo.js';
import { measure, initialMeter, userIssues } from '../../static/circuit/js/meter/meter-model.js';
import { attachTerm } from '../../static/circuit/js/views/schematic.js';

const profile = JSON.parse(readFileSync(new URL('../../static/circuit/meters/fluke-87v.json', import.meta.url), 'utf8'));

function run(i) {
  const c = buildDemo(registry);
  const s = DEMO_STEPS[i];
  for (const [id, closed] of Object.entries(s.switches)) c.components.find((x) => x.id === id).params.closed = closed;
  for (const [id, cut] of Object.entries(s.cuts)) c.wires.find((x) => x.id === id).cut = cut;
  const meter = { ...initialMeter(), dial: s.dial, red: s.red,
    probes: { red: attachTerm(c, s.probes[0]), black: attachTerm(c, s.probes[1]) } };
  const m = measure(c, profile, meter);
  return { m, codes: m.warnings.map((w) => w.code), text: `${m.display.text} ${m.display.unit}`.trim(), issues: userIssues(m.result).map((x) => x.code) };
}

const expected = [
  { text: '6.66 V', codes: [] },
  { text: '-6.66 V', codes: [] },
  { text: '5.34 mA', codes: [], tier: 'safe' },
  { tier: 'safe', codes: ['current-across'], issues: ['cc-mode'] },
  { text: 'LEAd', tier: 'blows', codes: ['lead-in-current-jack', 'current-across'] },
  { tier: 'blows', codes: [], issues: ['unconnected'] },        // fuse open: the cut wire is open again
  { text: '0.781 A', tier: 'safe', codes: [], issues: ['overpower'] },
  { text: '7.83 V', codes: [], issues: ['overpower'] },
  { codes: ['ohms-live', 'ohms-in-circuit'] },
  { text: '1.245 kΩ', codes: ['ohms-in-circuit'] },
  { text: '2.000 kΩ', codes: [] },
];

test('demo has a check for every step', () => assert.equal(DEMO_STEPS.length, expected.length));

DEMO_STEPS.forEach((step, i) => {
  test(`demo step ${i + 1}: ${step.title}`, () => {
    const r = run(i);
    const e = expected[i];
    assert.ok(r.m.placed, 'both probes placed');
    if (e.text) assert.equal(r.text, e.text);
    if (e.tier) assert.equal(r.m.fuse && r.m.fuse.tier, e.tier);
    assert.deepEqual([...r.codes].sort(), [...e.codes].sort());
    const extra = r.issues.filter((x) => x !== 'auto-ground');
    assert.deepEqual(extra, e.issues || [], 'circuit check stays clean except where the step means it');
  });
});
