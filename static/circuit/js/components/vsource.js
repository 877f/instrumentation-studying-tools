/* DC supply: a voltage source with a small internal resistance r and an optional current limit.
   Constant-voltage (CV) mode solves as V(p) − V(n) + r·I = V. If the current comes out above the
   limit, the supply re-solves in constant-current (CC) mode as a current source at the limit,
   the way a bench supply does when the CC lamp lights. */

import { stampVoltage, stampCurrent } from '../core/mna.js';
import { formatEng } from '../core/units.js';

const PRESETS = {
  bench: { V: 12, r: 0.01, ilimit: 1 },
  battery9v: { V: 9, r: 1.5, ilimit: null },
  batteryAA: { V: 1.5, r: 0.15, ilimit: null },
};

export default {
  type: 'vsource',
  label: 'DC supply',
  prefix: 'V',
  pins: ['p', 'n'],
  groundPin: 'n',
  defaults: { ...PRESETS.bench },
  presets: PRESETS,

  validate(p, id) {
    const out = [];
    if (!Number.isFinite(p.V)) out.push(`${id} needs a voltage.`);
    else if (Math.abs(p.V) > 1e6) out.push(`${id} = ${formatEng(p.V, 'V')} is beyond anything on a bench (limit 1 MV).`);
    if (!Number.isFinite(p.r) || p.r < 0 || p.r > 1e6) out.push(`${id}'s internal resistance must be between 0 Ω and 1 MΩ.`);
    if (p.ilimit !== null && p.ilimit !== undefined && !(Number.isFinite(p.ilimit) && p.ilimit > 0)) {
      out.push(`${id}'s current limit must be above 0 A, or empty for no limit.`);
    }
    return out;
  },

  initState: () => ({ mode: 'CV', sign: 1 }),
  // In CC mode it's a current source: no DC path through it for floating-node analysis.
  paths: (p, state) => (state.mode === 'CV' ? [['p', 'n']] : []),
  idealVoltage: (p, state) => state.mode === 'CV' && p.r === 0,
  injections: (p, state) => (state.mode === 'CC' ? { p: state.sign * p.ilimit, n: -state.sign * p.ilimit } : null),
  branches: (p, state) => (state.mode === 'CV' ? 1 : 0),

  stamp(A, rhs, ctx) {
    const { V, r, ilimit } = ctx.params;
    const p = ctx.node('p'), n = ctx.node('n');
    if (ctx.state.mode === 'CV') stampVoltage(A, rhs, p, n, ctx.branch(0), V, r);
    else stampCurrent(rhs, n, p, ctx.state.sign * ilimit);
  },

  pinCurrents(ctx) {
    // supply current, out of + into the circuit
    const out = ctx.state.mode === 'CV' ? ctx.x(0) : ctx.complex(ctx.state.sign * ctx.params.ilimit);
    return { p: out.neg(), n: out };
  },

  /** CV → CC when the current passes the limit; CC → CV if the output would rise past the setpoint. */
  update(ctx) {
    const { V, ilimit } = ctx.params;
    if (!(ilimit > 0)) return false;
    if (ctx.state.mode === 'CV') {
      const i = ctx.x(0).re;
      if (Math.abs(i) > ilimit * (1 + 1e-9)) {
        ctx.state.mode = 'CC';
        ctx.state.sign = Math.sign(i) || 1;
        return true;
      }
      return false;
    }
    const vt = ctx.v('p').sub(ctx.v('n')).re;
    if (Math.abs(vt) > Math.abs(V) * (1 + 1e-9) || Math.sign(vt) * Math.sign(V) < 0) {
      ctx.state.mode = 'CV';
      return true;
    }
    return false;
  },

  extra(ctx, r) {
    const supply = r.pins.p.i.neg();
    return {
      mode: ctx.state.mode,
      supplyCurrent: supply.re,
      terminalVoltage: r.v,
      delivered: -r.p,
    };
  },

  checks(ctx, r) {
    const out = [];
    const { V, ilimit } = ctx.params;
    if (ctx.state.mode === 'CC') {
      out.push({
        level: 'info', code: 'cc-mode', ids: [ctx.id],
        message: `${ctx.id} hit its ${formatEng(ilimit, 'A')} current limit and switched to constant-current (CC) mode. `
          + `Its output sagged from ${formatEng(V, 'V')} to ${formatEng(r.extra.terminalVoltage, 'V')}: `
          + 'the load wanted more current than the limit allows.',
      });
    }
    return out;
  },
};
