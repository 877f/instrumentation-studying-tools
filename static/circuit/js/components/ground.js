/* Ground symbol. Every ground pin belongs to the reference node (0 V); several symbols are
   one node, tied together by an implicit ground bus. */

export default {
  type: 'ground',
  label: 'Ground',
  prefix: 'GND',
  pins: ['g'],
  defaults: {},
  isGround: true,

  validate: () => [],
  paths: () => [],
  stamp() {},
};
