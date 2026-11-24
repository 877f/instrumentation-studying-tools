/* Schematic geometry: where each part's pins sit, how it's drawn, and wire routing.
   Pure functions returning numbers or SVG strings; no DOM access. Units are board pixels. */

export const GRID = 20;

/* Each shape: pins (local offsets, rotation 0), axis ('x' if the pins run left-right at rotation 0),
   hit box [x, y, w, h], and draw(comp) returning SVG in local coordinates. */
export const SHAPES = {
  resistor: {
    pins: { a: [-40, 0], b: [40, 0] }, axis: 'x', hit: [-30, -14, 60, 28],
    draw: () => '<path class="ink" d="M-40 0H-24l4-8 8 16 8-16 8 16 8-16 8 16 4-8H40"/>',
  },
  reqblock: {
    pins: { a: [-40, 0], b: [40, 0] }, axis: 'x', hit: [-34, -18, 68, 36],
    draw: () => '<rect class="req-box" x="-33" y="-17" width="66" height="34" rx="6"/>'
      + '<path class="ink" d="M-40 0H-24l4-8 8 16 8-16 8 16 8-16 8 16 4-8H40"/>',
  },
  vsource: {
    pins: { p: [0, -40], n: [0, 40] }, axis: 'y', hit: [-24, -24, 48, 48],
    draw: (c) => (c.style === 'battery'
      ? '<path class="ink" d="M0 -40V-6M0 6V40"/><path class="ink plate" d="M-18 -6H18"/><path class="ink plate thick" d="M-9 6H9"/>'
        + '<path class="ink thin" d="M12 -20h8M16 -24v8"/>'
      : '<path class="ink" d="M0 -40V-20M0 20V40"/><circle class="ink body" r="20"/>'
        + '<path class="ink thin" d="M0 -14v10M-5 -9h10M-5 9h10"/>'),
  },
  isource: {
    pins: { p: [0, -40], n: [0, 40] }, axis: 'y', hit: [-24, -24, 48, 48],
    draw: () => '<path class="ink" d="M0 -40V-20M0 20V40"/><circle class="ink body" r="20"/>'
      + '<path class="ink thin" d="M0 12V-10M-6 -4L0 -12L6 -4"/>',
  },
  switch: {
    pins: { a: [-40, 0], b: [40, 0] }, axis: 'x', hit: [-28, -22, 56, 32],
    draw: (c) => '<path class="ink" d="M-40 0H-16M16 0H40"/><circle class="ink body" cx="-16" r="3"/><circle class="ink body" cx="16" r="3"/>'
      + (c.params.closed ? '<path class="ink" d="M-16 0L16 -2"/>' : '<path class="ink" d="M-16 0L12 -17"/>'),
  },
  ground: {
    pins: { g: [0, -20] }, axis: 'y', hit: [-16, -10, 32, 24],
    draw: () => '<path class="ink" d="M0 -20V0M-14 0H14M-9 5H9M-4 10H4"/>',
  },
  junction: {
    pins: { j: [0, 0] }, axis: 'x', hit: [-7, -7, 14, 14],
    draw: () => '',
  },
};

export const shapeOf = (type) => SHAPES[type] || SHAPES.resistor;

/** Rotate a local offset by rot quarter-turns clockwise (screen coordinates, y down). */
export function rotate([x, y], rot = 0) {
  switch (((rot % 4) + 4) % 4) {
    case 1: return [-y, x];
    case 2: return [-x, -y];
    case 3: return [y, -x];
    default: return [x, y];
  }
}

export function pinPos(comp, pin) {
  const [dx, dy] = rotate(shapeOf(comp.type).pins[pin], comp.layout.rot);
  return [comp.layout.x + dx, comp.layout.y + dy];
}

/** Which way a pin points out of its part: 'h' or 'v'. Used to pick a wire's first bend. */
export function pinDir(comp, pin) {
  const [dx, dy] = rotate(shapeOf(comp.type).pins[pin], comp.layout.rot);
  if (dx === 0 && dy === 0) return null;
  return Math.abs(dx) >= Math.abs(dy) ? 'h' : 'v';
}

export const snap = (v) => Math.round(v / GRID) * GRID;

/* ------------------------------------------------------------- labels */

/** Where the part's name and value go, kept upright whatever the rotation. */
export function labelSpots(comp) {
  const s = shapeOf(comp.type);
  const vertical = (s.axis === 'y') !== (((comp.layout.rot || 0) % 2) === 1);
  const { x, y } = comp.layout;
  if (vertical) return { name: [x + 28, y - 4, 'start'], value: [x + 28, y + 13, 'start'], vertical };
  return { name: [x, y - 24, 'middle'], value: [x, y + 32, 'middle'], vertical };
}

/* --------------------------------------------------------------- wires */

/** A wire's L-shaped route between two points. bend 'hv' goes across first, 'vh' goes up/down first. */
export function wirePoints(A, B, bend = 'hv') {
  if (A[0] === B[0] || A[1] === B[1]) return [A, B];
  return bend === 'vh' ? [A, [A[0], B[1]], B] : [A, [B[0], A[1]], B];
}

export function polyLength(pts) {
  let L = 0;
  for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  return L;
}

/** The point a fraction t (0 to 1) of the way along a polyline. */
export function pointAt(pts, t) {
  const L = polyLength(pts);
  let want = Math.max(0, Math.min(1, t)) * L;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
    const seg = Math.hypot(x1 - x0, y1 - y0);
    if (want <= seg || i === pts.length - 1) {
      const f = seg ? Math.min(1, want / seg) : 0;
      return [x0 + (x1 - x0) * f, y0 + (y1 - y0) * f];
    }
    want -= seg;
  }
  return pts[pts.length - 1];
}

/** Nearest point on a polyline to p: { t, dist, point }. */
export function nearestOn(pts, p) {
  const L = polyLength(pts) || 1;
  let best = { t: 0, dist: Infinity, point: pts[0] }, run = 0;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
    const dx = x1 - x0, dy = y1 - y0, seg2 = dx * dx + dy * dy, seg = Math.sqrt(seg2);
    const f = seg2 ? Math.max(0, Math.min(1, ((p[0] - x0) * dx + (p[1] - y0) * dy) / seg2)) : 0;
    const q = [x0 + dx * f, y0 + dy * f];
    const d = Math.hypot(p[0] - q[0], p[1] - q[1]);
    if (d < best.dist) best = { t: (run + f * seg) / L, dist: d, point: q };
    run += seg;
  }
  return best;
}

/** Split a polyline at fractions t0 < t1 (for drawing the gap in a cut wire). */
export function splitPoly(pts, t0, t1) {
  const L = polyLength(pts);
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const take = (a, b) => {
    const out = [pointAt(pts, a / L)];
    for (let i = 1; i < pts.length - 1; i++) if (cum[i] > a && cum[i] < b) out.push(pts[i]);
    out.push(pointAt(pts, b / L));
    return out;
  };
  return [take(0, t0 * L), take(t1 * L, L)];
}

export const pathD = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${r1(p[0])} ${r1(p[1])}`).join('');
const r1 = (n) => Math.round(n * 10) / 10;

/* ------------------------------------------------------- color bands */

const BAND = ['#111', '#7b4a1e', '#d0312d', '#f08a24', '#f5d000', '#2e9a48', '#2a63c9', '#8a46b8', '#8a8a8a', '#f4f4f4'];
const BAND_NAME = ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'gray', 'white'];
const GOLD = '#c9a23a', SILVER = '#b9bec4';

/** Color bands for a resistance: 4-band (2 digits) when it fits, else 5-band. */
export function resistorBands(R) {
  if (!(R > 0)) return null;
  for (const digits of [2, 3]) {
    const exp = Math.floor(Math.log10(R)) - (digits - 1);
    const sig = Math.round(R / 10 ** exp);
    if (Math.abs(sig * 10 ** exp - R) / R > 1e-9 && digits === 2) continue;
    let mult = exp, s = sig;
    if (String(s).length > digits) { s = Math.round(s / 10); mult += 1; }
    if (mult < -2 || mult > 9) return null;
    const ds = String(s).padStart(digits, '0').split('').map(Number);
    const multColor = mult === -1 ? GOLD : mult === -2 ? SILVER : BAND[mult];
    const multName = mult === -1 ? 'gold' : mult === -2 ? 'silver' : BAND_NAME[mult];
    return {
      colors: [...ds.map((d) => BAND[d]), multColor, GOLD],
      names: [...ds.map((d) => BAND_NAME[d]), multName, digits === 2 ? 'gold (5%)' : 'gold (5%)'],
    };
  }
  return null;
}

/* ------------------------------------------------------- value series */

export const E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2];
export const E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1];
