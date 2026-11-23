/* Fuse verdict tiers for a current jack, from the meter profile's fuse data. */

import { formatEng } from '../core/units.js';

export const TIERS = {
  safe: { label: 'SAFE', tone: 'go' },
  shortterm: { label: 'SURVIVABLE ≤30 s', tone: 'amber' },
  overspec: { label: 'OVER SPEC', tone: 'amber' },
  blows: { label: 'FUSE BLOWS', tone: 'stop' },
};

/** current: magnitude in amps through the jack. */
export function fuseVerdict(profile, jack, current) {
  const f = profile.fuses[jack.fuse];
  const I = formatEng(current, 'A');
  const cont = formatEng(f.continuous, 'A');
  let tier, message;
  if (current <= f.continuous) {
    tier = 'safe';
    message = `${I} through the ${jack.label} jack, within its ${cont} rating.`;
  } else if (f.shortTerm && current <= f.shortTerm.max) {
    tier = 'shortterm';
    message = `Survivable for ≤${f.shortTerm.seconds} s. ${I} is over the ${cont} continuous rating. The meter tolerates up to `
      + `${formatEng(f.shortTerm.max, 'A')} for ${f.shortTerm.seconds} seconds, then it needs time to cool. Keep it brief.`;
  } else if (current <= f.rating) {
    tier = 'overspec';
    message = `Outside rated input — fuse may survive, don't do this. ${I} is over the ${jack.label} jack's ${cont} rating `
      + `but under the ${f.label} fuse, so it probably won't blow, but the meter isn't specified for it.`;
  } else {
    tier = 'blows';
    message = `${I} tried to flow through the ${f.label} fuse. The fuse melts open to protect the meter (and you). `
      + 'Now the meter reads 0 and the circuit is open at the leads.';
  }
  return { tier, ...TIERS[tier], current, fuse: jack.fuse, fuseLabel: f.label, jack: jack.id, message };
}
