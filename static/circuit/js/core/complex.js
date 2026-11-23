/* A tiny immutable complex number. DC solves use im = 0 throughout; AC stamps
   (capacitors, inductors) will put admittances like jωC on the imaginary axis. */

export class Complex {
  constructor(re = 0, im = 0) {
    this.re = re;
    this.im = im;
  }

  static from(x) {
    if (x instanceof Complex) return x;
    if (typeof x === 'number') return new Complex(x, 0);
    if (x && typeof x.re === 'number') return new Complex(x.re, x.im || 0);
    throw new TypeError(`not a number: ${x}`);
  }

  add(z) { z = Complex.from(z); return new Complex(this.re + z.re, this.im + z.im); }
  sub(z) { z = Complex.from(z); return new Complex(this.re - z.re, this.im - z.im); }
  mul(z) {
    z = Complex.from(z);
    return new Complex(this.re * z.re - this.im * z.im, this.re * z.im + this.im * z.re);
  }
  div(z) {
    z = Complex.from(z);
    const d = z.re * z.re + z.im * z.im;
    return new Complex((this.re * z.re + this.im * z.im) / d, (this.im * z.re - this.re * z.im) / d);
  }
  neg() { return new Complex(-this.re, -this.im); }
  conj() { return new Complex(this.re, -this.im); }
  scale(k) { return new Complex(this.re * k, this.im * k); }
  abs() { return Math.hypot(this.re, this.im); }
  arg() { return Math.atan2(this.im, this.re); }
  isFinite() { return Number.isFinite(this.re) && Number.isFinite(this.im); }
  toString() { return this.im ? `${this.re}${this.im < 0 ? '-' : '+'}${Math.abs(this.im)}j` : String(this.re); }
}

export const ZERO = new Complex(0, 0);
export const ONE = new Complex(1, 0);
export const c = (re, im = 0) => new Complex(re, im);
