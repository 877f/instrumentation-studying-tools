'use strict';
/* Instruments: the analog meter, the formula ring, the progress scale, lamps and color bands.
   Each builder returns markup. After a view renders, animateInstruments() swings the needles
   with a damped-spring model of a moving-coil meter: overshoot, settle, bounce off the end stops.
   Loaded before formula.js and app.js; esc() comes from app.js and is only used at render time. */

const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)');
const needleMemory = {};    // meter key -> value last shown, so a needle moves on from where it was
const needleState = new WeakMap();
const activeNeedles = new Set();
const NEEDLE = { w: 10, z: 0.45, stop: 2.5, bounce: 0.3 };   // rad/s, damping ratio, degrees past the scale, energy kept
const RESISTOR = ['black', 'brown', 'red', 'orange', 'yellow', 'green', 'blue', 'violet', 'gray', 'white'];
let needleRaf = 0;
let needleLast = 0;

/* ---------------------------------------------------------------- geometry */

function n2(n) { return String(Math.round(n * 100) / 100); }
function polar(cx, cy, r, deg) {
  const a = (deg * Math.PI) / 180;
  return [cx + r * Math.sin(a), cy - r * Math.cos(a)];
}
function arcPath(cx, cy, r, a0, a1) {
  const [x0, y0] = polar(cx, cy, r, a0), [x1, y1] = polar(cx, cy, r, a1);
  return `M${n2(x0)} ${n2(y0)}A${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${n2(x1)} ${n2(y1)}`;
}
function sectorPath(cx, cy, r0, r1, a0, a1) {
  const [x0, y0] = polar(cx, cy, r1, a0), [x1, y1] = polar(cx, cy, r1, a1);
  if (r0 < 0.5) return `M${cx} ${cy}L${n2(x0)} ${n2(y0)}A${r1} ${r1} 0 0 1 ${n2(x1)} ${n2(y1)}Z`;
  const [x2, y2] = polar(cx, cy, r0, a1), [x3, y3] = polar(cx, cy, r0, a0);
  return `M${n2(x0)} ${n2(y0)}A${r1} ${r1} 0 0 1 ${n2(x1)} ${n2(y1)}L${n2(x2)} ${n2(y2)}A${r0} ${r0} 0 0 0 ${n2(x3)} ${n2(y3)}Z`;
}
function tickLine(cx, cy, r0, r1, deg, cls) {
  const [x0, y0] = polar(cx, cy, r0, deg), [x1, y1] = polar(cx, cy, r1, deg);
  return `<line class="${cls}" x1="${n2(x0)}" y1="${n2(y0)}" x2="${n2(x1)}" y2="${n2(y1)}"/>`;
}
function niceStep(max) {
  for (const s of [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500]) if (max / s <= 7) return s;
  return Math.ceil(max / 6);
}
function clampValue(value, max) { return Math.max(0, Math.min(Number(value) || 0, max)); }

function needleGroup({ key, value, max, cx, cy, a, inner }) {
  const angle = (v) => -a + (2 * a * v) / max;
  const from = REDUCED_MOTION.matches ? angle(value) : angle(clampValue(needleMemory[key] ?? 0, max));
  return `<g class="m-needle" data-needle="${esc(key)}" data-value="${value}" data-max="${max}" data-cx="${cx}"
    data-cy="${cy}" data-a="${a}" transform="rotate(${n2(from)} ${cx} ${cy})">${inner}</g>`;
}

/* ------------------------------------------------------------- panel meter */

/* A moving-coil panel meter. Outer scale counts (0 to max), inner red scale reads percent,
   both from the same deflection, like a multi-range meter face. */
function meterSVG({ key, value, max, legend, tag, readout, label }) {
  const cx = 200, cy = 230, R = 168, A = 46;
  max = Math.max(1, Math.round(max));
  value = clampValue(value, max);
  const ang = (v, m) => -A + (2 * A * v) / m;
  const step = niceStep(max);
  const minor = step % 5 === 0 ? step / 5 : step / 2;     // 0-5 gets half steps, 0-54 gets twos
  let s = '<rect class="m-face" width="400" height="198"/>';
  s += `<path class="m-arc" d="${arcPath(cx, cy, R, -A, A)}"/>`;
  for (let v = 0; v <= max; v += minor) s += tickLine(cx, cy, R, R + (v % step ? 7 : 13), ang(v, max), 'm-tick');
  if (max % minor) s += tickLine(cx, cy, R, R + 13, A, 'm-tick');
  const labels = [];
  for (let v = 0; v < max; v += step) if (max - v > max * 0.1) labels.push(v);
  labels.push(max);
  labels.forEach((v) => {
    const [x, y] = polar(cx, cy, R + 26, ang(v, max));
    s += `<text class="m-num" x="${n2(x)}" y="${n2(y)}">${v}</text>`;
  });
  s += `<path class="m-mirror" d="${arcPath(cx, cy, R - 7, -A + 0.6, A - 0.6)}"/>`;
  const Ri = R - 19;
  s += `<path class="m-arc m-alt" d="${arcPath(cx, cy, Ri, -A, A)}"/>`;
  for (let p = 0; p <= 100; p += 10) s += tickLine(cx, cy, Ri, Ri - (p % 50 ? 4.5 : 8), ang(p, 100), 'm-tick m-alt');
  for (let p = 0; p <= 100; p += 25) {
    const [x, y] = polar(cx, cy, Ri - 17, ang(p, 100));
    s += `<text class="m-num m-sm m-alt" x="${n2(x)}" y="${n2(y)}">${p}${p === 100 ? '%' : ''}</text>`;
  }
  s += `<text class="m-legend" x="${cx}" y="168">${esc(legend)}</text>`;
  s += needleGroup({ key, value, max, cx, cy, a: A, inner:
    `<path class="m-ptr-shadow" d="M${cx + 1.6} ${cy + 3}L${cx + 5} ${cy + 3}L${cx + 3.5} ${cy - R - 2}L${cx + 2.7} ${cy - R - 2}Z"/>
     <path class="m-ptr" d="M${cx - 2.4} ${cy}L${cx + 2.4} ${cy}L${cx + 0.45} ${cy - R - 7}L${cx - 0.45} ${cy - R - 7}Z"/>` });
  s += `<rect class="m-shade" width="400" height="16"/><path class="m-glass" d="M0 0H232L96 198H0Z"/>
    <path class="m-cover" d="M0 198H400V260H0Z"/><path class="m-cover-edge" d="M0 198.75H400"/>
    <circle class="m-screw" cx="${cx}" cy="${cy}" r="10"/><path class="m-slot" d="M${cx - 6.5} ${cy - 3}L${cx + 6.5} ${cy + 3}"/>
    <text class="m-plate" x="24" y="${cy}">${esc(tag)}</text>
    <text class="m-plate m-end" x="376" y="${cy}">${esc(readout)}</text>`;
  return `<svg class="meter" viewBox="0 0 400 260" role="img" aria-label="${esc(label)}">${s}</svg>`;
}

/* A small meter for tight spots (mobile chapter header, loading screen). No numerals. */
function miniMeterSVG({ key, value, max, label, idle }) {
  const cx = 60, cy = 70, R = 52, A = 48;
  max = Math.max(1, max);
  value = clampValue(value, max);
  let s = '<rect class="m-face" width="120" height="78" rx="6"/>';
  s += `<path class="m-arc" d="${arcPath(cx, cy, R, -A, A)}"/>`;
  for (let i = 0; i <= 10; i++) s += tickLine(cx, cy, R, R + (i % 5 ? 4 : 8), -A + (2 * A * i) / 10, 'm-tick');
  const ptr = `<path class="m-ptr" d="M${cx - 1.6} ${cy}L${cx + 1.6} ${cy}L${cx + 0.35} ${cy - R - 5}L${cx - 0.35} ${cy - R - 5}Z"/>
    <circle class="m-pivot" cx="${cx}" cy="${cy}" r="5"/>`;
  s += idle ? `<g class="m-needle idle">${ptr}</g>` : needleGroup({ key, value, max, cx, cy, a: A, inner: ptr });
  return `<svg class="meter mini" viewBox="0 0 120 78" role="img" aria-label="${esc(label)}">${s}</svg>`;
}

/* ------------------------------------------------------------ formula ring */

/* The formula wheel as a ring of lamps: one segment per formula, grouped by quadrant.
   quadrants: [{ var, slots }], lit: { var: count right }, legend: lines printed top left */
function ringSVG({ quadrants, lit, tag, readout, label, legend }) {
  const cx = 200, cy = 99, R1 = 88, R0 = 61, H = 51;
  let s = '<rect class="m-face" width="400" height="198"/>';
  let k = 0;
  const span = 360 / quadrants.length;
  quadrants.forEach((q, qi) => {
    const base = span * qi;
    for (let j = 0; j < q.slots; j++) {
      const a0 = base + (span * j) / q.slots + 1.5, a1 = base + (span * (j + 1)) / q.slots - 1.5;
      s += `<path class="r-seg${j < (lit[q.var] || 0) ? ' on' : ''}" style="--i:${k++}" d="${sectorPath(cx, cy, R0, R1, a0, a1)}"/>`;
    }
    s += `<path class="r-hub${qi % 2 ? ' alt' : ''}" d="${sectorPath(cx, cy, 0, H, base, base + span)}"/>`;
    const [lx, ly] = polar(cx, cy, H * 0.56, base + span / 2);
    s += `<text class="r-var" x="${n2(lx)}" y="${n2(ly)}">${esc(q.var)}</text>`;
  });
  legend.forEach((line, i) => { s += `<text class="m-legend r-legend" x="24" y="${34 + i * 19}">${esc(line)}</text>`; });
  s += `<rect class="m-shade" width="400" height="16"/><path class="m-glass" d="M0 0H232L96 198H0Z"/>
    <path class="m-cover" d="M0 198H400V260H0Z"/><path class="m-cover-edge" d="M0 198.75H400"/>
    <text class="m-plate" x="24" y="230">${esc(tag)}</text>
    <text class="m-plate m-end" x="376" y="230">${esc(readout)}</text>`;
  return `<svg class="meter ring" viewBox="0 0 400 260" role="img" aria-label="${esc(label)}">${s}</svg>`;
}

/* ------------------------------------------------------- scale, lamps, bands */

/* Session progress as a graduated scale: one tick per question, colored by result.
   marks: ['ok' | 'no' | 'rev', ...] for answered questions, in order. current: mark the next one. */
function scaleHTML(marks, total, label, current = true) {
  const ticks = [];
  for (let i = 0; i < total; i++) {
    const cls = i < marks.length ? marks[i] : i === marks.length && current ? 'cur' : '';
    ticks.push(`<i class="t ${cls}${(i + 1) % 5 === 0 ? ' maj' : ''}"></i>`);
  }
  return `<div class="scale" role="progressbar" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="${total}"
    aria-valuenow="${marks.length}" style="--n:${Math.max(total, 1)}">${ticks.join('')}</div>`;
}

function lamp(kind, extra = '') { return `<span class="lamp ${kind} ${extra}" aria-hidden="true"></span>`; }

/* Resistor color code: part 1 is brown, 2 red, 3 orange, 4 yellow, 5 green... */
function band(n) { return `<i class="band ${RESISTOR[Math.abs(n) % 10]}" aria-hidden="true"></i>`; }

/* ------------------------------------------------------------------ motion */

function setNeedle(n, angle) {
  n.a = angle;
  n.g.setAttribute('transform', `rotate(${n2(angle)} ${n.cx} ${n.cy})`);
}

function runNeedles() {
  if (!needleRaf && activeNeedles.size) {
    needleLast = performance.now();
    needleRaf = requestAnimationFrame(tickNeedles);
  }
}

function tickNeedles(now) {
  const dt = Math.min(0.05, Math.max(0, (now - needleLast) / 1000));
  needleLast = now;
  for (const n of activeNeedles) {
    if (!n.g.isConnected) { activeNeedles.delete(n); continue; }
    if (now < n.start) continue;
    if (n.hold && now >= n.hold) { n.hold = 0; n.target = n.final; n.w = NEEDLE.w; }
    for (let t = 0; t < dt; t += 0.004) {
      const h = Math.min(0.004, dt - t);
      n.v += (-n.w * n.w * (n.a - n.target) - 2 * NEEDLE.z * n.w * n.v) * h;
      n.a += n.v * h;
      if (n.a > n.hi) { n.a = n.hi; n.v = -Math.abs(n.v) * NEEDLE.bounce; }
      else if (n.a < n.lo) { n.a = n.lo; n.v = Math.abs(n.v) * NEEDLE.bounce; }
    }
    if (!n.hold && Math.abs(n.a - n.target) < 0.03 && Math.abs(n.v) < 0.3) {
      n.v = 0;
      activeNeedles.delete(n);
      setNeedle(n, n.target);
    } else {
      setNeedle(n, n.a);
    }
  }
  needleRaf = activeNeedles.size ? requestAnimationFrame(tickNeedles) : 0;
}

/* Swing every needle in `root` to its reading. powerOn: first sweep to full scale and back,
   staggered, the way bench instruments self-test when switched on. */
function animateInstruments(root, { powerOn = false } = {}) {
  const sweep = powerOn && !REDUCED_MOTION.matches;
  const t0 = performance.now();
  root.querySelectorAll('[data-needle]').forEach((g, i) => {
    const A = +g.dataset.a, max = +g.dataset.max, value = +g.dataset.value;
    const target = -A + (2 * A * value) / max;
    needleMemory[g.dataset.needle] = value;
    const m = /rotate\((-?[\d.]+)/.exec(g.getAttribute('transform') || '');
    const n = { g, cx: +g.dataset.cx, cy: +g.dataset.cy, a: m ? +m[1] : target, v: 0, w: NEEDLE.w,
                lo: -A - NEEDLE.stop, hi: A + NEEDLE.stop, target, final: target, start: 0, hold: 0 };
    needleState.set(g, n);
    if (REDUCED_MOTION.matches) return setNeedle(n, target);
    if (sweep) {
      n.start = t0 + 180 + i * 170;
      n.hold = n.start + 620;
      n.target = A + 10;          // past full scale: the needle pegs against the stop
      n.w = 8;
    }
    activeNeedles.add(n);
  });
  if (sweep) root.querySelectorAll('.ring').forEach((r) => r.classList.add('power'));
  runNeedles();
}

/* A small flick of the needle, like touching the probes. Used on hover. */
function kickNeedle(g, dv = 55) {
  const n = needleState.get(g);
  if (!n || REDUCED_MOTION.matches) return;
  n.v += dv;
  activeNeedles.add(n);
  runNeedles();
}
