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
      info: s.blockInfo && s.blockInfo.get(c.id),
      vals: s.values ? s.values.get(c.id) : undefined,
      oneLine: s.values ? partBelow(c, circuit.components) : false,
    }));
  }
  out.push('</g>');

  // Req blocks shown open on the board: their inside, drawn small in a bubble above the block
  if (s.bubble) {
    for (const c of circuit.components) {
      if (c.type !== 'reqblock' || !c.expanded) continue;
      const g = bubbleGeom(c);
      const lead = g.lines.map(([x0, y0, x1, y1]) => `M${r1(x0)} ${r1(y0)}L${r1(x1)} ${r1(y1)}`).join('');
      out.push(`<g class="bubble ${sel.kind === 'comp' && sel.id === c.id ? 'sel' : ''}" data-hit="comp" data-id="${esc(c.id)}">
        <path class="bubble-lead" d="${lead}"/>
        <rect class="bubble-bg" x="${r1(g.left)}" y="${r1(g.top)}" width="${r1(g.W)}" height="${r1(g.H)}" rx="10"/>
        <g class="bubble-inner" transform="translate(${r1(g.left - g.ib.x0 * g.k)} ${r1(g.top - g.ib.y0 * g.k)}) scale(${g.k})">${s.bubble(c)}</g>
      </g>`);
    }
  }

  // connection dots: junctions, and pins where 3+ things meet
  out.push('<g class="dots">');
  for (const c of circuit.components) {
    for (const pin of Object.keys(shapeOf(c.type).pins)) {
      const term = `${c.id}.${pin}`;
      const n = (ix.wiresAt.get(term) || 0) + (c.type === 'junction' ? 0 : 1);
      const [x, y] = pinPos(c, pin);
      if (c.port) {
        out.push(`<g class="port ${sel.kind === 'comp' && sel.id === c.id ? 'sel' : ''}"><circle cx="${x}" cy="${y}" r="7"/>
          <text class="port-name" x="${c.id === 'B' ? x + 13 : x - 13}" y="${y + 5}" text-anchor="${c.id === 'B' ? 'start' : 'end'}">${esc(c.id)}</text></g>`);
      } else if (c.type === 'junction') {
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
    out.push(`<g class="probe ${which} ${p.dragging ? 'dragging' : ''} ${p.loose ? 'loose' : ''} ${p.inside ? 'inside' : ''}" data-hit="probe" data-probe="${which}"
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

/** A Req block's value label: its Req once the student has checked it, else "Req = ?". */
function blockLabel(info) {
  if (!info || !info.solved) return { text: 'Req = ?', cls: 'q' };
  if (info.R === Infinity) return { text: 'open', cls: 'r' };
  return { text: short(info.R, 'Ω'), cls: 'r' };
}

const VALUED = new Set(['resistor', 'reqblock']);

/** Which way conventional current flows through a two-pin part on screen. */
function arrowFor(c, i) {
  const pins = Object.keys(shapeOf(c.type).pins);
  const a = pinPos(c, pins[0]), b = pinPos(c, pins[1]);
  let dx = b[0] - a[0], dy = b[1] - a[1];
  if (i < 0) { dx = -dx; dy = -dy; }
  return Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? '→' : '←') : (dy > 0 ? '↓' : '↑');
}

/** Labels for resistors and Req blocks: the name and resistance together on one line, then the
    current and the voltage DROP across the part, spaced apart on their own line(s).
    vals: undefined (no live values), 'locked' (shown as ?), or { i, v } from the solve. */
/** Is another resistor or block right under this horizontal one (parallel rows)? Then its current
    and drop go on one short line instead of two, to leave room for that part's name. */
function partBelow(c, comps) {
  if (!VALUED.has(c.type) || (c.layout.rot || 0) % 2) return false;
  return comps.some((o) => o !== c && VALUED.has(o.type) && !((o.layout.rot || 0) % 2)
    && Math.abs(o.layout.x - c.layout.x) < 100 && o.layout.y > c.layout.y && o.layout.y - c.layout.y < 110);
}

function valuedLabels(c, val, vals, oneLine) {
  const { x, y, rot = 0 } = c.layout;
  const vertical = rot % 2 === 1;
  const head = `<tspan class="pname">${esc(c.id)}</tspan><tspan class="pval ${val.cls}" dx="9">${esc(val.text)}</tspan>`;
  let I = '', V = '';
  if (vals === 'locked') {
    I = '<tspan class="q">I ?</tspan>';
    V = '<tspan class="q">ΔV ?</tspan>';
  } else if (vals) {
    I = Math.abs(vals.i) < 1e-12 ? '<tspan class="iv-i">0 A</tspan>'
      : `<tspan class="iv-i">${arrowFor(c, vals.i)} ${esc(short(Math.abs(vals.i), 'A'))}</tspan>`;
    V = `<tspan class="tag">ΔV</tspan><tspan class="iv-v" dx="5">${esc(short(Math.abs(vals.v), 'V'))}</tspan>`;
  }
  const box = c.type === 'reqblock' ? 5 : 0;    // a block's dashed outline needs a little more room
  // Horizontal: current over drop, centred under the part, so the labels stay about as wide as the
  // part itself and don't run into neighbours in a series row.
  if (!vertical && oneLine) {
    return `<text class="plabel" x="${x}" y="${y - 22 - box}" text-anchor="middle">${head}</text>${I ? `
      <text class="pvals" x="${x - 7}" y="${y + 27 + box}" text-anchor="end">${I}</text>
      <text class="pvals" x="${x + 7}" y="${y + 27 + box}" text-anchor="start">${V}</text>` : ''}`;
  }
  if (!vertical) {
    return `<text class="plabel" x="${x}" y="${y - 22 - box}" text-anchor="middle">${head}</text>${I ? `
      <text class="pvals" x="${x}" y="${y + 26 + box}" text-anchor="middle">${I}</text>
      <text class="pvals" x="${x}" y="${y + 41 + box}" text-anchor="middle">${V}</text>` : ''}`;
  }
  const lx = x + 24 + box;
  if (!I) return `<text class="plabel" x="${lx}" y="${y + 5}">${head}</text>`;
  return `<text class="plabel" x="${lx}" y="${y - 15}">${head}</text>
    <text class="pvals" x="${lx}" y="${y + 5}">${I}</text>
    <text class="pvals" x="${lx}" y="${y + 23}">${V}</text>`;
}

function partSVG(c, { sel, hl, info, vals, oneLine }) {
  const s = shapeOf(c.type);
  const { x, y, rot = 0 } = c.layout;
  const [hx, hy, hw, hh] = s.hit;
  const lab = labelSpots(c);
  const showLabels = c.type !== 'ground' && c.type !== 'junction';
  const cls = ['part', `t-${c.type}`, sel ? 'sel' : '', hl ? 'hl' : '', c.style ? `s-${c.style}` : ''].join(' ');
  const val = c.type === 'reqblock' ? blockLabel(info) : { text: valueLabel(c), cls: c.type === 'resistor' ? 'r' : '' };
  return `<g class="${cls}" data-hit="comp" data-id="${esc(c.id)}">
    <g transform="translate(${x} ${y}) rotate(${rot * 90})">
      <rect class="part-hit" x="${hx - 4}" y="${hy - 4}" width="${hw + 8}" height="${hh + 8}" rx="6"/>
      ${s.draw(c)}
    </g>
    ${VALUED.has(c.type) ? valuedLabels(c, val, vals, oneLine) : showLabels ? `<text class="pname" x="${lab.name[0]}" y="${lab.name[1]}" text-anchor="${lab.name[2]}">${esc(c.id)}</text>
    <text class="pval ${val.cls}" x="${lab.value[0]}" y="${lab.value[1]}" text-anchor="${lab.value[2]}">${esc(val.text)}</text>` : ''}
  </g>`;
}

/* An expanded Req block's bubble: where it sits and how much its inside is scaled down. */
export const BUBBLE_SCALE = 0.55;
export function bubbleGeom(c) {
  const ib = bounds(c.inner || { components: [], wires: [] }) || { x0: -40, y0: 40, x1: 400, y1: 200 };
  const k = BUBBLE_SCALE, W = (ib.x1 - ib.x0) * k, H = (ib.y1 - ib.y0) * k;
  const { x, y, rot = 0 } = c.layout;
  if (rot % 2 === 1) {
    const left = x - 50 - W, top = y - H / 2;
    return { left, top, W, H, k, ib, lines: [[x - 17, y - 33, left + W, top + 8], [x - 17, y + 33, left + W, top + H - 8]] };
  }
  const left = x - W / 2, top = y - 48 - H;
  return { left, top, W, H, k, ib, lines: [[x - 33, y - 17, left + 8, top + H], [x + 33, y - 17, left + W - 8, top + H]] };
}

function overlaySVG(circuit, ix, result) {
  const out = ['<g class="overlay">'];
  // Current through the other two-pin parts (supplies, switches). Resistors and blocks carry their
  // own current and voltage-drop labels (see valuedLabels), so nothing here sits on a resistor's pin.
  for (const c of circuit.components) {
    const r = result.components[c.id];
    const pins = Object.keys(shapeOf(c.type).pins);
    if (!r || pins.length !== 2 || VALUED.has(c.type) || Math.abs(r.i) < 1e-12) continue;
    const lab = labelSpots(c);
    const [x, y, anchor] = lab.value;
    out.push(`<text class="amp" x="${x}" y="${y + 16}" text-anchor="${anchor}">${arrowFor(c, r.i)} ${esc(short(Math.abs(r.i), 'A'))}</text>`);
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
    if (VALUED.has(c.type)) {   // room for the name, value, current and drop labels
      if ((c.layout.rot || 0) % 2 === 1) xs.push(c.layout.x + 140);
      else { xs.push(c.layout.x - 60, c.layout.x + 60); ys.push(c.layout.y + 50); }
    }
    if (c.type === 'reqblock' && c.expanded) {
      const g = bubbleGeom(c);
      xs.push(g.left, g.left + g.W); ys.push(g.top, g.top + g.H);
    }
  }
  if (!xs.length) return null;
  return { x0: Math.min(...xs) - 40, y0: Math.min(...ys) - 50, x1: Math.max(...xs) + 60, y1: Math.max(...ys) + 50 };
}
