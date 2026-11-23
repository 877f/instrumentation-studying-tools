/* A connection point: lets a wire end in the middle of the board or tee into another wire.
   Electrically it's nothing; its single pin just joins whatever wires meet there. */

export default {
  type: 'junction',
  label: 'Junction',
  prefix: 'J',
  pins: ['j'],
  defaults: {},
  isJunction: true,

  validate: () => [],
  paths: () => [],
  stamp() {},
};
