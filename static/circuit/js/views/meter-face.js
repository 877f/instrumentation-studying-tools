/* A generic handheld DMM face: yellow holster, LCD, rotary dial, four jacks.
   Returns an SVG string; clickable parts carry data-dial / data-jack attributes. */

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const polar = (cx, cy, r, deg) => [cx + r * Math.sin((deg * Math.PI) / 180), cy - r * Math.cos((deg * Math.PI) / 180)];

/**
 * opts: { profile, meter, display: { text, unit, alert }, tone: 'go'|'amber'|'stop'|null, blownNow, highlight: { dial, jack } }
 */
export function meterFace({ profile, meter, display, tone, blownNow, highlight = {} }) {
  const W = 260, H = 456;
  const dial = profile.dial;
  const step = 280 / (dial.length - 1);
  const angleOf = (i) => -140 + i * step;
  const sel = dial.findIndex((d) => d.id === meter.dial);
  const cx = 130, cy = 262, rKnob = 42, rLabel = 82;

  const dialMarks = dial.map((d, i) => {
    const a = angleOf(i);
    const [tx, ty] = polar(cx, cy, rLabel, a);
    const [t0x, t0y] = polar(cx, cy, rKnob + 6, a);
    const [t1x, t1y] = polar(cx, cy, rKnob + 12, a);
    const cls = ['dial-pos', d.id === meter.dial ? 'on' : '', d.unsupported ? 'dim' : '', highlight.dial === d.id ? 'hint' : ''].join(' ');
    return `<g class="${cls}" data-dial="${esc(d.id)}" role="button" tabindex="0" aria-label="Dial: ${esc(d.label)}${d.unsupported ? ' (not yet)' : ''}">
      <circle class="hit" cx="${tx.toFixed(1)}" cy="${ty.toFixed(1)}" r="17"/>
      <line class="tick" x1="${t0x.toFixed(1)}" y1="${t0y.toFixed(1)}" x2="${t1x.toFixed(1)}" y2="${t1y.toFixed(1)}"/>
      <text x="${tx.toFixed(1)}" y="${(ty + 4).toFixed(1)}" text-anchor="middle">${esc(d.label)}</text></g>`;
  }).join('');
  const [px, py] = polar(cx, cy, rKnob - 8, angleOf(sel));

  const jx = [48, 104, 160, 216];
  const jacks = profile.jacks.map((j, i) => {
    const x = jx[i], y = 398;
    const isRed = meter.red === j.id, isCom = j.id === 'COM';
    const fuse = j.fuse ? meter.fuses[j.fuse] : null;
    const ring = j.kind === 'common' ? 'com' : 'red';
    return `<g class="jack ${isRed ? 'red-in' : ''} ${highlight.jack === j.id ? 'hint' : ''} ${isCom ? 'com' : ''}" data-jack="${esc(j.id)}"
        role="button" tabindex="0" aria-label="Jack ${esc(j.label)}${isRed ? ', red lead is here' : ''}">
      <circle class="hit" cx="${x}" cy="${y - 10}" r="24"/>
      <text class="jack-label" x="${x}" y="${y - 26}" text-anchor="middle">${esc(j.label)}</text>
      ${fuse ? `<text class="fuse ${fuse === 'blown' ? 'blown' : ''}" x="${x}" y="${y + 28}" text-anchor="middle">${fuse === 'blown' ? 'FUSE BLOWN' : esc(profile.fuses[j.fuse].label.replace(/ 1000 V$/, ''))}</text>` : ''}
      <circle class="socket ${ring}" cx="${x}" cy="${y}" r="13"/>
      <circle class="socket-hole" cx="${x}" cy="${y}" r="6"/>
      ${isRed ? `<circle class="plug red" cx="${x}" cy="${y}" r="9"/>` : ''}
      ${isCom ? `<circle class="plug black" cx="${x}" cy="${y}" r="9"/>` : ''}
    </g>`;
  }).join('');

  const off = meter.dial === 'off';
  const lcdClass = ['lcd', off ? 'off' : '', tone ? `tone-${tone}` : '', blownNow ? 'blown-flash' : ''].join(' ');
  const fn = dial[sel] && dial[sel].function;
  const ann = off ? '' : fn === 'current' || fn === 'voltage' || fn === 'resistance' ? `${fn === 'resistance' ? '' : 'DC'} AUTO` : '';
  const text = off ? '' : display.text;
  return `<svg class="dmm" viewBox="0 0 ${W} ${H}" role="group" aria-label="Multimeter">
    <rect class="holster" x="2" y="2" width="${W - 4}" height="${H - 4}" rx="28"/>
    <rect class="case" x="16" y="16" width="${W - 32}" height="${H - 32}" rx="18"/>
    <g class="${lcdClass}">
      <rect class="glass" x="32" y="30" width="196" height="90" rx="8"/>
      <text class="ann" x="44" y="48">${esc(ann)}</text>
      ${display.alert ? '<text class="ann warn" x="216" y="48" text-anchor="end">⚠</text>' : ''}
      <text class="digits ${display.alert ? 'alert' : ''}" x="${display.unit ? 176 : 214}" y="100" text-anchor="end">${esc(text)}</text>
      <text class="unit" x="216" y="100" text-anchor="end">${off ? '' : esc(display.unit || '')}</text>
    </g>
    <text class="brand" x="130" y="142" text-anchor="middle">BENCH DMM</text>
    <circle class="dial-ring" cx="${cx}" cy="${cy}" r="${rKnob + 16}"/>
    ${dialMarks}
    <circle class="knob" cx="${cx}" cy="${cy}" r="${rKnob}"/>
    <path class="knob-grip" d="M${cx - 10} ${cy - 34}h20v68h-20z" transform="rotate(${angleOf(sel).toFixed(1)} ${cx} ${cy})"/>
    <circle class="knob-dot" cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="4"/>
    ${jacks}
  </svg>`;
}
