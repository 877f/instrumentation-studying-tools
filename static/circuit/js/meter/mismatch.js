/* Mistakes the meter setup can make, found from the circuit's layout and the meter state,
   independent of the reading. Each warning says why it's bad in plain words. */

import { buildNetlist, UnionFind } from '../core/netlist.js';
import { formatEng } from '../core/units.js';

const list = (a) => (a.length < 3 ? a.join(' and ') : `${a.slice(0, -1).join(', ')} and ${a.at(-1)}`);
const w = (level, code, title, message) => ({ level, code, title, message });

/**
 * ctx: { profile, meter, dial, jack, circuit, registry, base (solve without meter), withMeter, reading, fuse }
 * returns [{ level: 'danger'|'warning'|'info', code, title, message }]
 */
export function findMismatches(ctx) {
  const { profile, meter, dial, jack } = ctx;
  const out = [];
  const fn = dial.function;
  const shunt = jack.kind === 'current' ? shuntOf(profile, jack, dial) : null;

  if (dial.unsupported) {
    out.push(w('info', 'unsupported', 'AC is coming later', `${dial.label} needs the AC update. For now the meter measures DC.`));
  }
  if (jack.kind === 'current' && fn !== 'current') {
    out.push(w('danger', 'lead-in-current-jack', `Red lead is in the ${jack.label} jack`,
      `The dial is on ${dial.label}, but the ${jack.label} jack doesn't ${fn === 'resistance' ? 'measure resistance' : 'measure voltage'}. `
      + `Inside the meter it runs through the ${profile.fuses[jack.fuse].label} fuse and a ${formatEng(shunt, 'Ω')} shunt straight to COM`
      + `${fn === 'off' ? ', even with the meter off' : ''}. Touch the probes across anything with voltage and you've put a near short `
      + 'across it. Move the red lead to V Ω.'));
  }
  if (fn === 'current' && jack.kind !== 'current') {
    out.push(w('warning', 'current-in-voltage-jack', 'Red lead is in the V Ω jack',
      `For current, the current has to flow into the meter through the ${dial.inputs.map((j) => jackLabel(profile, j)).join(' or ')} jack. `
      + 'The V Ω jack is a 10 MΩ input, so the reading stays at 0.'));
  }
  if (fn === 'current' && jack.kind === 'current' && !dial.inputs.includes(jack.id)) {
    out.push(w('warning', 'wrong-current-jack', `${dial.label} doesn't read the ${jack.label} jack`,
      `${dial.label} reads through the ${dial.inputs.map((j) => jackLabel(profile, j)).join(' or ')} jack. `
      + `Move the red lead there, or turn the dial to the setting for the ${jack.label} jack.`));
  }
  if (meter.fuses[jack.fuse] === 'blown') {
    out.push(w('danger', 'fuse-blown', `The ${profile.fuses[jack.fuse].label} fuse is blown`,
      `Nothing can flow through the ${jack.label} jack until the fuse is replaced, so current readings stay at 0.`));
  }

  const { red, black } = meter.probes;
  if (!red || !black || !ctx.base.ok) return out;

  const net = buildNetlist(ctx.circuit, ctx.registry);
  const nr = net.nodeOf(red), nb = net.nodeOf(black);
  const parts = net.comps.filter((c) => !c.def.isGround && c.def.pins.length === 2);
  const across = parts.filter((c) => {
    const [a, b] = c.def.pins.map((p) => c.pins[p]);
    return (a === nr && b === nb) || (a === nb && b === nr);
  });

  // Current jack with the probes across something instead of in series.
  if (jack.kind === 'current' && meter.fuses[jack.fuse] !== 'blown') {
    const cutPair = (ctx.circuit.wires || []).some((x) => {
      if (!x.cut) return false;
      const a = net.nodeOf(`${x.id}.a`), b = net.nodeOf(`${x.id}.b`);
      return (a === nr && b === nb) || (a === nb && b === nr);
    });
    if (nr === nb) {
      out.push(w('info', 'current-same-node', 'Both probes are on the same node',
        'The meter reads about 0, because no current has to pass through it. To measure current, cut a wire and put the '
        + 'probes on the two cut ends.'));
    } else if (!cutPair) {
      const sources = across.filter((c) => c.type === 'vsource' || c.type === 'isource');
      const what = across.length ? list(across.map((c) => c.id)) : 'part of the circuit';
      const fault = ctx.fuse ? formatEng(ctx.fuse.current, 'A') : null;
      const limited = sources.filter((c) => ctx.withMeter.components[c.id]?.extra?.mode === 'CC');
      out.push(w('danger', 'current-across', `Ammeter across ${what}`,
        `In a current setting the meter is nearly a dead short (${formatEng(shunt, 'Ω')}). With the leads across ${what}, `
        + `it shorts ${across.length === 1 ? 'it' : 'that'} out instead of measuring the current through it`
        + `${fault ? `: ${fault} flows through the meter` : ''}. To measure current, cut a wire and put the probes on the two cut `
        + 'ends, so the current has to go through the meter.'
        + (limited.length ? ` ${list(limited.map((c) => c.id))}'s current limit saved the fuse this time. On a battery or an `
          + "unlimited supply, it wouldn't." : '')));
    }
  }

  // Ohms on a live circuit, or on a part that's still wired in.
  if (fn === 'resistance' && jack.id === 'VOhm') {
    const pathsOf = (c) => (c.def.paths ? c.def.paths(c.params, c.def.initState ? c.def.initState(c.params) : {}) : []);
    const isSource = (c) => c.type === 'vsource' || c.type === 'isource';
    // The measured network: everything joined to the probes through passive parts.
    const passive = new UnionFind();
    for (const c of net.comps) if (!isSource(c)) for (const [p, q] of pathsOf(c)) passive.union(c.pins[p], c.pins[q]);
    const reach = new Set([passive.find(nr), passive.find(nb)]);
    // A source can push current through it only if both its terminals reach it.
    const live = net.comps.filter((c) => isSource(c) && ((c.type === 'vsource' && c.params.V !== 0) || (c.type === 'isource' && c.params.I !== 0))
      && reach.has(passive.find(c.pins.p)) && reach.has(passive.find(c.pins.n)));
    if (live.length) {
      out.push(w('danger', 'ohms-live', 'Measuring ohms on a powered circuit',
        `${list(live.map((c) => c.id))} ${live.length > 1 ? 'are' : 'is'} connected to what you're measuring. An ohmmeter pushes its `
        + "own small current and reads the voltage it makes; the circuit's own voltage swamps that, so the reading is garbage. "
        + 'On a real meter, ohms on a live circuit can also damage the meter. Turn the supply off and disconnect it first.'));
    }
    const target = across.find((c) => c.type === 'resistor');
    if (target) {
      const rest = new UnionFind();
      for (const c of net.comps) if (c.id !== target.id) for (const [p, q] of pathsOf(c)) rest.union(c.pins[p], c.pins[q]);
      if (rest.find(nr) === rest.find(nb)) {
        // Name the parts the meter's test current actually flows through.
        const test = Math.abs(ctx.withMeter.components['~ohms']?.extra?.supplyCurrent || 0);
        const others = net.comps.filter((c) => c.id !== target.id && !c.def.isGround && !c.hidden
          && test > 0 && Math.abs(ctx.withMeter.components[c.id]?.i || 0) > 0.01 * test).map((c) => c.id);
        const r = ctx.reading && Number.isFinite(ctx.reading.value) ? formatEng(ctx.reading.value, 'Ω') : null;
        out.push(w('warning', 'ohms-in-circuit', `${target.id} is still connected in the circuit`,
          `${r ? `The meter reads ${r}, but ${target.id} is ${formatEng(target.params.R, 'Ω')}. ` : ''}`
          + `The meter's test current also flows through ${others.length ? list(others.slice(0, 4)) + (others.length > 4 ? ' and more' : '')
            : `the other parts around ${target.id}`}, so it measures them in parallel. Lift one leg of ${target.id} out of the circuit `
          + 'to measure it alone.'));
      }
    }
  }

  if (fn === 'voltage' && dial.danger && ctx.reading && Math.abs(ctx.reading.value) > dial.danger) {
    out.push(w('danger', 'overvoltage', `Over ${dial.danger} V`,
      `${formatEng(ctx.reading.value, 'V')} is beyond what this meter is rated for. Above its rating the input protection can arc over, `
      + 'and that can hurt you, not just the meter. Never do this on a real bench.'));
  }
  return out;
}

export function shuntOf(profile, jack, dial) {
  const sh = profile.inputs[jack.id].shunt;
  return sh[dial.id] ?? sh.default;
}

function jackLabel(profile, id) {
  return profile.jacks.find((j) => j.id === id).label;
}
