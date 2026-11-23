/* The meter as a circuit element: readings, fuse tiers and setup mistakes. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { builder, close, assertFinite } from './helpers.mjs';
import { measure, initialMeter, formatReading } from '../../static/circuit/js/meter/meter-model.js';

const profile = JSON.parse(readFileSync(new URL('../../static/circuit/meters/fluke-87v.json', import.meta.url), 'utf8'));
const meter = (dial, red, probes, extra = {}) => ({ ...initialMeter(), dial, red, probes: { red: probes[0], black: probes[1] }, ...extra });
const codes = (m) => m.warnings.map((x) => x.code);

function divider(opts = {}) {
  const b = builder();
  b.V('top', 'gnd', 12, { r: 0.01, ilimit: null, ...opts });
  b.R('top', 'mid', 1000);
  b.R('mid', 'gnd', 2000);
  return b;
}

test('DC volts across R2 reads 8 V, loaded slightly by the 10 MΩ input', () => {
  const b = divider();
  const m = measure(b.circuit, profile, meter('dcv', 'VOhm', ['R2.a', 'R2.b']));
  // 2k ∥ 10M = 1999.6 Ω → 12 × 1999.6 / (1000.01 + 1999.6) ≈ 7.9994 V
  close(m.display.value, 12 * (2000 * 1e7 / (2000 + 1e7)) / (1000.01 + 2000 * 1e7 / (2000 + 1e7)), 1e-9);
  assert.equal(m.display.text, '8.00', 'above 6 V, so it auto-ranges to the 60 V range');
  assert.equal(m.display.unit, 'V');
  assert.equal(m.fuse, null);
  assert.deepEqual(codes(m), []);
  // reversed leads: negative
  const r = measure(b.circuit, profile, meter('dcv', 'VOhm', ['R2.b', 'R2.a']));
  assert.equal(r.display.text, '-8.00');
});

test('auto-ranging and OL', () => {
  const ranges = profile.dial.find((d) => d.id === 'dcv').ranges;
  assert.equal(formatReading(0.5, ranges).text, '0.500');
  assert.equal(formatReading(12, ranges).text, '12.00');
  assert.equal(formatReading(230, ranges).text, '230.0');
  assert.equal(formatReading(1200, ranges).text, 'OL');
  const mv = profile.dial.find((d) => d.id === 'mv').ranges;
  assert.deepEqual([formatReading(0.0123, mv).text, formatReading(0.0123, mv).unit], ['12.3', 'mV']);
});

test('current through a cut wire: meter in series reads the loop current, SAFE', () => {
  const b = divider();
  const w = b.wire('mid', 'x');               // the divider's bottom now goes through wire w
  b.circuit.wires.find((x) => x.a === 'R2.a' || x.b === 'R2.a').b = 'x';
  b.circuit.wires.find((x) => x.id === w).cut = true;
  const m = measure(b.circuit, profile, meter('dca', 'mAuA', [`${w}.a`, `${w}.b`]));
  // 12 / (1000 + 2000 + 1.8 + 0.01)
  close(m.display.value, 12 / 3001.81);
  assert.equal(m.display.text, '4.00');
  assert.equal(m.display.unit, 'mA');
  assert.equal(m.fuse.tier, 'safe');
  assert.deepEqual(codes(m), []);
});

test('mA jack across a 12 V bench supply: limited to 100 mA vs unlimited', () => {
  const limited = divider({ ilimit: 0.1 });
  const a = measure(limited.circuit, profile, meter('dca', 'mAuA', ['V1.p', 'V1.n']));
  assert.equal(a.result.components.V1.extra.mode, 'CC');
  // 100 mA from the supply, split between the 1.8 Ω meter and the 3 kΩ divider
  close(a.fuse.current, 0.1 * 3000.0 / 3001.8, 1e-6);
  assert.equal(a.fuse.tier, 'safe');
  assert.ok(codes(a).includes('current-across'), 'still flagged even though the limit saved it');
  assert.match(a.warnings.find((x) => x.code === 'current-across').message, /V1's current limit saved the fuse/);

  const open = divider();
  const b = measure(open.circuit, profile, meter('dca', 'mAuA', ['V1.p', 'V1.n']));
  // 12 V / (0.01 + 1.8 Ω) ≈ 6.63 A through a 440 mA fuse
  close(b.fuse.current, 12 / 1.81, 1e-4);         // the divider draws a hair alongside
  assert.equal(b.fuse.tier, 'blows');
  assert.equal(b.blows, 'mA');
  assert.equal(b.display.text, '0.00', 'fuse open: the meter reads 0');
  assert.ok(!b.result.components['~shunt'], 're-solved with the fuse open');
  close(b.result.voltage('mid'), 8, 1e-3, 'circuit back to normal after the fuse opens');
  assert.ok(b.fault.components['~shunt']);
  assertFinite(b.display);
});

test('A jack across a battery: flagged; a 9 V battery survives, a car battery blows the 11 A fuse', () => {
  const nine = builder();
  nine.V('p', 'gnd', 9, { r: 1.5, ilimit: null });
  const a = measure(nine.circuit, profile, meter('dca', 'A', ['V1.p', 'V1.n']));
  close(a.fuse.current, 9 / 1.53);
  assert.equal(a.fuse.tier, 'safe');
  assert.equal(a.display.text, '5.882');
  assert.ok(codes(a).includes('current-across'));

  const car = builder();
  car.V('p', 'gnd', 12.6, { r: 0.01, ilimit: null });
  const b = measure(car.circuit, profile, meter('dca', 'A', ['V1.p', 'V1.n']));
  assert.equal(b.fuse.tier, 'blows');
  assert.equal(b.blows, 'A');
});

test('fuse tiers: OVER SPEC in the mA jack, 30-second zone in the A jack', () => {
  const b = builder();
  b.V('s', 'gnd', 12, { r: 0.01, ilimit: null });
  b.R('s', 'x', 27);
  b.wire('x', 'y');
  b.circuit.wires.at(-1).cut = true;
  const cut = b.circuit.wires.at(-1).id;
  b.R('y', 'gnd', 0.001);
  const over = measure(b.circuit, profile, meter('dca', 'mAuA', [`${cut}.a`, `${cut}.b`]));
  // 12 / (27 + 1.8 + 0.011) ≈ 0.4165 A: over 400 mA, under the 440 mA fuse
  assert.equal(over.fuse.tier, 'overspec');
  assert.match(over.fuse.message, /Outside rated input — fuse may survive, don't do this/);

  b.circuit.components.find((c) => c.id === 'R1').params.R = 0.77;
  const hot = measure(b.circuit, profile, meter('dca', 'A', [`${cut}.a`, `${cut}.b`]));
  // 12 / (0.77 + 0.03 + 0.011) ≈ 14.8 A
  assert.equal(hot.fuse.tier, 'shortterm');
  assert.match(hot.fuse.message, /Survivable for ≤30 s/);
});

test('red lead left in a current jack with the dial on volts: LEAd plus a danger warning', () => {
  const b = divider();
  const m = measure(b.circuit, profile, meter('dcv', 'A', ['V1.p', 'V1.n']));
  assert.equal(m.display.text, 'LEAd');
  assert.ok(codes(m).includes('lead-in-current-jack'));
  assert.equal(m.blows, 'A', '12 V across 0.04 Ω is 300 A');
  // still dangerous with the meter OFF
  const off = measure(b.circuit, profile, meter('off', 'mAuA', ['V1.p', 'V1.n']));
  assert.ok(codes(off).includes('lead-in-current-jack'));
  assert.equal(off.blows, 'mA');
});

test('ohms on a live circuit is flagged', () => {
  const b = divider();
  const m = measure(b.circuit, profile, meter('ohm', 'VOhm', ['R2.a', 'R2.b']));
  assert.ok(codes(m).includes('ohms-live'));
  assert.match(m.warnings.find((x) => x.code === 'ohms-live').message, /V1 is connected/);
});

test('in-circuit ohms: reads the parallel combination and says to lift a leg', () => {
  const b = builder();
  b.V('s', 'gnd', 12, { r: 0.01, ilimit: null });
  b.S('s', 't', false);                        // supply switched off
  b.R('t', 'm', 1000);
  b.R('m', 'gnd', 2000);                       // R2: the one we measure
  b.R('m', 'gnd', 3000);                       // R3 in parallel with it
  const m = measure(b.circuit, profile, meter('ohm', 'VOhm', ['R2.a', 'R2.b']));
  close(m.display.value, 1200, 1e-6);          // 2k ∥ 3k
  assert.equal(m.display.text, '1.200');
  assert.equal(m.display.unit, 'kΩ');
  assert.ok(!codes(m).includes('ohms-live'), 'open switch isolates the supply');
  const w = m.warnings.find((x) => x.code === 'ohms-in-circuit');
  assert.ok(w);
  assert.match(w.message, /reads 1\.20 kΩ, but R2 is 2\.00 kΩ/);
  assert.match(w.message, /flows through R3/);
  assert.match(w.message, /Lift one leg of R2/);
});

test('ohms on a lifted resistor reads its value with no warnings; open probes read OL', () => {
  const b = builder();
  b.R('a', 'b', 4700);
  const m = measure(b.circuit, profile, meter('ohm', 'VOhm', ['R1.a', 'R1.b']));
  assert.equal(m.display.text, '4.700');
  assert.equal(m.display.unit, 'kΩ');
  assert.deepEqual(codes(m), []);
  const open = measure(b.circuit, profile, meter('ohm', 'VOhm', ['R1.a', 'R1.a']));
  assert.equal(open.display.text, '0.0', 'shorted probes read 0');
  const air = builder();
  air.R('a', 'b', 4700);
  air.R('c', 'd', 4700);
  assert.equal(measure(air.circuit, profile, meter('ohm', 'VOhm', ['R1.a', 'R2.a'])).display.text, 'OL');
});

test('blown fuse stays blown: current reads 0 until it is replaced', () => {
  const b = divider();
  const w = b.wire('mid', 'x');
  b.circuit.wires.find((x) => x.a === 'R2.a' || x.b === 'R2.a').b = 'x';
  b.circuit.wires.find((x) => x.id === w).cut = true;
  const m = measure(b.circuit, profile, meter('dca', 'mAuA', [`${w}.a`, `${w}.b`], { fuses: { mA: 'blown', A: 'ok' } }));
  assert.equal(m.display.text, '0.00');
  assert.ok(codes(m).includes('fuse-blown'));
  assert.equal(m.fuse, null);
});

test('current dial with the red lead in V Ω reads 0 and explains why', () => {
  const b = divider();
  const m = measure(b.circuit, profile, meter('dca', 'VOhm', ['V1.p', 'V1.n']));
  assert.equal(m.display.value, 0);
  assert.ok(codes(m).includes('current-in-voltage-jack'));
});

test('one probe placed: no measurement, no crash', () => {
  const b = divider();
  const m = measure(b.circuit, profile, meter('dcv', 'VOhm', ['R2.a', null]));
  assert.equal(m.placed, false);
  assert.equal(m.display.text, '0.000');
});
