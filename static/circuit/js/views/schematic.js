/* Schematic view: renders the circuit model as SVG and answers "what's under this point?".
   It only reads the model; app.js owns state and editing. */

import { shapeOf, pinPos, labelSpots, wirePoints, pathD, splitPoly, nearestOn, pointAt, polyLength, rotate } from './symbols.js';
import { formatEng } from '../core/units.js';

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const r1 = (n) => Math.round(n * 10) / 10;

/** "1.00 kΩ" → "1 kΩ", "4.70 kΩ" → "4.7 kΩ" */
export function short(value, unit) {
  const s = formatEng(value, unit);
  return s.includes('.') ? s.replace(/(\.\d*?)0+(?=\s|$)/, '$1').replace(/\.(?=\s|$)/, '') : s;
}

export function valueLabel(c) {
  const p = c.params;
  switch (c.type) {
    case 'resistor': return short(p.R, 'Ω');
    case 'vsource': return c.style === 'battery' || !(p.ilimit > 0) ? short(p.V, 'V') : `${short(p.V, 'V')} · ${short(p.ilimit, 'A')} max`;
    case 'isource': return short(p.I, 'A');
    case 'switch': return p.closed ? 'closed' : 'open';
    default: return '';
  }
}

/* --------------------------------------------------------------- lookup */

export function indexCircuit(circuit) {
  const comps = new Map(circuit.components.map((c) => [c.id, c]));
  const termPos = (term) => {
    const m = /^(.*)\.([^.]+)$/.exec(term);
    const c = m && comps.get(m[1]);
    return c && shapeOf(c.type).pins[m[2]] ? pinPos(c, m[2]) : null;
  };
  const route = (w) => {
    const A = termPos(w.a), B = termPos(w.b);
    return A && B ? wirePoints(A, B, (w.layout && w.layout.bend) || 'hv') : null;
  };
  const wiresAt = new Map();
  for (const w of circuit.wires) for (const t of [w.a, w.b]) wiresAt.set(t, (wiresAt.get(t) || 0) + 1);
  return { comps, termPos, route, wiresAt };
}

/** Gap fractions for drawing a cut wire. */
function cutGap(pts) {
  const L = polyLength(pts) || 1;
  const g = Math.min(18, L * 0.4) / L;
  return [0.5 - g / 2, 0.5 + g / 2];
}

/** The terminal a probe attachment touches: a pin, or one side of a (possibly cut) wire. */
export function attachTerm(circuit, att) {
  if (!att) return null;
  if (att.kind === 'pin') return att.term;
  const w = circuit.wires.find((x) => x.id === att.id);
  if (!w) return null;
  return w.cut && att.t > 0.5 ? `${w.id}.b` : `${w.id}.a`;
}

export function attachPoint(ix, circuit, att) {
  if (!att) return null;
  if (att.kind === 'pin') return ix.termPos(att.term);
  const w = circuit.wires.find((x) => x.id === att.id);
  const pts = w && ix.route(w);
  return pts ? pointAt(pts, att.t) : null;
}

/** What's at a board point, for probes and wiring: a pin (preferred) or a wire. */
export function findTarget(ix, circuit, p, { pinRadius = 14, wireRadius = 10, allowCutGap = false } = {}) {
  let best = null;
  for (const c of circuit.components) {
    for (const pin of Object.keys(shapeOf(c.type).pins)) {
      const q = pinPos(c, pin);
      const d = Math.hypot(q[0] - p[0], q[1] - p[1]);
      if (d <= pinRadius && (!best || d < best.dist)) best = { kind: 'pin', term: `${c.id}.${pin}`, point: q, dist: d };
    }
  }
  if (best) return best;
  for (const w of circuit.wires) {
    const pts = ix.route(w);
    if (!pts) continue;
    const n = nearestOn(pts, p);
    if (n.dist > wireRadius) continue;
    if (w.cut && !allowCutGap) {
      const [g0, g1] = cutGap(pts);
      if (n.t > g0 && n.t < g1) continue;
    }
    if (!best || n.dist < best.dist) best = { kind: 'wire', id: w.id, t: n.t, point: n.point, dist: n.dist };
  }
  return best;
}

/* --------------------------------------------------------------- render */

/**
 * s: { circuit, sel, highlight: Set, result, overlay, probes: { red: {point}, black: {point} },
 *      pending: { from: [x,y], to: [x,y], bend }, ghost: comp | null, target: point | null }
 */
export function renderBoard(s) {
  const { circuit, result } = s;
  const ix = indexCircuit(circuit);
  const sel = s.sel || {};
  const hl = s.highlight || new Set();
  const out = [];

  // wires
  out.push('<g class="wires">');
  for (const w of circuit.wires) {
    const pts = ix.route(w);
    if (!pts) continue;
    const cls = ['wire', sel.kind === 'wire' && sel.id === w.id ? 'sel' : '', hl.has(w.id) ? 'hl' : '', w.cut ? 'cut' : ''].join(' ');
    let line;
    if (w.cut) {
      const [g0, g1] = cutGap(pts);
      const [h1, h2] = splitPoly(pts, g0, g1);
      const e1 = h1[h1.length - 1], e2 = h2[0];
      line = `<path class="wire-line" d="${pathD(h1)}"/><path class="wire-line" d="${pathD(h2)}"/>
        <circle class="cut-end" cx="${r1(e1[0])}" cy="${r1(e1[1])}" r="3.5"/><circle class="cut-end" cx="${r1(e2[0])}" cy="${r1(e2[1])}" r="3.5"/>`;
    } else line = `<path class="wire-line" d="${pathD(pts)}"/>`;
    out.push(`<g class="${cls}" data-hit="wire" data-id="${esc(w.id)}"><path class="wire-hit" d="${pathD(pts)}"/>${line}</g>`);
  }
  out.push('</g>');

  // parts
  out.push('<g class="parts">');
  for (const c of circuit.components) {
    if (c.type === 'junction') continue;
    out.push(partSVG(c, {
      sel: sel.kind === 'comp' && sel.id === c.id,
      hl: hl.has(c.id),
    }));
  }
  out.push('</g>');

  // connection dots: junctions, and pins where 3+ things meet
  out.push('<g class="dots">');
  for (const c of circuit.components) {
    for (const pin of Object.keys(shapeOf(c.type).pins)) {
      const term = `${c.id}.${pin}`;
      const n = (ix.wiresAt.get(term) || 0) + (c.type === 'junction' ? 0 : 1);
      const [x, y] = pinPos(c, pin);
      if (c.type === 'junction') {
        const cls = ['junction', n >= 3 ? 'tee' : '', sel.kind === 'comp' && sel.id === c.id ? 'sel' : '', n === 0 ? 'lonely' : ''].join(' ');
        out.push(`<circle class="${cls}" cx="${x}" cy="${y}" r="${n >= 3 ? 4.5 : 3}"/>`);
      } else if (n >= 3) out.push(`<circle class="tee" cx="${x}" cy="${y}" r="4.5"/>`);
    }
  }
  out.push('</g>');

  // pin hotspots (on top so they win the click)
  out.push('<g class="pins">');
  for (const c of circuit.components) {
    for (const pin of Object.keys(shapeOf(c.type).pins)) {
      const [x, y] = pinPos(c, pin);
      const j = c.type === 'junction';
      out.push(`<circle class="pin ${j ? 'jpin' : ''}" data-hit="pin" data-term="${esc(c.id)}.${pin}" ${j ? `data-junction="${esc(c.id)}"` : ''}
        cx="${x}" cy="${y}" r="${j ? 8 : 7}"/>`);
    }
  }
  out.push('</g>');

  if (s.overlay && result && result.ok) out.push(overlaySVG(circuit, ix, result));

  // probes
  out.push('<g class="probes">');
  for (const which of ['black', 'red']) {
    const p = s.probes && s.probes[which];
    if (!p || !p.point) continue;
    const [x, y] = p.point;
    const dx = which === 'red' ? 1 : -1;
    out.push(`<g class="probe ${which} ${p.dragging ? 'dragging' : ''} ${p.loose ? 'loose' : ''}" data-hit="probe" data-probe="${which}"
        transform="translate(${r1(x)} ${r1(y)})">
      <path class="probe-cord" d="M${dx * 30} -44C${dx * 50} -70 ${dx * 70} -70 ${dx * 90} -80"/>
      <path class="probe-body" d="M${dx * 6} -8L${dx * 30} -44"/>
      <circle class="probe-tip" r="5"/>
      <text class="probe-label" x="${dx * 36}" y="-48" text-anchor="${dx > 0 ? 'start' : 'end'}">${which === 'red' ? 'RED' : 'BLACK'}</text>
    </g>`);
  }
  out.push('</g>');

  // previews
  out.push('<g class="preview">');
  if (s.target) out.push(`<circle class="target" cx="${r1(s.target[0])}" cy="${r1(s.target[1])}" r="11"/>`);
  if (s.pending) {
    out.push(`<path class="pending" d="${pathD(wirePoints(s.pending.from, s.pending.to, s.pending.bend))}"/>`);
  }
  if (s.ghost) out.push(`<g class="ghost">${partSVG(s.ghost, {})}</g>`);
  out.push('</g>');
  return out.join('');
}

function partSVG(c, { sel, hl }) {
  const s = shapeOf(c.type);
  const { x, y, rot = 0 } = c.layout;
  const [hx, hy, hw, hh] = s.hit;
  const lab = labelSpots(c);
  const showLabels = c.type !== 'ground' && c.type !== 'junction';
  const cls = ['part', `t-${c.type}`, sel ? 'sel' : '', hl ? 'hl' : '', c.style ? `s-${c.style}` : ''].join(' ');
  return `<g class="${cls}" data-hit="comp" data-id="${esc(c.id)}">
    <g transform="translate(${x} ${y}) rotate(${rot * 90})">
      <rect class="part-hit" x="${hx - 4}" y="${hy - 4}" width="${hw + 8}" height="${hh + 8}" rx="6"/>
      ${s.draw(c)}
    </g>
    ${showLabels ? `<text class="pname" x="${lab.name[0]}" y="${lab.name[1]}" text-anchor="${lab.name[2]}">${esc(c.id)}</text>
    <text class="pval" x="${lab.value[0]}" y="${lab.value[1]}" text-anchor="${lab.value[2]}">${esc(valueLabel(c))}</text>` : ''}
  </g>`;
}

function overlaySVG(circuit, ix, result) {
  const out = ['<g class="overlay">'];
  // node voltages, one chip per node at its first visible pin
  for (const n of result.nodes) {
    if (n.floating || n.name === 'GND') continue;
    const term = n.terminals.find((t) => !t.startsWith('~') && ix.termPos(t));
    if (!term) continue;
    const [x, y] = ix.termPos(term);
    const text = short(n.v, 'V');
    const w = text.length * 7 + 10;
    out.push(`<g class="vchip" transform="translate(${x + 8} ${y - 24})"><rect width="${w}" height="17" rx="5"/>
      <text x="${w / 2}" y="12.5" text-anchor="middle">${esc(text)}</text></g>`);
  }
  // branch currents with an arrow for direction
  for (const c of circuit.components) {
    const r = result.components[c.id];
    const pins = Object.keys(shapeOf(c.type).pins);
    if (!r || pins.length !== 2 || Math.abs(r.i) < 1e-12) continue;
    const a = pinPos(c, pins[0]), b = pinPos(c, pins[1]);
    let dx = b[0] - a[0], dy = b[1] - a[1];
    if (r.i < 0) { dx = -dx; dy = -dy; }
    const arrow = Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? '→' : '←') : (dy > 0 ? '↓' : '↑');
    const lab = labelSpots(c);
    const [x, y, anchor] = lab.value;
    out.push(`<text class="amp" x="${x}" y="${y + 16}" text-anchor="${anchor}">${arrow} ${esc(short(Math.abs(r.i), 'A'))}</text>`);
  }
  out.push('</g>');
  return out.join('');
}

/** Bounding box of everything on the board, for "fit". */
export function bounds(circuit) {
  const xs = [], ys = [];
  for (const c of circuit.components) {
    const [hx, hy, hw, hh] = shapeOf(c.type).hit;
    for (const [px, py] of [[hx, hy], [hx + hw, hy + hh]]) {
      const [dx, dy] = rotate([px, py], c.layout.rot);
      xs.push(c.layout.x + dx); ys.push(c.layout.y + dy);
    }
    for (const pin of Object.values(shapeOf(c.type).pins)) {
      const [dx, dy] = rotate(pin, c.layout.rot);
      xs.push(c.layout.x + dx); ys.push(c.layout.y + dy);
    }
  }
  if (!xs.length) return null;
  return { x0: Math.min(...xs) - 40, y0: Math.min(...ys) - 50, x1: Math.max(...xs) + 60, y1: Math.max(...ys) + 50 };
}
