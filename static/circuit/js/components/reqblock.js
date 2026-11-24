/* Req block: one resistor on the board that holds its own small circuit between ports A and B.

   The block never reaches the MNA matrix itself. buildNetlist() flattens it first: its inner
   parts join the circuit as "Req1/R2", "Req1/W3"…, and two hidden wires tie the block's outer
   pins (Req1.a, Req1.b) to its inner ports (Req1/A.j, Req1/B.j). So the meter, the live values
   and every check see the real inside, and Req is just what that inside works out to. */

export default {
  type: 'reqblock',
  label: 'Req block',
  prefix: 'Req',
  pins: ['a', 'b'],
  defaults: {},

  validate: () => [],
  paths: () => [['a', 'b']],
  stamp() { /* flattened away before stamping */ },
};
