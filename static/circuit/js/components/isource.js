/* Ideal DC current source: pushes I out of pin p into the circuit and draws it back in at n. */

import { stampCurrent } from '../core/mna.js';
import { formatEng } from '../core/units.js';

export default {
  type: 'isource',
  label: 'Current source',
  prefix: 'I',
  pins: ['p', 'n'],
  groundPin: 'n',
  defaults: { I: 0.001 },

  validate(p, id) {
    if (!Number.isFinite(p.I)) return [`${id} needs a current.`];
    if (Math.abs(p.I) > 1e4) return [`${id} = ${formatEng(p.I, 'A')} is beyond the simulator's range (limit 10 kA).`];
    return [];
  },
  paths: () => [],
  injections: (p) => ({ p: p.I, n: -p.I }),

  stamp(A, rhs, ctx) {
    stampCurrent(rhs, ctx.node('n'), ctx.node('p'), ctx.params.I);
  },

  pinCurrents(ctx) {
    const i = ctx.complex(ctx.params.I);
    return { p: i.neg(), n: i };
  },
};
