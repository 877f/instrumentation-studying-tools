'use strict';
/* Problem sets (type "problems"), e.g. Household kWh and Circuit Diagrams.
   Loaded after formula.js and before app.js. Uses app.js helpers at call time (app, $, esc, rich, api, go, pct,
   plural, rail, verdictHTML, markTick, scrollToEl, showErr, insertAtCursor, getChapter, busy, renderToken),
   formula.js (keyButtons, FORMULA_KEYS) and instruments.js (meterSVG, scaleHTML, lamp, animateInstruments).
   Nothing is saved: settings and stats live in memory and reset when the page closes.
   Routes: #/<module> (levels) · #/problem · #/problem-results · #/problem-summary/<module>
   Formulas appear only after you check an answer and on the results and summary screens, never on a question. */

const PS = { mods: {}, run: null, lastRun: null, sheets: {} };
const PROBLEM_ROUTES = {
  problem: () => problemView(),
  'problem-results': (arg, token) => problemResultsView(token),
  'problem-summary': (arg, token) => problemSummaryView(decodeURIComponent(arg || ''), token),
};
const MODE_TAGS = { worksheet: 'worksheet hours', variations: 'random hours', custom: 'your own numbers' };

/* in-memory state, per module: stats per level, missed question types, settings, the custom table */
function pmod(c) {
  return (PS.mods[c.id] ||= {
    detail: c, stats: {}, missed: {},
    mode: c.modes.length ? c.modes[0].id : null,
    settings: Object.fromEntries(c.settings.map((s) => [s.key, String(s.default)])),
    custom: c.appliances ? { watts: c.appliances.map((a) => wattsText(a.watts)), hours: c.appliances.map(() => ''),
                             monthly: false } : null,
  });
}
function wattsText(w) { return Number(w).toLocaleString('en-US', { maximumFractionDigits: 3 }); }
function readNumber(s) {
  const t = String(s).replace(/[,\s]/g, '');
  return /^(\d+\.?\d*|\.\d+)$/.test(t) ? Number(t) : NaN;
}
/* "I = 0.1 A (= 100 mA) · P = 2.4 W": line breaks only between answers or before "(=". */
function headlineHTML(h) { return h.split(' · ').map((p) => rich(p.replace(/ (?!\()/g, ' '))).join(' · '); }
function pTotals(m) {
  return Object.values(m ? m.stats : {}).reduce((t, s) => ({ answers: t.answers + s.answers, correct: t.correct + s.correct }),
    { answers: 0, correct: 0 });
}
async function getSheet(mid) {
  return (PS.sheets[mid] ||= await api(`/api/problems/${encodeURIComponent(mid)}/formulas`));
}

/* Accuracy this session, on a 0-100 meter. */
function accuracyMeter(c, m) {
  const t = pTotals(m);
  const p = t.answers ? Math.round((100 * t.correct) / t.answers) : 0;
  return `<div class="bezel">${meterSVG({ key: 'pm:' + c.id, value: p, max: 100, legend: 'ACCURACY', tag: c.badge,
    readout: t.answers ? `${t.correct} OF ${t.answers}` : 'NOT STARTED',
    label: t.answers ? `${t.correct} of ${t.answers} right this session` : 'Not started this session' })}</div>`;
}

/* ------------------------------------------------------------ home card */

function problemCard(c) {
  const m = PS.mods[c.id];
  return `<a class="bay" href="#/${esc(c.id)}">${accuracyMeter(c, m)}
    <div class="bay-body"><div class="label">Problem set</div>
      <h2 class="bay-title">${esc(c.title)}</h2>
      <p class="bay-meta">${esc(c.subtitle)}</p>
      <span class="bay-go">${pTotals(m).answers ? 'Keep practicing' : 'Start practicing'}</span></div></a>`;
}

/* ---------------------------------------------------------- module page */

function problemModuleView(c) {
  const m = pmod(c);
  const tried = pTotals(m).answers;
  const setup = c.modes.length || c.settings.length;
  app.innerHTML = `${rail('#/', 'Chapters')}
    <header class="page-head"><div class="label">Problem set</div><h1>${esc(c.title)}</h1>
      <p class="lede">${esc(c.intro)}</p>
      ${c.reminder ? `<p class="reminder">${esc(c.reminder).replace(/ ([=×÷]) /g, ' $1 ')}</p>` : ''}</header>
    <div class="mod-grid">
      ${accuracyMeter(c, m)}
      <div>
        ${setup ? `<div class="face form ps-setup">
          ${c.modes.length ? `<fieldset class="field"><legend class="label">Mode</legend>
            <div class="seg">${c.modes.map((md) => `<label><input type="radio" name="pmode" value="${esc(md.id)}"
              ${md.id === m.mode ? 'checked' : ''}><span>${esc(md.label)}</span></label>`).join('')}</div>
            <p class="help" id="pmodeHelp"></p></fieldset>` : ''}
          ${c.settings.map((s) => `<div class="field"><label class="label" for="set-${esc(s.key)}">${esc(s.label)}</label>
            <div class="setting"><input id="set-${esc(s.key)}" data-key="${esc(s.key)}" type="text" inputmode="decimal"
              autocomplete="off" value="${esc(m.settings[s.key])}"><span>${esc(s.unit)}</span></div></div>`).join('')}
        </div>` : ''}
        <div class="levels" id="levelsBox">${c.levels.map((lv) => {
          const s = m.stats[lv.id];
          return `<button class="face level level-btn" data-level="${esc(lv.id)}">
            <span class="bubble" aria-hidden="true"><b>${esc(lv.id[0])}</b><i>${esc(lv.id.slice(1))}</i></span>
            <span class="lvl-body"><span class="lvl-title">Level ${esc(lv.id)} · ${esc(lv.title)}</span>
              <span class="lvl-desc">${esc(lv.desc)}</span>
              <span class="lvl-stat">${s ? `${pct(s.correct, s.answers)} right · ${s.correct} of ${plural(s.answers, 'question')} this session`
                : 'Not tried this session'}</span></span>
            <span class="chev" aria-hidden="true"></span></button>`;
        }).join('')}</div>
        ${m.custom ? customHTML(c, m) : ''}
        <div id="startErr" class="alert bad" hidden></div>
        ${tried ? `<a class="btn block spaced" href="#/problem-summary/${esc(c.id)}">Session summary</a>` : ''}
        <p class="fine">Nothing is saved. Stats and settings reset when you close or reload this page.</p>
      </div>
    </div>`;

  const syncMode = () => {
    const picked = app.querySelector('input[name=pmode]:checked');
    if (picked) m.mode = picked.value;
    const md = c.modes.find((x) => x.id === m.mode);
    if ($('pmodeHelp')) $('pmodeHelp').textContent = md ? md.help : '';
    $('levelsBox').hidden = m.mode === 'custom';
    if ($('customBox')) $('customBox').hidden = m.mode !== 'custom';
    $('startErr').hidden = true;
  };
  app.querySelectorAll('input[name=pmode]').forEach((i) => i.addEventListener('change', syncMode));
  app.querySelectorAll('.setting input').forEach((i) => i.addEventListener('input', () => { m.settings[i.dataset.key] = i.value; }));
  app.querySelectorAll('.level-btn').forEach((b) => { b.onclick = () => startProblems(c, b.dataset.level, m.mode); });
  if (m.custom) bindCustom(c, m);
  syncMode();
  animateInstruments(app);
}

function settingsFor(c, m) {
  const out = {};
  for (const s of c.settings) {
    const v = readNumber(m.settings[s.key]);
    if (!(v >= s.min && v <= s.max)) throw new Error(`${s.label} must be a number from ${s.min} to ${s.max} ${s.unit}.`);
    out[s.key] = v;
  }
  return out;
}

function startErr(msg) {
  const el = $('startErr');
  if (el) { el.textContent = msg; el.hidden = false; scrollToEl(el); } else alert(msg);
}

async function startProblems(c, levelId, mode, extra = {}) {
  const m = pmod(c);
  if (busy) return;
  busy = true;
  try {
    const r = await api('/api/problems/session', { module: c.id, level: levelId, mode, settings: settingsFor(c, m), ...extra });
    PS.run = { module: c.id, title: c.title, level: c.levels.find((l) => l.id === levelId), mode,
               questions: r.questions, idx: 0, results: [], answered: false, feedback: null };
    go('#/problem');
  } catch (e) {
    startErr(e.message);
  } finally {
    busy = false;
  }
}

/* Custom mode: the appliance table with editable wattages and hours. Rows without hours are skipped. */
function customHTML(c, m) {
  const cu = m.custom;
  return `<div class="face form" id="customBox" hidden>
    <p class="help flush">Type the hours from your teacher's problem, and change any wattage to match it.
      Rows with no hours are left out.</p>
    <div class="tb-wrap"><table class="tb tb-edit">
      <thead><tr><th scope="col">APPLIANCE</th><th scope="col" class="num">POWER RATING (WATTS)</th>
        <th scope="col" class="num">HOURS USED</th></tr></thead>
      <tbody>${c.appliances.map((a, i) => `<tr><th scope="row">${esc(a.name)}</th>
        <td class="in"><input data-cw="${i}" type="text" inputmode="decimal" autocomplete="off" value="${esc(cu.watts[i])}"
          aria-label="${esc(a.name)} power rating in watts"></td>
        <td class="in"><input data-ch="${i}" type="text" inputmode="decimal" autocomplete="off" value="${esc(cu.hours[i])}"
          placeholder="–" aria-label="${esc(a.name)} hours used"></td></tr>`).join('')}</tbody>
    </table></div>
    <label class="toggle spaced"><input type="checkbox" id="cMonthly" ${cu.monthly ? 'checked' : ''}>
      <span class="switch"></span>Monthly cost too (like Level K5)</label>
    <button class="btn primary block start" id="customGo">Solve it</button>
    <p class="center"><button class="link" id="customReset" type="button">Reset wattages and clear hours</button></p>
  </div>`;
}

function bindCustom(c, m) {
  const cu = m.custom;
  app.querySelectorAll('[data-cw]').forEach((i) => i.addEventListener('input', () => { cu.watts[+i.dataset.cw] = i.value; }));
  app.querySelectorAll('[data-ch]').forEach((i) => i.addEventListener('input', () => { cu.hours[+i.dataset.ch] = i.value; }));
  $('cMonthly').onchange = (e) => { cu.monthly = e.target.checked; };
  $('customReset').onclick = () => {
    cu.watts = c.appliances.map((a) => wattsText(a.watts));
    cu.hours = c.appliances.map(() => '');
    problemModuleView(c);
  };
  $('customGo').onclick = () => {
    const rows = [], bad = [];
    c.appliances.forEach((a, i) => {
      if (!cu.hours[i].trim()) return;
      const watts = readNumber(cu.watts[i]), hours = readNumber(cu.hours[i]);
      if (!(watts > 0)) bad.push(`${a.name}: type the power rating in watts.`);
      else if (!(hours > 0 && hours <= 24)) bad.push(`${a.name}: hours must be above 0 and at most 24.`);
      else rows.push({ name: a.name, watts, hours });
    });
    if (bad.length) return startErr(bad.join(' '));
    if (!rows.length) return startErr('Type the hours for at least one appliance.');
    startProblems(c, cu.monthly ? 'K5' : 'K4', 'custom', { rows });
  };
}

/* ------------------------------------------------------------ a question */

function inputHTML(key, label, extra = '') {
  return `<input data-field="${esc(key)}" id="pf-${esc(key)}" type="text" autocomplete="off" autocapitalize="off"
    autocorrect="off" spellcheck="false" enterkeyhint="done" aria-label="${esc(label)}" ${extra}>`;
}

/* The appliance table, styled like the textbook's. Givens are text; answer boxes are inputs. */
function tableHTML(q) {
  const L = q.layout;
  const cell = (x, label) => (x.input
    ? `<td class="in" data-cell="${esc(x.input)}">${inputHTML(x.input, label, 'inputmode="decimal"')}<span class="fix" hidden></span></td>`
    : `<td class="num">${esc(x.text)}</td>`);
  return `<div class="tb-wrap"><table class="tb">
    <thead><tr><th scope="col">APPLIANCE</th><th scope="col" class="num">POWER RATING (WATTS)</th>
      <th scope="col" class="num">HOURS USED</th><th scope="col" class="num">kWh</th></tr></thead>
    <tbody>${L.rows.map((r) => `<tr><th scope="row">${esc(r.name)}</th>${cell(r.watts, `${r.name}: power rating`)}${
      cell(r.hours, `${r.name}: hours used`)}${cell(r.kwh, `${r.name}: kWh`)}</tr>`).join('')}</tbody>
    ${L.total ? `<tfoot><tr><th scope="row" colspan="3">TOTAL kWh</th>${cell({ input: L.total }, 'TOTAL kWh')}</tr></tfoot>` : ''}
  </table></div>`;
}

/* A series loop: battery on the left (long plate +), zigzag resistor on the right, current arrow on top. */
function circuitSVG(L) {
  const x1 = 150, x2 = 290, yt = 64, yb = 200, ym = 132, mid = (x1 + x2) / 2;
  const val = (k) => (L.labels[k] == null ? '<tspan class="q">?</tspan>' : esc(L.labels[k]));
  const zig = [[x2, 96], [x2, 102], [x2 + 13, 108], [x2 - 13, 120], [x2 + 13, 132], [x2 - 13, 144], [x2 + 13, 156], [x2, 162], [x2, 168]];
  const say = (k) => `${k} ${L.labels[k] == null ? 'unknown' : L.labels[k]}`;
  const aria = `Series circuit: a battery, ${say('V')}, and a resistor, ${say('R')}, with current ${say('I')}` +
               (L.power ? `, power P ${L.power}` : '');
  return `<svg class="circuit" viewBox="0 0 440 ${L.power ? 236 : 222}" role="img" aria-label="${esc(aria)}">
    <path class="wire" d="M${x1} ${ym - 9}V${yt}H${x2}V96M${x2} 168V${yb}H${x1}V${ym + 9}"/>
    <path class="wire" d="M${zig.map((p) => p.join(' ')).join('L')}"/>
    <line class="plate" x1="${x1 - 24}" y1="${ym - 9}" x2="${x1 + 24}" y2="${ym - 9}"/>
    <line class="plate neg" x1="${x1 - 12}" y1="${ym + 9}" x2="${x1 + 12}" y2="${ym + 9}"/>
    <text class="sign" x="${x1 + 36}" y="${ym - 20}">+</text>
    <text class="sign" x="${x1 + 36}" y="${ym + 22}">−</text>
    <path class="arrow" d="M${mid - 9} ${yt - 8}L${mid + 10} ${yt}L${mid - 9} ${yt + 8}Z"/>
    <text class="lbl mid" x="${mid}" y="${yt - 24}">I = ${val('I')}</text>
    <text class="lbl end" x="${x1 - 36}" y="${ym}">V = ${val('V')}</text>
    <text class="lbl" x="${x2 + 26}" y="${ym - (L.power ? 16 : 0)}">R = ${val('R')}</text>
    ${L.power ? `<text class="lbl" x="${x2 + 26}" y="${ym + 18}">P = ${esc(L.power)}</text>` : ''}
  </svg>`;
}

function fieldHTML(f, extra = '') {
  return `<div class="pfield" data-cell="${esc(f.key)}">
    <label for="pf-${esc(f.key)}">${esc(f.label)}</label>
    <div class="ansrow">${inputHTML(f.key, f.label, `placeholder="${esc(f.unit === '$' ? 'Answer in dollars' : `Answer in ${f.unit}`)}"
      data-unit="${esc(f.unit)}" ${extra}`)}</div>
    <span class="fix" hidden></span></div>`;
}

function problemView() {
  const r = PS.run;
  if (!r) return go('#/', true);
  const q = r.questions[r.idx];
  const n = r.questions.length;
  const table = q.layout.kind === 'table';
  const below = table ? q.fields.filter((f) => q.layout.below.includes(f.key)) : q.fields;
  app.innerHTML = `<div class="quiz">
    <div class="quizbar">
      <button class="icon-btn" id="quitBtn" aria-label="End level" title="End level">✕</button>
      ${scaleHTML(r.results.map((x) => (x.ok ? 'ok' : x.revealed ? 'rev' : 'no')), n, `Question ${r.idx + 1} of ${n}`)}
      <span class="qcount">${r.idx + 1}/${n}</span>
    </div>
    <article class="face qcard">
      <div class="label">Level ${esc(r.level.id)} · ${esc(r.level.title)}</div>
      <p class="qtext">${rich(q.prompt)}</p>
      <div class="qtags">${esc(q.type_label)}${MODE_TAGS[r.mode] ? ` · ${MODE_TAGS[r.mode]}` : ''}</div>
      <form id="pForm" autocomplete="off">
        ${table ? tableHTML(q) : circuitSVG(q.layout)}
        ${below.map((f) => fieldHTML(f, table ? 'inputmode="decimal"' : '')).join('')}
        ${q.formula ? `<div class="pfield formula" data-cell="__formula">
          <label for="pf-formula">Formula used <small>optional, not scored</small></label>
          <div class="ansrow"><input id="pf-formula" data-formula="1" type="text" autocomplete="off" autocapitalize="off"
            autocorrect="off" spellcheck="false" enterkeyhint="done" placeholder="${esc(q.formula.target)} = …"
            aria-label="Formula used for step 1 (optional)"></div>
          <span class="fix" hidden></span></div>` : ''}
        ${table ? '' : '<div class="keys" id="pkeys"></div><p class="formats">Unit optional · prefixes work, like 2.5 mA or 4.7 kΩ</p>'}
        <button class="btn primary block start" id="checkBtn" type="submit">Check</button>
      </form>
      <div id="err" class="alert bad" hidden></div>
      <div class="links"><button class="link" id="hintBtn" type="button">Hint</button>
        <button class="link" id="giveBtn" type="button">Show answer</button></div>
      <div id="hint" class="hint" hidden><b>Hint:</b> ${rich(q.hint)}</div>
    </article>
    <div id="fb" aria-live="polite"></div>
  </div>`;

  const inputs = [...app.querySelectorAll('#pForm input')];
  $('pForm').onsubmit = (e) => { e.preventDefault(); problemSubmit(); };
  $('hintBtn').onclick = () => { $('hint').hidden = !$('hint').hidden; };
  $('giveBtn').onclick = problemGiveUp;
  $('quitBtn').onclick = () => { if (!r.results.length || confirm('End this level and see your results?')) problemFinish(); };
  inputs.forEach((inp, i) => inp.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || i === inputs.length - 1) return;      // Enter moves down the boxes; the last one checks
    e.preventDefault();
    inputs[i + 1].focus();
  }));
  if (!table) bindProblemKeys(inputs);
  if (r.answered && r.feedback) {
    Object.entries(r.feedback.answers).forEach(([k, v]) => { const el = $('pf-' + k); if (el) el.value = v; });
    if ($('pf-formula')) $('pf-formula').value = r.feedback.formula;
    problemLock();
    problemFeedback(r.feedback.res, false);
  } else if (window.matchMedia('(hover: hover)').matches) {
    inputs[0].focus({ preventScroll: true });
  }
}

/* Keys under the circuit: prefixes and the unit for a number box, formula keys for the formula box. */
function bindProblemKeys(inputs) {
  const box = $('pkeys');
  let last = inputs[0];
  const show = (inp) => {
    last = inp;
    const kind = inp.dataset.formula ? 'formula' : inp.dataset.unit;
    if (box.dataset.kind === kind) return;
    box.dataset.kind = kind;
    box.innerHTML = keyButtons(inp.dataset.formula ? FORMULA_KEYS
      : [['×10^', 'x10^'], ['µ', 'µ'], ['m', 'm'], ['k', 'k'], ['M', 'M'], [inp.dataset.unit, inp.dataset.unit]]);
  };
  inputs.forEach((inp) => inp.addEventListener('focus', () => show(inp)));
  box.addEventListener('pointerdown', (e) => { if (e.target.closest('.key')) e.preventDefault(); });   // keep the phone keyboard open
  box.addEventListener('click', (e) => { const b = e.target.closest('.key'); if (b && last) insertAtCursor(last, b.dataset.ins); });
  show(inputs[0]);
}

function problemLock() {
  app.querySelectorAll('#pForm input, #checkBtn, #giveBtn, #pkeys .key').forEach((el) => { el.disabled = true; });
}

async function problemSubmit() {
  const r = PS.run;
  if (!r || r.answered || busy) return;
  const q = r.questions[r.idx];
  const answers = Object.fromEntries(q.fields.map((f) => [f.key, $('pf-' + f.key).value.trim()]));
  app.querySelectorAll('[data-cell]').forEach((el) => el.classList.remove('miss'));
  const empty = q.fields.filter((f) => !answers[f.key]);
  if (empty.length) {
    empty.forEach((f) => app.querySelector(`[data-cell="${f.key}"]`).classList.add('miss'));
    return showErr(empty.length === q.fields.length ? 'Type your answers first, or tap Show answer.'
      : `Fill in every box first. Still empty: ${empty.map((f) => f.label).join(', ')}.`);
  }
  $('err').hidden = true;
  busy = true;
  $('checkBtn').disabled = true;
  try {
    const formula = $('pf-formula') ? $('pf-formula').value.trim() : '';
    const res = await api('/api/problems/check', { module: r.module, level: r.level.id, params: q.params, answers, formula });
    if (res.status === 'unparsed') {      // not graded: say what couldn't be read
      const bad = res.fields.filter((f) => f.status === 'unparsed');
      bad.forEach((f) => app.querySelector(`[data-cell="${f.key}"]`).classList.add('miss'));
      return showErr(bad.map((f) => `${f.label}: ${f.message}`).join(' '));
    }
    problemRecord(res, answers, formula);
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
    if (PS.run === r && !r.answered && $('checkBtn')) $('checkBtn').disabled = false;
  }
}

async function problemGiveUp() {
  const r = PS.run;
  if (!r || r.answered || busy) return;
  busy = true;
  try {
    const q = r.questions[r.idx];
    const formula = $('pf-formula') ? $('pf-formula').value.trim() : '';
    const answers = Object.fromEntries(q.fields.map((f) => [f.key, $('pf-' + f.key).value.trim()]));
    problemRecord(await api('/api/problems/reveal', { module: r.module, level: r.level.id, params: q.params }), answers, formula);
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
  }
}

function problemRecord(res, answers, formula) {
  const r = PS.run;
  const q = r.questions[r.idx];
  const m = PS.mods[r.module];
  const ok = res.status === 'correct';
  const revealed = res.status === 'revealed';
  const s = (m.stats[r.level.id] ||= { answers: 0, correct: 0 });
  s.answers += 1;
  s.correct += ok ? 1 : 0;
  // A question type counts as missed if any of its boxes is wrong (six rows, two wrong: one miss).
  const wrong = new Set(res.fields.filter((f) => f.status !== 'correct').map((f) => f.miss));
  new Set(res.fields.map((f) => f.miss)).forEach((label) => {
    const k = `${r.level.id}|${label}`;
    if (wrong.has(label)) {
      const x = (m.missed[k] ||= { level: r.level.id, label, count: 0, fixed: false });
      x.count += 1;
      x.fixed = false;
    } else if (m.missed[k]) {
      m.missed[k].fixed = true;
    }
  });
  r.results.push({ ok, revealed, desc: q.desc, wrong: [...wrong], headline: res.headline });
  r.answered = true;
  r.feedback = { res, answers, formula };
  problemLock();
  markTick(r.results.length - 1, ok ? 'ok' : revealed ? 'rev' : 'no', r.results.length);
  problemFeedback(res, true);
}

function problemFeedback(res, scroll) {
  const r = PS.run;
  const ok = res.status === 'correct';
  const revealed = res.status === 'revealed';
  const last = r.idx === r.questions.length - 1;
  const table = r.questions[r.idx].layout.kind === 'table';
  res.fields.forEach((f) => {
    const cell = app.querySelector(`[data-cell="${f.key}"]`);
    if (!cell) return;
    cell.classList.add(f.status === 'correct' ? 'ok' : f.status === 'revealed' ? 'rev' : 'no');
    const fix = cell.querySelector('.fix');
    if (f.status !== 'correct') { fix.textContent = table && cell.tagName === 'TD' ? f.short : f.correct_answer; fix.hidden = false; }
  });
  const right = res.fields.filter((f) => f.status === 'correct').length;
  const single = res.fields.length === 1 ? res.fields[0] : null;
  const extra = !ok && !revealed && !single ? `<div class="v-you">${right} of ${res.fields.length} boxes right</div>`
    : !ok && single && single.read_as ? `<div class="v-you">You: ${rich(single.read_as)}</div>` : '';
  const msgs = res.fields.filter((f) => f.status === 'incorrect' && f.message);
  $('fb').innerHTML = `
    ${verdictHTML(ok ? 'ok' : revealed ? 'neutral' : 'no', ok ? 'Correct' : revealed ? 'Answer' : 'Not quite', headlineHTML(res.headline), extra, scroll)}
    ${msgs.length ? `<div class="alert warn"><ul class="msgs">${msgs.map((f) =>
      `<li>${single ? '' : `<b>${esc(f.label)}:</b> `}${rich(f.message)}</li>`).join('')}</ul></div>` : ''}
    ${formulaHTML(res.formula)}
    <details class="face solution" ${ok ? '' : 'open'}><summary>Worked solution</summary>
      <ol>${res.steps.map((s) => `<li>${rich(s)}</li>`).join('')}</ol>
      ${res.notes.map((n) => `<div class="note">${rich(n)}</div>`).join('')}
    </details>
    <button class="btn primary block next" id="nextBtn">${last ? 'See results' : 'Next question'}</button>`;
  $('nextBtn').onclick = problemNext;
  if (scroll) scrollToEl($('fb'));
  $('nextBtn').focus({ preventScroll: true });
}

/* The optional formula box: reported after checking, never scored. */
function formulaHTML(fr) {
  if (!fr) return '';
  const cell = app.querySelector('[data-cell="__formula"]');
  const right = `<span class="mono">${esc(fr.correct_formula)}</span>`;
  if (fr.status === 'correct') {
    if (cell) cell.classList.add('ok');
    return `<div class="alert ok-note">${lamp('go')}<span>Formula used: <span class="mono">${esc(fr.read_as)}</span> is right.
      ${fr.reminder ? esc(fr.reminder) : ''} (Not scored.)</span></div>`;
  }
  if (fr.status === 'blank' || fr.status === 'revealed') return `<p class="help">Step 1 formula: ${right}</p>`;
  if (cell) cell.classList.add('no');
  return `<div class="alert warn">Formula used: ${fr.read_as ? `<span class="mono">${esc(fr.read_as)}</span> isn't it. ` : ''}${
    fr.message ? esc(fr.message) + ' ' : ''}The step 1 formula is ${right}. (Not scored.)</div>`;
}

function problemNext() {
  const r = PS.run;
  if (!r || busy) return;
  if (r.idx >= r.questions.length - 1) return problemFinish();
  r.idx += 1;
  r.answered = false;
  r.feedback = null;
  problemView();
  window.scrollTo(0, 0);
}

function problemFinish() {
  const r = PS.run;
  PS.run = null;
  if (!r.results.length) return go(`#/${r.module}`, true);
  PS.lastRun = r;
  delete needleMemory['problem-result'];   // every result swings up from zero
  go('#/problem-results', true);
}

/* ------------------------------------------------------ results & review */

async function problemResultsView(token) {
  const r = PS.lastRun;
  if (!r) return go('#/', true);
  const sheet = await getSheet(r.module);
  if (token !== renderToken) return;
  const m = PS.mods[r.module];
  const n = r.results.length;
  const correct = r.results.filter((x) => x.ok).length;
  const missed = r.results.filter((x) => !x.ok);
  const skipped = r.questions.length - n;
  app.innerHTML = `${rail(`#/${esc(r.module)}`, r.title)}
    <section class="score">
      <div class="bezel">${meterSVG({ key: 'problem-result', value: correct, max: n, legend: 'CORRECT',
        tag: `LEVEL ${r.level.id}`, readout: `${correct} OF ${n}`, label: `${correct} of ${n} correct` })}</div>
      <div><div class="label">Level ${esc(r.level.id)} · ${esc(r.level.title)}${MODE_TAGS[r.mode] ? ` · ${MODE_TAGS[r.mode]}` : ''}</div>
        <div class="big">${correct}/${n}</div>
        <div class="sub">${pct(correct, n)} correct${skipped ? ` · ${skipped} not answered` : ''}</div></div>
    </section>
    ${missed.length ? `<section class="face list-card"><h2 class="label">Missed this level · ${missed.length}</h2>
      <ul class="rows two">${missed.map((x) => `<li><span class="id">${lamp(x.revealed ? 'amber' : 'stop')}</span>
        <div>${esc(x.desc)}<div class="v-you">${x.revealed ? 'Showed the answer' : `Wrong: ${esc(x.wrong.join(', '))}`}
          · <span class="mono">${rich(x.headline)}</span></div></div></li>`).join('')}</ul></section>`
      : `<p class="good">${lamp('go', 'strike')}No misses. Nice work.</p>`}
    <div class="stack">
      <button class="btn primary block" id="againBtn">${r.mode === 'custom' ? 'Back to your table' : `Run Level ${esc(r.level.id)} again`}</button>
      <a class="btn block" href="#/${esc(r.module)}">All levels</a>
    </div>
    ${sessionSummaryHTML(m)}
    ${sheetHTML(sheet)}`;
  $('againBtn').onclick = () => (r.mode === 'custom' ? go(`#/${r.module}`) : startProblems(m.detail, r.level.id, r.mode));
  animateInstruments(app);
}

async function problemSummaryView(mid, token) {
  const c = await getChapter(mid);
  if (c.type !== 'problems') return go('#/', true);
  const sheet = await getSheet(mid);
  if (token !== renderToken) return;
  const m = pmod(c);
  app.innerHTML = `${rail(`#/${esc(mid)}`, c.title)}
    <header class="page-head"><div class="label">Session summary</div><h1>${esc(c.title)}</h1></header>
    ${sessionSummaryHTML(m)}
    ${sheetHTML(sheet)}
    <div class="stack">
      <a class="btn primary block" href="#/${esc(mid)}">Back to levels</a>
      <button class="btn block" id="clearBtn">Clear this session's stats</button>
    </div>`;
  $('clearBtn').onclick = () => {
    if (!confirm('Clear all stats for this session?')) return;
    m.stats = {};
    m.missed = {};
    go(`#/${mid}`);
  };
}

function sessionSummaryHTML(m) {
  const order = m.detail.levels.map((lv) => lv.id);
  const misses = Object.values(m.missed).sort((a, b) => order.indexOf(a.level) - order.indexOf(b.level));
  return `
    <section class="face list-card spaced"><h2 class="label">This session · accuracy per level</h2>
      <ul class="rows">${m.detail.levels.map((lv) => {
        const s = m.stats[lv.id];
        return `<li><span class="id">${esc(lv.id)}</span><span class="txt">${esc(lv.title)}</span>
          <span class="stat"><span>${s ? `${pct(s.correct, s.answers)}<small>${s.correct} of ${plural(s.answers, 'question')}</small>`
            : '<small>not tried</small>'}</span></span></li>`;
      }).join('')}</ul></section>
    ${misses.length ? `<section class="face list-card spaced"><h2 class="label">Question types you missed</h2>
      <ul class="rows two">${misses.map((x) => `<li><span class="id">${esc(x.level)}</span>
        <div>${esc(x.label)}<div class="v-you">missed ${x.count}×${x.fixed ? ' · then got it right' : ''}</div></div></li>`).join('')}
      </ul></section>` : ''}`;
}

/* The formula sheet: review screens only. */
function sheetHTML(sheet) {
  return `<h2 class="label sheet-head">Formulas</h2><div class="sheet">${sheet.map((sec) => `<section class="face">
    <h2 class="label">${esc(sec.title)}</h2>${sec.items.map((f) => `<div class="f"><div class="f-name">${esc(f.name)}</div>
      <div class="f-eq">${rich(f.formula)}</div>${f.note ? `<div class="f-note">${rich(f.note)}</div>` : ''}</div>`).join('')}
  </section>`).join('')}</div>`;
}
