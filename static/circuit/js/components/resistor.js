import { stampAdmittance } from '../core/mna.js';
import { formatEng } from '../core/units.js';

export default {
  type: 'resistor',
  label: 'Resistor',
  prefix: 'R',
  pins: ['a', 'b'],
  defaults: { R: 1000, Pmax: 0.25 },

  validate(p, id) {
    const out = [];
    if (!Number.isFinite(p.R) || p.R <= 0) out.push(`${id} needs a resistance above 0 Ω. For a dead short, use a wire.`);
    else if (p.R < 1e-6 || p.R > 1e12) out.push(`${id} = ${formatEng(p.R, 'Ω')} is outside what the simulator handles (1 µΩ to 1 TΩ).`);
    if (!Number.isFinite(p.Pmax) || p.Pmax <= 0) out.push(`${id} needs a power rating above 0 W.`);
    return out;
  },
  paths: () => [['a', 'b']],

  stamp(A, rhs, ctx) {
    stampAdmittance(A, ctx.node('a'), ctx.node('b'), 1 / ctx.params.R);
  },

  pinCurrents(ctx) {
    const i = ctx.v('a').sub(ctx.v('b')).scale(1 / ctx.params.R);
    return { a: i, b: i.neg() };
  },

  checks(ctx, r) {
    const { Pmax } = ctx.params;
    if (r.p > Pmax * 1.0001) {
      return [{
        level: 'warning', code: 'overpower', ids: [ctx.id],
        message: `${ctx.id} is dissipating ${formatEng(r.p, 'W')}, rated ${formatEng(Pmax, 'W')} — it'll cook. `
          + 'Power in a resistor is I²R; past its rating it overheats, discolors and can burn open.',
      }];
    }
    return [];
  },
};
