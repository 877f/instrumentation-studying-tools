/* Teacher demo: one board, eleven setups that walk through the right and wrong ways to use a meter.
   Each step sets every switch, cut and meter setting it cares about, so steps run in any order. */

import { createCircuit, addComponent, addWire } from './core/netlist.js';

export function buildDemo(registry) {
  const c = createCircuit();
  const add = (id, type, x, y, rot, params = {}, extra = {}) =>
    addComponent(c, registry, type, params, { id, layout: { x, y, rot }, ...extra });
  const w = (id, a, b, bend = 'hv') => addWire(c, a, b, { id, layout: { bend } });

  // Left: bench supply (100 mA limit) → switch → R1 → node A → R2 ∥ R3 → ground
  add('V1', 'vsource', 80, 220, 0, { V: 12, r: 0.01, ilimit: 0.1 });
  add('S1', 'switch', 160, 100, 0, { closed: true });
  add('R1', 'resistor', 280, 100, 0, { R: 1000, Pmax: 0.25 });
  add('J1', 'junction', 400, 100, 0);
  add('R2', 'resistor', 400, 200, 1, { R: 2000, Pmax: 0.25 });
  add('R3', 'resistor', 520, 200, 1, { R: 3300, Pmax: 0.25 });
  add('J2', 'junction', 400, 300, 0);
  add('GND1', 'ground', 400, 360, 0);
  w('W1', 'V1.p', 'S1.a', 'vh');
  w('W2', 'S1.b', 'R1.a');
  w('W_cur', 'R1.b', 'J1.j');                 // cut here to measure current
  w('W_leg', 'J1.j', 'R2.a');                 // cut here to "lift a leg" of R2
  w('W3', 'J1.j', 'R3.a', 'hv');
  w('W4', 'R2.b', 'J2.j');
  w('W5', 'R3.b', 'J2.j', 'vh');
  w('W6', 'J2.j', 'V1.n', 'hv');
  w('W7', 'GND1.g', 'J2.j');

  // Right: 9 V battery → switch → 10 Ω ¼ W resistor that's far too small for it
  add('B1', 'vsource', 640, 220, 0, { V: 9, r: 1.5, ilimit: null }, { style: 'battery' });
  add('S2', 'switch', 720, 100, 0, { closed: false });
  add('R4', 'resistor', 840, 200, 1, { R: 10, Pmax: 0.25 });
  add('GND2', 'ground', 640, 320, 0);
  w('W8', 'B1.p', 'S2.a', 'vh');
  w('W_hot', 'S2.b', 'R4.a', 'hv');           // cut here to measure the battery current
  w('W9', 'R4.b', 'B1.n', 'vh');
  w('W10', 'GND2.g', 'B1.n');
  return c;
}

const BASE = { switches: { S1: true, S2: false }, cuts: { W_cur: false, W_leg: false, W_hot: false } };
const pin = (term) => ({ kind: 'pin', term });
const wire = (id, t) => ({ kind: 'wire', id, t });

export const DEMO_STEPS = [
  {
    title: 'Voltage, done right',
    dial: 'dcv', red: 'VOhm', probes: [pin('R2.a'), pin('R2.b')],
    look: 'Red in V Ω, black in COM, dial on V⎓, leads across R2. It reads about 6.66 V with no warnings.',
    why: "A voltmeter goes across a part. Its 10 MΩ input barely loads the circuit, so it reads what's really there.",
  },
  {
    title: 'Leads reversed',
    dial: 'dcv', red: 'VOhm', probes: [pin('R2.b'), pin('R2.a')],
    look: 'Same voltage with a minus sign: −6.66 V.',
    why: 'Harmless on a DMM. The sign tells you the red lead is on the lower-voltage side.',
  },
  {
    title: 'Current, done right',
    dial: 'dca', red: 'mAuA', cuts: { W_cur: true }, probes: [wire('W_cur', 0.3), wire('W_cur', 0.7)],
    look: 'The wire between R1 and R2 is cut and the meter bridges the gap. All the current flows through it: about 5.34 mA, SAFE.',
    why: 'An ammeter goes in series. You have to break the circuit so the current has no way around the meter.',
  },
  {
    title: 'Ammeter across a supply (limit saves it)',
    dial: 'dca', red: 'mAuA', probes: [pin('V1.p'), pin('V1.n')],
    look: "The meter's 1.8 Ω shunt shorts the supply. Its 100 mA current limit holds the current under the fuse rating, so SAFE, but it's still flagged.",
    why: 'Across a source, an ammeter is a short circuit. A current-limited bench supply forgives it; a battery won’t (next step).',
  },
  {
    title: 'Forgot the red lead in mA',
    dial: 'dcv', red: 'mAuA', probes: [pin('B1.p'), pin('B1.n')],
    look: 'The dial says volts but the red lead is still in mA. Across the battery that’s 2.7 A into a 440 mA fuse: FUSE BLOWS, and the LCD shows LEAd.',
    why: 'The classic blown fuse. The current jacks are wired straight to COM through the fuse, whatever the dial says.',
  },
  {
    title: 'Right method, wrong jack',
    dial: 'dca', red: 'mAuA', switches: { S2: true }, cuts: { W_hot: true }, probes: [wire('W_hot', 0.3), wire('W_hot', 0.75)],
    look: 'In series this time, but the battery pushes about 0.68 A through R4. That’s over the 440 mA fuse: FUSE BLOWS.',
    why: 'Estimate the current before you measure (I = V ÷ R). Anything near or over 400 mA goes in the A jack.',
  },
  {
    title: 'Same circuit, A jack',
    dial: 'dca', red: 'A', switches: { S2: true }, cuts: { W_hot: true }, probes: [wire('W_hot', 0.3), wire('W_hot', 0.75)],
    look: 'Red in the A jack: it reads about 0.781 A, SAFE. The 11 A fuse has plenty of room. (R4 is overheating, though; that’s the next step.)',
    why: 'Start in the A jack when you don’t know the current, then move to mA if the reading is small.',
  },
  {
    title: 'A resistor that’ll cook',
    dial: 'dcv', red: 'VOhm', switches: { S2: true }, probes: [pin('R4.a'), pin('R4.b')], select: 'R4',
    look: 'R4 has about 7.8 V across it and burns about 6.1 W. It’s rated ¼ W. Check the Circuit check panel and R4’s power reading.',
    why: 'Power is I²R. Past its rating a resistor overheats, discolors and can burn open. Size the resistor for the power.',
  },
  {
    title: 'Ohms on a live circuit',
    dial: 'ohm', red: 'VOhm', probes: [pin('R2.a'), pin('R2.b')],
    look: 'S1 is closed, so V1 is still powering R2. The reading is meaningless and it’s flagged as danger.',
    why: 'An ohmmeter works by pushing its own small current. Any outside voltage swamps it, and on a real meter can damage it.',
  },
  {
    title: 'Ohms in circuit (power off)',
    dial: 'ohm', red: 'VOhm', switches: { S1: false }, probes: [pin('R2.a'), pin('R2.b')],
    look: 'Power is off, but it reads 1.245 kΩ instead of 2 kΩ: R3 is still in parallel.',
    why: 'The meter measures everything connected between its probes, not just the part you’re touching.',
  },
  {
    title: 'Lift a leg',
    dial: 'ohm', red: 'VOhm', switches: { S1: false }, cuts: { W_leg: true }, probes: [pin('R2.a'), pin('R2.b')],
    look: 'With one end of R2 disconnected, it reads 2.000 kΩ: its true value.',
    why: 'To measure a resistor, turn the power off and lift one leg out of the circuit.',
  },
].map((s) => ({ ...s, switches: { ...BASE.switches, ...(s.switches || {}) }, cuts: { ...BASE.cuts, ...(s.cuts || {}) } }));
