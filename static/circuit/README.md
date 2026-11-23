# Circuit Bench

A DC circuit builder and multimeter safety trainer that runs entirely in the browser. It's served at `/tools/circuit`, and the solver debug page is at `/tools/circuit/debug`.

It's plain ES modules, with no build step and no dependencies. The model and solver code never touches the DOM, so it runs under Node.

## Run the tests

From the repo root:

```
node --test
```

Tests live in `tests/circuit/`, outside `static/`, so they aren't served.

## How it fits together

```
js/core/complex.js     tiny complex-number class (DC uses im = 0; AC will use the rest)
js/core/units.js       parse "4.7k" / "4k7" / "100m"; format "4.70 kΩ"
js/core/netlist.js     circuit model, union-find node building, save/load
js/core/mna.js         the MNA matrix, stamp helpers, Gaussian elimination with partial pivoting
js/core/solver.js      solve(circuit, { freq }) → node voltages, part currents and power, issues
js/components/*.js     one file per part type
js/components/registry.js   the list of part types
```

The circuit is plain JSON: `components` (id, type, params) and `wires` (two terminal names such as `"R1.a"`). Wires and closed switches are ideal. The pins they join become one node, and the current in each wire is worked out from the parts around it. A wire with `"cut": true` leaves two open ends.

`solve()` never returns `NaN` or `Infinity`. Anything it can't answer comes back as an issue `{ level, code, message }`, where `level` is `error`, `warning` or `info`.

## Add a component

1. Create `js/components/yourpart.js` exporting a definition. The comment at the top of `registry.js` lists every field. The minimum is `type`, `prefix`, `pins`, `defaults`, `stamp(A, rhs, ctx)` and `pinCurrents(ctx)`.
2. Import it in `registry.js` and add it to the list.

Use the helpers in `mna.js` (`stampAdmittance`, `stampCurrent`, `stampVoltage`) inside `stamp`. For AC parts, read `ctx.omega` and stamp complex admittances. You never need to edit the solver.

## Add a meter

Meter profiles are JSON files in `meters/`. They arrive in Phase 3.
