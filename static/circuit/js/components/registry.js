/* Component registry. Adding a part = write one file with a stamp, then add one line below.

   A component definition:
     type, label, prefix ('R' → R1, R2…), pins ['a','b'], defaults {…}
     validate(params, id)        → string[]   problems that stop the solve
     stamp(A, rhs, ctx)                       add the part to the MNA system
     pinCurrents(ctx)            → {pin: Complex}  current ENTERING the part at each pin
   Optional:
     paths(params, state)        → [[pin,pin]]  DC-conducting pin pairs (floating-node analysis)
     shorts(params)              → [[pin,pin]]  ideal connections, merged into one node (closed switch)
     branches(params, state)     → n   extra current unknowns the stamp needs (ctx.branch(k))
     injections(params)          → {pin: A}  fixed currents pushed out of each pin (current sources)
     idealVoltage(params, state) → bool  a zero-impedance voltage source (loop check)
     initState(params)           → {}    per-solve state, e.g. a supply's CV/CC mode
     update(ctx)                 → bool  after a solve: change state and ask for a re-solve
     extra(ctx, result)          → {}    extra result fields
     checks(ctx, result)         → issue[]  warnings after the solve
     groundPin, isGround, isJunction, presets

   ctx: id, params, state, omega (rad/s, 0 for DC), node(pin) → matrix index (−1 = reference),
        branch(k) → matrix index; after the solve also v(pin) → Complex, x(k) → Complex,
        complex(n) → Complex. */

import resistor from './resistor.js';
import vsource from './vsource.js';
import isource from './isource.js';
import sw from './switch.js';
import ground from './ground.js';
import junction from './junction.js';

export function createRegistry(defs = []) {
  const map = new Map();
  const reg = {
    register(def) {
      if (!def || !def.type || !Array.isArray(def.pins) || typeof def.stamp !== 'function') {
        throw new Error(`bad component definition: ${def && def.type}`);
      }
      map.set(def.type, def);
      return reg;
    },
    get: (type) => map.get(type),
    has: (type) => map.has(type),
    types: () => [...map.keys()],
  };
  defs.forEach(reg.register);
  return reg;
}

export const registry = createRegistry([
  resistor,
  vsource,
  isource,
  sw,
  ground,
  junction,
]);
