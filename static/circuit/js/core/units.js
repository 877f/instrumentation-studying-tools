/* Engineering notation: parse what a student types ("4.7k", "4k7", "100m", "1M", "2.2 µF")
   and format values for display ("4.70 kΩ"). Case matters for M (mega) vs m (milli). */

const PREFIX = { T: 12, G: 9, M: 6, k: 3, K: 3, '': 0, m: -3, u: -6, 'µ': -6, 'μ': -6, n: -9, p: -12 };
// Trailing unit names. None of these letters is also a prefix, so stripping them is safe.
const UNIT = /(ohms?|Ω|volts?|v|amps?|a|watts?|w|hz|f|h|s)$/i;

/** Parse an engineering-notation string. Returns a finite number, or null if it isn't one. */
export function parseEng(text) {
  if (typeof text === 'number') return Number.isFinite(text) ? text : null;
  if (typeof text !== 'string') return null;
  let s = text.replace(/[\s,]/g, '').replace(/meg/i, 'M').replace(UNIT, '');
  if (!s) return null;
  // R-notation: 4k7 = 4.7k, 2R2 = 2.2, 1M5 = 1.5M
  let m = /^([+-]?\d+)([TGMkKmuµμnpR])(\d+)$/.exec(s);
  if (m) return Number(`${m[1]}.${m[3]}`) * 10 ** (m[2] === 'R' ? 0 : PREFIX[m[2]]);
  m = /^([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)([TGMkKmuµμnp]?)$/.exec(s);
  if (!m) return null;
  const v = Number(m[1]) * 10 ** PREFIX[m[2]];
  return Number.isFinite(v) ? v : null;
}

const SI = [[1e12, 'T'], [1e9, 'G'], [1e6, 'M'], [1e3, 'k'], [1, ''], [1e-3, 'm'], [1e-6, 'µ'], [1e-9, 'n'], [1e-12, 'p']];

/** Format with an SI prefix and `sig` significant figures: formatEng(0.004, 'A') → "4.00 mA". */
export function formatEng(value, unit = '', sig = 3) {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  if (value === 0) return `0 ${unit}`.trim();
  const a = Math.abs(value);
  let i = SI.findIndex(([f]) => a >= f);
  if (i < 0) i = SI.length - 1;
  // rounding can carry into the next prefix: 999.96 → "1000" → show "1.00 k"
  if (i > 0 && Math.abs(Number((value / SI[i][0]).toPrecision(sig))) >= 1000) i -= 1;
  const n = value / SI[i][0];
  const digits = Math.max(0, sig - 1 - Math.floor(Math.log10(Math.abs(Number(n.toPrecision(sig))))));
  return `${n.toFixed(Math.min(digits, 6))} ${SI[i][1]}${unit}`.trim();
}

/** Round to sig figures as a plain number, for comparisons and JSON. */
export function roundSig(value, sig = 3) {
  if (!Number.isFinite(value) || value === 0) return value;
  return Number(value.toPrecision(sig));
}
