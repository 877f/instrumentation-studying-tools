/* The multimeter as a circuit element.

   When both probes are placed, the meter goes INTO the netlist as real parts, chosen by the
   jack the red lead is in and the dial position, and the circuit is re-solved:
     red in V Ω, voltage dial   → 10 MΩ between the probes
     red in V Ω, Ω dial         → the meter's own test source (a few volts behind a resistance)
     red in mA µA or A          → fuse + shunt resistor straight to COM, whatever the dial says
   That's what makes the fuse check honest: the classic blown fuse is a red lead left in a
   current jack while probing across a supply, and here that's simply a 0.03 Ω part across it. */

import { solve } from '../core/solver.js';
import { registry as defaultRegistry } from '../components/registry.js';
import { fuseVerdict } from './fuse.js';
import { findMismatches, shuntOf } from './mismatch.js';

export function initialMeter() {
  return { dial: 'dcv', red: 'VOhm', fuses: { mA: 'ok', A: 'ok' }, probes: { red: null, black: null } };
}

export const dialOf = (profile, id) => profile.dial.find((d) => d.id === id);
export const jackOf = (profile, id) => profile.jacks.find((j) => j.id === id);

/** The parts the meter adds between its probes, or null if both probes aren't placed. */
export function meterParts(profile, meter, { fuseOpen = false } = {}) {
  const { red, black } = meter.probes;
  if (!red || !black) return null;
  const dial = dialOf(profile, meter.dial);
  const jack = jackOf(profile, meter.red);
  let comp = null, role;
  if (jack.kind === 'current') {
    if (fuseOpen || meter.fuses[jack.fuse] === 'blown') return { role: 'open', components: [], wires: [] };
    comp = { id: '~shunt', type: 'resistor', params: { R: shuntOf(profile, jack, dial), Pmax: 1e9 } };
    role = 'shunt';
  } else if (dial.function === 'off') {
    return { role: 'open', components: [], wires: [] };
  } else if (dial.function === 'resistance') {
    comp = { id: '~ohms', type: 'vsource', params: { V: profile.ohms.openVoltage, r: profile.ohms.sourceResistance, ilimit: null } };
    role = 'ohms';
  } else {
    comp = { id: '~input', type: 'resistor', params: { R: profile.inputs.VOhm.impedance, Pmax: 1e9 } };
    role = 'input';
  }
  comp.hidden = true;
  const [pa, pb] = comp.type === 'vsource' ? ['p', 'n'] : ['a', 'b'];
  return {
    role,
    components: [comp],
    wires: [
      { id: '~lead-red', a: `${comp.id}.${pa}`, b: red, hidden: true },
      { id: '~lead-black', a: `${comp.id}.${pb}`, b: black, hidden: true },
    ],
  };
}

export function withParts(circuit, parts) {
  if (!parts) return circuit;
  return { ...circuit, components: [...circuit.components, ...parts.components], wires: [...circuit.wires, ...parts.wires] };
}

/** Pick the lowest range that fits, like auto-ranging. */
export function formatReading(value, ranges) {
  const r = ranges.find((x) => Math.abs(value) <= x.max * (1 + 1e-12));
  const top = ranges[ranges.length - 1];
  if (!r) return { text: 'OL', unit: top.unit, value, ol: true };
  let text = (value / r.scale).toFixed(r.decimals);
  if (/^-0\.?0*$/.test(text)) text = text.slice(1);
  return { text, unit: r.unit, value, ol: false };
}

function readingFor(profile, meter, dial, jack, role, result, blown) {
  const { red, black } = meter.probes;
  const fn = dial.function;
  if (fn === 'off') return { text: '', unit: '', value: null };
  if (dial.unsupported) return { text: 'AC', unit: '', value: null };
  const lead = { text: profile.leadAlert.display, unit: '', value: null, alert: true };
  if (fn === 'voltage' || fn === 'resistance') {
    if (jack.kind === 'current') return lead;
  }
  if (fn === 'current' && jack.kind === 'current' && !dial.inputs.includes(jack.id)) return lead;
  const zeroOf = (ranges) => formatReading(0, ranges);
  if (!red || !black) {
    if (fn === 'resistance') return { text: 'OL', unit: dial.ranges.at(-1).unit, value: Infinity, ol: true };
    return zeroOf(fn === 'current' ? (dial.rangesByJack[jack.id] || Object.values(dial.rangesByJack)[0]) : dial.ranges);
  }
  if (!result.ok) return { text: '----', unit: '', value: null };

  if (fn === 'voltage') return formatReading(result.voltage(red, black) ?? 0, dial.ranges);
  if (fn === 'resistance') {
    const v = result.voltage(red, black) ?? 0;
    const i = result.components['~ohms'] ? result.components['~ohms'].extra.supplyCurrent : 0;
    const R = i > 1e-15 ? v / i : Infinity;
    if (!(R >= 0) || !Number.isFinite(R)) return { text: 'OL', unit: dial.ranges.at(-1).unit, value: Infinity, ol: true };
    return formatReading(R, dial.ranges);
  }
  // current
  const ranges = dial.rangesByJack[jack.id] || Object.values(dial.rangesByJack)[0];
  if (jack.kind !== 'current' || role !== 'shunt' || blown) return zeroOf(ranges);
  return formatReading(result.components['~shunt'].i, ranges);
}

/**
 * Measure. Returns {
 *   placed, dial, jack, display: { text, unit, value, ol, alert },
 *   fuse: verdict or null, blows: 'mA'|'A'|null,
 *   base: solve without the meter, result: solve with the meter (fuse open if it blew),
 *   fault: solve with the meter before the fuse opened (only when it blew),
 *   warnings: [...]
 * }
 */
export function measure(circuit, profile, meter, opts = {}) {
  const registry = opts.registry || defaultRegistry;
  const dial = dialOf(profile, meter.dial);
  const jack = jackOf(profile, meter.red);
  const base = opts.base || solve(circuit, { registry });
  const parts = meterParts(profile, meter);
  const out = { placed: !!parts, dial, jack, base, result: base, fault: null, fuse: null, blows: null };

  let withMeter = base;
  if (parts) {
    withMeter = solve(withParts(circuit, parts), { registry });
    out.result = withMeter;
    if (parts.role === 'shunt' && withMeter.ok) {
      out.fuse = fuseVerdict(profile, jack, Math.abs(withMeter.components['~shunt'].i));
      if (out.fuse.tier === 'blows') {
        out.blows = jack.fuse;
        out.fault = withMeter;
        out.result = solve(withParts(circuit, meterParts(profile, meter, { fuseOpen: true })), { registry });
      }
    }
  }
  out.display = readingFor(profile, meter, dial, jack, parts && parts.role, out.result, out.blows);
  out.warnings = findMismatches({ profile, meter, dial, jack, circuit, registry, base, withMeter, reading: out.display, fuse: out.fuse });
  return out;
}

/** Solve issues that belong to the user's circuit, not the meter's internal parts. */
export function userIssues(result) {
  return result.issues.filter((i) => !(i.ids || []).some((id) => id.startsWith('~')));
}
