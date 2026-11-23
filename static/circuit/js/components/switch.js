/* SPST switch. Closed, it's an ideal connection: its pins join one node (like a wire), and its
   current comes from the wiring-flow pass. Open, it connects nothing. No matrix stamp either way. */

export default {
  type: 'switch',
  label: 'Switch',
  prefix: 'S',
  pins: ['a', 'b'],
  defaults: { closed: true },

  validate: (p, id) => (typeof p.closed === 'boolean' ? [] : [`${id} must be open or closed.`]),
  shorts: (p) => (p.closed ? [['a', 'b']] : []),
  paths: () => [],
  stamp() {},
};
