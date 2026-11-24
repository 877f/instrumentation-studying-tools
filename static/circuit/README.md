# Circuit Bench

A DC circuit builder and multimeter safety trainer that runs entirely in the browser.

- `/tools/circuit` is the landing page.
- `/tools/circuit/bench` is the editor and meter.
- `/tools/circuit/debug` is the solver debug page (paste circuit JSON, see every value).

## Using the bench

1. Pick a part on the left, then click the board to place it. Press R to rotate before or after placing.
2. Drag from one pin to another to wire them. Dropping a wire on another wire tees into it; clicking empty board adds a corner.
3. Click a part to set its value. Type `4.7k`, `4k7`, `220` or `1M`, or pick a standard E12/E24 value.
4. Drag the red and black probes from the meter panel onto pins or wires. Click the dial and jacks to set the meter up.
5. To measure current, select a wire, press **Cut wire**, and put the probes on the two cut ends.

The circuit autosaves in the browser. **Share** copies a link that holds the whole circuit.

**Req blocks** (the **Req block** tool) are for working series-parallel circuits by hand. A block sits on the board like one resistor (dashed outline, labelled `Req = ?`). Double-click it, or press **Open**, to open a window with its own small board between ports A and B; build any mix of resistors and further Req blocks in there. Close it and the block is one resistor in series again.

- The student types the Req they calculated and presses **Check** (1% tolerance). A wrong answer gets a hint in words only, never the formula. **Show me** reveals it instead.
- Until Req checks out, every part inside shows `I ?  V ?`. After it checks out, each part shows its current (green) and voltage (red), and the window lists the KCL lines at A and B and the KVL line for each path from A to B, each ticked when it balances.
- Change anything inside and the block locks again, so the student can predict the new Req.
- The meter's probes work inside a block. **Show inside on board** draws the block's inside in a bubble above it on the main board.
- Colors across the bench: resistance blue, current green, voltage red. A resistor or block shows its name and resistance above it, and its current (with a direction arrow) over its voltage drop ΔV below it, so labels stay about as wide as the part. When another resistor sits right below (parallel rows), current and drop share one line instead. On the main board those show while **Show values** is on; inside a block they always show.

Under the hood, `buildNetlist()` flattens each block before solving: inner parts become `Req1/R2`, and two hidden wires join `Req1.a` and `Req1.b` to the inner ports. `js/core/blocks.js` works out Req (a 1 A test source between A and B), grades guesses and builds the KCL/KVL lines; `tests/circuit/blocks.test.mjs` checks them against the hand calculation.

**Teacher demo** (Examples menu, or `/tools/circuit/bench#demo`) loads one board and walks through eleven setups: voltage done right, reversed leads, current through a cut wire, an ammeter across a supply, the red lead left in mA, the wrong current jack, a resistor over its power rating, ohms on a live circuit, in-circuit ohms, and lifting a leg. The steps live in `js/demo.js`; `tests/circuit/demo.test.mjs` checks that each step's on-screen text matches what the engine actually shows.

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
js/core/share.js       circuit ↔ compressed URL hash
js/core/blocks.js      Req blocks: scopes, Req, guess grading, KCL/KVL lines
js/components/*.js     one file per part type
js/components/registry.js   the list of part types
js/meter/meter-model.js     puts the meter into the circuit as real parts and reads it
js/meter/fuse.js            SAFE / OVER SPEC / SURVIVABLE ≤30 s / FUSE BLOWS
js/meter/mismatch.js        setup mistakes: lead in the wrong jack, ammeter across a part, ohms on a live circuit…
js/views/symbols.js         part geometry, symbols, wire routing, color bands
js/views/schematic.js       renders the board, finds what's under a point
js/views/meter-face.js      draws the meter
js/app.js                   editor state, panels, undo, autosave
js/demo.js                  the teacher demo circuit and its steps
meters/fluke-87v.json       meter profile
```

The meter is a circuit element. With both probes placed, it's added to the netlist based on the red lead's jack and the dial: 10 MΩ for volts, a test source for ohms, or fuse plus shunt for the current jacks, whatever the dial says. Then the circuit is re-solved. A blown fuse stays blown until you press **Replace fuse**.

The circuit is plain JSON: `components` (id, type, params) and `wires` (two terminal names such as `"R1.a"`). Wires and closed switches are ideal. The pins they join become one node, and the current in each wire is worked out from the parts around it. A wire with `"cut": true` leaves two open ends.

`solve()` never returns `NaN` or `Infinity`. Anything it can't answer comes back as an issue `{ level, code, message }`, where `level` is `error`, `warning` or `info`.

## Add a component

1. Create `js/components/yourpart.js` exporting a definition. The comment at the top of `registry.js` lists every field. The minimum is `type`, `prefix`, `pins`, `defaults`, `stamp(A, rhs, ctx)` and `pinCurrents(ctx)`.
2. Import it in `registry.js` and add it to the list.

Use the helpers in `mna.js` (`stampAdmittance`, `stampCurrent`, `stampVoltage`) inside `stamp`. For AC parts, read `ctx.omega` and stamp complex admittances. You never need to edit the solver.

## Add a meter

Copy `meters/fluke-87v.json` and edit it: jacks, fuse ratings, shunt resistances, input impedance, the ohms test source, and the dial positions with their display ranges. Each range lists `max`, `decimals`, `unit` and `scale`; the meter auto-ranges to the lowest one that fits. Values marked `"verify": true` came from memory and should be checked against the manual. The editor currently loads the 87V profile by path in `js/app.js`.
