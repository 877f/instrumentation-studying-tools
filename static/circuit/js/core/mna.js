/* The MNA system and the helpers component stamps use.

   Unknowns: one voltage per non-reference node, then one current per "branch" a component
   asks for (voltage sources do). Index -1 means the reference node; every helper skips it,
   so stamps never have to special-case ground.

   Row convention for node rows (KCL): sum of currents LEAVING the node through elements
   = sum of currents INJECTED into it by sources (the right-hand side). */

import { Complex } from './complex.js';

export class System {
  constructor(size) {
    this.size = size;
    this.re = new Float64Array(size * size);
    this.im = new Float64Array(size * size);
    this.bre = new Float64Array(size);
    this.bim = new Float64Array(size);
  }
  /** A[i][j] += z */
  add(i, j, z) {
    if (i < 0 || j < 0) return;
    const k = i * this.size + j;
    if (typeof z === 'number') this.re[k] += z;
    else { this.re[k] += z.re; this.im[k] += z.im; }
  }
  /** rhs[i] += z */
  addRhs(i, z) {
    if (i < 0) return;
    if (typeof z === 'number') this.bre[i] += z;
    else { this.bre[i] += z.re; this.bim[i] += z.im; }
  }
}

/** The right-hand side as its own object, so stamps can be written as stamp(A, rhs, ctx). */
export function rhsOf(sys) {
  return { add: (i, z) => sys.addRhs(i, z) };
}

/* ------------------------------------------------------------ stamp helpers */

const neg = (z) => (typeof z === 'number' ? -z : z.neg());

/** Admittance y between nodes a and b (a resistor is y = 1/R). */
export function stampAdmittance(A, a, b, y) {
  A.add(a, a, y); A.add(b, b, y);
  A.add(a, b, neg(y)); A.add(b, a, neg(y));
}

/** A current source pushing current i out into node `to`, drawing it from node `from`. */
export function stampCurrent(rhs, from, to, i) {
  rhs.add(to, i);
  rhs.add(from, neg(i));
}

/** A voltage source with series impedance z on branch k: V(p) − V(n) + z·I = v,
    where I is the branch current flowing out of the + terminal into the circuit. */
export function stampVoltage(A, rhs, p, n, k, v, z = 0) {
  A.add(p, k, -1); A.add(n, k, 1);
  A.add(k, p, 1); A.add(k, n, -1);
  if (z !== 0) A.add(k, k, z);
  rhs.add(k, v);
}

/* ----------------------------------------------------- Gaussian elimination */

const PIVOT_TOL = 1e-13;

/** Solve A·x = b in place with partial pivoting.
    Returns { x: Complex[] } or { singular: col } naming the unknown that couldn't be pinned down. */
export function gaussSolve(sys) {
  const n = sys.size;
  const re = Float64Array.from(sys.re), im = Float64Array.from(sys.im);
  const bre = Float64Array.from(sys.bre), bim = Float64Array.from(sys.bim);
  // Column scale, so a column of tiny conductances (a 1 TΩ path) isn't mistaken for zero.
  const colMax = new Float64Array(n);
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
    const a = Math.hypot(re[i * n + j], im[i * n + j]);
    if (a > colMax[j]) colMax[j] = a;
  }
  const order = Array.from({ length: n }, (_, i) => i);   // row swaps, to report the original row

  for (let col = 0; col < n; col++) {
    let best = col, bestAbs = -1;
    for (let r = col; r < n; r++) {
      const a = Math.hypot(re[r * n + col], im[r * n + col]);
      if (a > bestAbs) { bestAbs = a; best = r; }
    }
    if (!(bestAbs > PIVOT_TOL * colMax[col]) || colMax[col] === 0) return { singular: col };
    if (best !== col) {
      for (let j = 0; j < n; j++) {
        const a = col * n + j, b = best * n + j;
        [re[a], re[b]] = [re[b], re[a]];
        [im[a], im[b]] = [im[b], im[a]];
      }
      [bre[col], bre[best]] = [bre[best], bre[col]];
      [bim[col], bim[best]] = [bim[best], bim[col]];
      [order[col], order[best]] = [order[best], order[col]];
    }
    const pr = re[col * n + col], pi = im[col * n + col];
    const pd = pr * pr + pi * pi;
    for (let r = col + 1; r < n; r++) {
      const ar = re[r * n + col], ai = im[r * n + col];
      if (ar === 0 && ai === 0) continue;
      // f = a / pivot
      const fr = (ar * pr + ai * pi) / pd, fi = (ai * pr - ar * pi) / pd;
      for (let j = col; j < n; j++) {
        const cr = re[col * n + j], ci = im[col * n + j];
        if (cr === 0 && ci === 0) continue;
        re[r * n + j] -= fr * cr - fi * ci;
        im[r * n + j] -= fr * ci + fi * cr;
      }
      const cr = bre[col], ci = bim[col];
      bre[r] -= fr * cr - fi * ci;
      bim[r] -= fr * ci + fi * cr;
    }
  }

  const xr = new Float64Array(n), xi = new Float64Array(n);
  for (let r = n - 1; r >= 0; r--) {
    let sr = bre[r], si = bim[r];
    for (let j = r + 1; j < n; j++) {
      const ar = re[r * n + j], ai = im[r * n + j];
      sr -= ar * xr[j] - ai * xi[j];
      si -= ar * xi[j] + ai * xr[j];
    }
    const pr = re[r * n + r], pi = im[r * n + r];
    const pd = pr * pr + pi * pi;
    xr[r] = (sr * pr + si * pi) / pd;
    xi[r] = (si * pr - sr * pi) / pd;
  }

  // Relative residual: a cheap ill-conditioning alarm.
  let res = 0, scale = 0;
  for (let i = 0; i < n; i++) {
    let sr = -sys.bre[i], si = -sys.bim[i];
    for (let j = 0; j < n; j++) {
      const ar = sys.re[i * n + j], ai = sys.im[i * n + j];
      sr += ar * xr[j] - ai * xi[j];
      si += ar * xi[j] + ai * xr[j];
      scale = Math.max(scale, Math.hypot(ar * xr[j] - ai * xi[j], ar * xi[j] + ai * xr[j]));
    }
    res = Math.max(res, Math.hypot(sr, si));
    scale = Math.max(scale, Math.hypot(sys.bre[i], sys.bim[i]));
  }
  const x = Array.from({ length: n }, (_, i) => new Complex(xr[i], xi[i]));
  return { x, residual: scale ? res / scale : res };
}
