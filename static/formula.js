'use strict';
/* Formula-drill modules (type "formula"), e.g. the Ohm's Law Wheel.
   Loaded before app.js and uses its helpers at call time (app, $, esc, rich, api, go, pct, plural,
   showErr, lockInputs, insertAtCursor, getChapter, rail, verdictHTML, markTick, scrollToEl, busy,
   renderToken) and the instruments in instruments.js (ringSVG, meterSVG, scaleHTML, lamp).
   Nothing here is saved: stats live in memory and reset when the page closes.
   Routes: #/<module> (levels) · #/drill · #/drill-results · #/blank · #/wheel-summary/<module>
   The filled-in wheel is only drawn on results/summary screens, never during questions. */

const FS = { mods: {}, wheels: {}, run: null, lastRun: null, blank: null };
const FORMULA_KEYS = [['V', 'V'], ['I', 'I'], ['R', 'R'], ['P', 'P'], ['√(', '√('], ['²', '²'],
                      ['×', '×'], ['/', '/'], ['(', '('], [')', ')']];
const FORMULA_ROUTES = {
  drill: () => drillView(),
  'drill-results': (arg, token) => runResultsView(token),
  blank: () => blankView(),
  'wheel-summary': (arg, token) => wheelSummaryView(decodeURIComponent(arg || ''), token),
};

/* in-memory session stats, per module */
function fmod(c) {
  return (FS.mods[c.id] ||= { detail: c, stats: {}, missed: {}, blanks: [], right: {} });
}
function levelStats(m, lv) {
  const s = m.stats[lv.id] || {};
  const vals = Object.values(s);
  return {
    answers: vals.reduce((a, v) => a + v.attempts, 0),
    correct: vals.reduce((a, v) => a + v.correct, 0),
    mastered: lv.keys.filter((k) => s[k] && s[k].last).length,
  };
}
function bestBlank(m) {
  return m.blanks.reduce((b, x) => (!b || x.score > b.score || (x.score === b.score && x.ms < b.ms) ? x : b), null);
}
function noteMiss(m, level, key, formula) {
  const miss = (m.missed[`${level.id}|${key}`] ||= { level, formula, count: 0, fixed: false });
  miss.count += 1;
  miss.fixed = false;
}
function mmss(ms) {
  const s = Math.round(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}
async function getWheel(mid) {
  return (FS.wheels[mid] ||= await api(`/api/formula/${encodeURIComponent(mid)}/wheel`));
}
function keyButtons(list) {
  return list.map(([label, ins]) => `<button type="button" class="key" data-ins="${esc(ins)}">${esc(label)}</button>`).join('');
}
function bindKeys(target) {
  document.querySelectorAll('.key').forEach((b) => {
    b.addEventListener('pointerdown', (e) => e.preventDefault());   // keep the phone keyboard open
    b.addEventListener('click', () => { const el = target(); if (el) insertAtCursor(el, b.dataset.ins); });
  });
}

/* The ring: one lamp per formula, lit once you've got that formula right this session. */
function ringFor(c, m) {
  const lit = {};
  Object.keys(m ? m.right : {}).forEach((display) => {
    const v = display.split(' = ')[0];
    lit[v] = (lit[v] || 0) + 1;
  });
  const n = Object.values(lit).reduce((a, b) => a + b, 0);
  return `<div class="bezel">${ringSVG({ quadrants: c.quadrants, lit, tag: `${c.badge} DRILL`, readout: `${n} OF ${c.question_count}`,
    legend: ['RIGHT THIS', 'SESSION'], label: `${n} of ${c.question_count} formulas right this session` })}</div>`;
}

/* ------------------------------------------------------------ home card */

function formulaCard(c) {
  const m = FS.mods[c.id];
  const started = m && (Object.keys(m.right).length || m.blanks.length || Object.keys(m.stats).length);
  return `<a class="bay" href="#/${esc(c.id)}">${ringFor(c, m)}
    <div class="bay-body"><div class="label">Formula drill</div>
      <h2 class="bay-title">${esc(c.title)}</h2>
      <p class="bay-meta">${esc(c.subtitle)}</p>
      <span class="bay-go">${started ? 'Keep drilling' : 'Start drilling'}</span></div></a>`;
}

/* ---------------------------------------------------------- module page */

function formulaModuleView(c) {
  const m = fmod(c);
  const best = bestBlank(m);
  const tried = c.levels.some((lv) => levelStats(m, lv).answers) || m.blanks.length;
  app.innerHTML = `${rail('#/', 'Chapters')}
    <header class="page-head"><div class="label">Formula drill</div><h1>${esc(c.title)}</h1>
      <p class="lede">${esc(c.intro)}</p></header>
    <div class="mod-grid">
      ${ringFor(c, m)}
      <div>
        <div class="levels">${c.levels.map((lv) => {
          const st = levelStats(m, lv);
          return `<button class="face level level-btn" data-level="${lv.id}">
            <span class="bubble" aria-hidden="true"><b>L</b><i>${lv.id}</i></span>
            <span class="lvl-body"><span class="lvl-title">Level ${lv.id} · ${esc(lv.title)}</span>
              <span class="lvl-desc">${esc(lv.desc)}</span>
              <span class="lvl-stat"><span class="leds" aria-hidden="true">${lv.keys.map((k, i) =>
                `<i class="${i < st.mastered ? 'on' : ''}"></i>`).join('')}</span>
                <span>${st.mastered}/${lv.keys.length} mastered this session${st.answers
                  ? ` · ${pct(st.correct, st.answers)} of ${plural(st.answers, 'answer')}` : ''}</span></span></span>
            <span class="chev" aria-hidden="true"></span></button>`;
        }).join('')}
          <button class="face level" id="blankBtn">
            <span class="bubble" aria-hidden="true"><b>ALL</b><i>${c.question_count}</i></span>
            <span class="lvl-body"><span class="lvl-title">Blank wheel</span>
              <span class="lvl-desc">Fill in all ${c.question_count} formulas from memory, timed.</span>
              ${best ? `<span class="lvl-stat">Best this session: ${best.score}/${best.total} in ${mmss(best.ms)}</span>` : ''}</span>
            <span class="chev" aria-hidden="true"></span></button>
        </div>
        <div id="startErr" class="alert bad" hidden></div>
        ${tried ? `<a class="btn block spaced" href="#/wheel-summary/${esc(c.id)}">Session summary</a>` : ''}
        <p class="fine">Nothing is saved. Stats reset when you close or reload this page.</p>
      </div>
    </div>`;
  document.querySelectorAll('.level-btn').forEach((b) => { b.onclick = () => startRun(c, +b.dataset.level); });
  $('blankBtn').onclick = () => startBlank(c);
  animateInstruments(app);
}

/* ---------------------------------------------------------------- drill */

async function startRun(c, levelId) {
  const level = c.levels.find((l) => l.id === levelId);
  try {
    const r = await api('/api/formula/session', { module: c.id, level: level.id });
    FS.run = { module: c.id, title: c.title, level, current: r.questions[0], queue: r.questions.slice(1),
               total: r.questions.length, results: [], requeued: {}, answered: false, feedback: null };
    go('#/drill');
  } catch (e) {
    const el = $('startErr');
    if (el) { el.textContent = e.message; el.hidden = false; } else alert(e.message);
  }
}

function drillView() {
  const r = FS.run;
  if (!r) return go('#/', true);
  const q = r.current;
  const left = r.queue.length + (r.answered ? 0 : 1);
  const done = r.results.length;
  const placeholder = q.numeric ? `Answer in ${q.unit}` : `${q.target} = …`;
  app.innerHTML = `<div class="quiz">
    <div class="quizbar">
      <button class="icon-btn" id="quitBtn" aria-label="End level" title="End level">✕</button>
      ${scaleHTML(r.results.map((x) => (x.ok ? 'ok' : x.revealed ? 'rev' : 'no')), done + left, `${left} left`)}
      <span class="qcount">${left} left</span>
    </div>
    <article class="face qcard">
      <div class="label">Level ${r.level.id} · ${esc(r.level.title)}</div>
      <p class="qtext">${rich(q.prompt)}</p>
      <div class="qtags">${q.numeric ? 'Unit optional · 2.5k = 2.5e3' : 'Type a formula, like V/R or sqrt(P/R)'}${q.repeat ? ' · missed earlier' : ''}</div>
      <form id="ansForm" autocomplete="off">
        <div class="ansrow">
          <input id="ans" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"
                 enterkeyhint="done" aria-label="Your answer" placeholder="${esc(placeholder)}">
          <button class="btn primary" id="checkBtn" type="submit">Check</button>
        </div>
        <div class="keys">${keyButtons(q.numeric
          ? [['×10^', 'x10^'], ['µ', 'µ'], ['m', 'm'], ['k', 'k'], ['M', 'M'], [q.unit, q.unit]] : FORMULA_KEYS)}</div>
      </form>
      <div id="err" class="alert bad" hidden></div>
      <div class="links"><button class="link" id="hintBtn" type="button">Hint</button>
        <button class="link" id="giveBtn" type="button">Show answer</button></div>
      <div id="hint" class="hint" hidden><b>Hint:</b> ${rich(q.hint)}</div>
    </article>
    <div id="fb" aria-live="polite"></div>
  </div>`;

  const input = $('ans');
  $('ansForm').onsubmit = (e) => { e.preventDefault(); drillSubmit(); };
  $('hintBtn').onclick = () => { $('hint').hidden = !$('hint').hidden; };
  $('giveBtn').onclick = drillGiveUp;
  $('quitBtn').onclick = () => { if (!r.results.length || confirm('End this level and see your results?')) drillFinish(); };
  bindKeys(() => input);
  if (r.answered && r.feedback) {
    input.value = r.feedback.raw;
    lockInputs();
    drillFeedback(r.feedback.res, false);
  } else {
    input.focus();
  }
}

async function drillSubmit() {
  const r = FS.run;
  if (!r || r.answered || busy) return;
  const raw = $('ans').value.trim();
  if (!raw) return showErr('Type an answer first, or tap Show answer.');
  $('err').hidden = true;
  busy = true;
  $('checkBtn').disabled = true;
  try {
    const q = r.current;
    const res = await api('/api/formula/check', { module: r.module, level: r.level.id, key: q.key, params: q.params, answer: raw });
    if (res.status === 'unparsed') return showErr(res.message);   // not graded: say what couldn't be read
    drillRecord(res, raw);
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
    if (FS.run === r && !r.answered && $('checkBtn')) $('checkBtn').disabled = false;
  }
}

async function drillGiveUp() {
  const r = FS.run;
  if (!r || r.answered || busy) return;
  busy = true;
  try {
    const q = r.current;
    drillRecord(await api('/api/formula/reveal', { module: r.module, level: r.level.id, key: q.key, params: q.params }), '');
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
  }
}

function requeue(r, q) {
  const n = r.requeued[q.key] || 0;
  if (n >= 3) return false;
  r.requeued[q.key] = n + 1;
  r.queue.splice(Math.min(2, r.queue.length), 0, { ...q, repeat: true, fresh: q.numeric });   // back after 2 others
  return true;
}

function drillRecord(res, raw) {
  const r = FS.run;
  const q = r.current;
  const m = FS.mods[r.module];
  const ok = res.status === 'correct';
  const revealed = res.status === 'revealed';
  const s = ((m.stats[r.level.id] ||= {})[q.key] ||= { attempts: 0, correct: 0, last: null });
  s.attempts += 1;
  s.correct += ok ? 1 : 0;
  s.last = ok;
  let requeued = false;
  if (!ok) {
    noteMiss(m, r.level, q.key, res.correct_formula);
    requeued = requeue(r, q);
  } else {
    m.right[res.correct_formula] = true;
    if (m.missed[`${r.level.id}|${q.key}`]) m.missed[`${r.level.id}|${q.key}`].fixed = true;
  }
  r.results.push({ key: q.key, prompt: q.prompt, ok, revealed, first: !q.repeat, formula: res.correct_formula });
  r.answered = true;
  r.feedback = { res, raw, requeued };
  lockInputs();
  markTick(r.results.length - 1, ok ? 'ok' : revealed ? 'rev' : 'no', r.results.length);
  drillFeedback(res, true);
}

function drillFeedback(res, scroll) {
  const r = FS.run;
  const ok = res.status === 'correct';
  const revealed = res.status === 'revealed';
  const numeric = r.current.numeric;
  const title = ok ? 'Correct' : revealed ? 'Answer' : 'Not quite';
  const extra = (numeric ? `<div class="v-you mono">${esc(res.correct_formula)}</div>` : '') +
                (!ok && res.read_as ? `<div class="v-you">You: ${rich(res.read_as)}</div>` : '');
  $('fb').innerHTML = `
    ${verdictHTML(ok ? 'ok' : revealed ? 'neutral' : 'no', title, rich(res.correct_answer), extra, scroll)}
    ${res.reminder ? `<div class="alert warn">${esc(res.reminder)}</div>` : ''}
    ${res.message ? `<div class="alert warn">${rich(res.message)}</div>` : ''}
    <details class="face solution" ${ok ? '' : 'open'}><summary>${numeric ? 'Worked solution' : 'Derivation'}</summary>
      <ol>${res.steps.map((s) => `<li>${rich(s)}</li>`).join('')}</ol></details>
    ${r.feedback.requeued ? '<p class="help spaced">This one comes back in a couple of questions.</p>' : ''}
    <button class="btn primary block next" id="nextBtn">${r.queue.length ? 'Next question' : 'See results'}</button>`;
  $('nextBtn').onclick = drillNext;
  if (scroll) scrollToEl($('fb'));
  $('nextBtn').focus({ preventScroll: true });
}

async function drillNext() {
  const r = FS.run;
  if (!r || busy) return;
  if (!r.queue.length) return drillFinish();
  busy = true;
  try {
    let q = r.queue.shift();
    if (q.fresh) {                     // a missed numeric question comes back with new numbers
      try {
        const fresh = await api('/api/formula/question', { module: r.module, level: r.level.id, key: q.key });
        q = { ...fresh.question, repeat: true };
      } catch (e) { /* keep the old numbers */ }
    }
    r.current = q;
    r.answered = false;
    r.feedback = null;
  } finally {
    busy = false;
  }
  drillView();
  window.scrollTo(0, 0);
}

function drillFinish() {
  const r = FS.run;
  FS.run = null;
  if (!r.results.length) return go(`#/${r.module}`, true);
  FS.lastRun = r;
  delete needleMemory['drill-result'];   // every result swings up from zero
  go('#/drill-results', true);
}

/* ------------------------------------------------------ results & review */

async function runResultsView(token) {
  const r = FS.lastRun;
  if (!r) return go('#/', true);
  const wheel = await getWheel(r.module);
  if (token !== renderToken) return;
  const m = FS.mods[r.module];
  const firstTry = r.results.filter((x) => x.first && x.ok).length;
  const correct = r.results.filter((x) => x.ok).length;
  const missed = [...new Map(r.results.filter((x) => !x.ok).map((x) => [x.key, x])).values()];
  app.innerHTML = `${rail(`#/${esc(r.module)}`, r.title)}
    <section class="score">
      <div class="bezel">${meterSVG({ key: 'drill-result', value: firstTry, max: r.total, legend: 'FIRST TRY',
        tag: `LEVEL ${r.level.id}`, readout: `${firstTry} OF ${r.total}`, label: `${firstTry} of ${r.total} right first time` })}</div>
      <div><div class="label">Level ${r.level.id} · ${esc(r.level.title)}</div>
        <div class="big">${firstTry}/${r.total}</div>
        <div class="sub">right first time · ${correct} of ${plural(r.results.length, 'answer')} correct</div></div>
    </section>
    ${missed.length ? `<section class="face list-card"><h2 class="label">Missed this level · ${missed.length}</h2>
      <ul class="rows two">${missed.map((x) => `<li><span class="id">${lamp('stop')}</span>
        <div>${rich(x.prompt)}<div class="v-you mono">${esc(x.formula)}</div></div></li>`).join('')}</ul></section>`
      : `<p class="good">${lamp('go', 'strike')}No misses. Nice work.</p>`}
    <div class="stack">
      <button class="btn primary block" id="againBtn">Run Level ${r.level.id} again</button>
      <a class="btn block" href="#/${esc(r.module)}">All levels</a>
    </div>
    ${sessionHTML(m, wheel)}`;
  $('againBtn').onclick = () => startRun(m.detail, r.level.id);
  animateInstruments(app);
}

async function wheelSummaryView(mid, token) {
  const c = await getChapter(mid);
  const wheel = await getWheel(mid);
  if (token !== renderToken) return;
  const m = fmod(c);
  app.innerHTML = `${rail(`#/${esc(mid)}`, c.title)}
    <header class="page-head"><div class="label">Session summary</div><h1>${esc(c.title)}</h1></header>
    ${sessionHTML(m, wheel)}
    <div class="stack">
      <a class="btn primary block" href="#/${esc(mid)}">Back to levels</a>
      <button class="btn block" id="clearBtn">Clear this session's stats</button>
    </div>`;
  $('clearBtn').onclick = () => {
    if (!confirm('Clear all stats for this session?')) return;
    delete FS.mods[mid];
    go(`#/${mid}`);
  };
}

function sessionHTML(m, wheel) {
  const best = bestBlank(m);
  const misses = Object.values(m.missed);
  return `
    <section class="face list-card spaced"><h2 class="label">This session · accuracy per level</h2>
      <ul class="rows">${m.detail.levels.map((lv) => {
        const st = levelStats(m, lv);
        return `<li><span class="id">L${lv.id}</span><span class="txt">${esc(lv.title)}</span>
          <span class="stat"><span>${st.answers ? `${pct(st.correct, st.answers)}<small>${st.mastered}/${lv.keys.length} mastered</small>`
            : '<small>not tried</small>'}</span></span></li>`;
      }).join('')}
        <li><span class="id">ALL</span><span class="txt">Blank wheel</span>
          <span class="stat"><span>${best ? `${best.score}/${best.total}<small>best, ${mmss(best.ms)}</small>` : '<small>not tried</small>'}</span></span></li>
      </ul></section>
    ${misses.length ? `<section class="face list-card spaced"><h2 class="label">Formulas you missed</h2>
      <ul class="rows two">${misses.map((x) => `<li><span class="id">${x.level.id === 'W' ? 'ALL' : 'L' + x.level.id}</span>
        <div><span class="mono">${esc(x.formula)}</span><div class="v-you">missed ${x.count}×${x.fixed ? ' · then got it right' : ''}</div></div></li>`).join('')}
      </ul></section>` : ''}
    ${wheelHTML(wheel)}`;
}

function wheelHTML(w) {
  return `<section class="face wheel-card spaced"><h2 class="label">The wheel</h2>
    ${wheelSVG(w)}
    <p class="help center">Base equations: <span class="mono">${w.base.map(esc).join(' · ')}</span></p>
    <div class="wheel-list">${w.quadrants.map((q) => `<div><b>${esc(q.var)}</b>
      <p class="help">${esc(q.label)}, ${esc(q.unit)}</p>
      ${q.formulas.map((f) => `<div class="f-eq">${esc(f.display)}</div>`).join('')}</div>`).join('')}</div></section>`;
}

function wheelSVG(w) {
  const R0 = 52, R1 = 56, R2 = 160, RT = 111;
  const span = 360 / w.quadrants.length;
  let s = '';
  w.quadrants.forEach((q, k) => {
    q.formulas.forEach((f, j) => {
      const a0 = span * k + (span * j) / q.formulas.length, a1 = a0 + span / q.formulas.length;
      const [tx, ty] = polar(0, 0, RT, (a0 + a1) / 2);
      s += `<path class="w-seg ${k % 2 ? 'b' : 'a'}" d="${sectorPath(0, 0, R1, R2, a0, a1)}"/>`;
      s += `<text class="wf" x="${n2(tx)}" y="${n2(ty)}">${esc(f.short.replace(/ × /g, '').replace(/ /g, ''))}</text>`;
    });
    const [lx, ly] = polar(0, 0, R0 * 0.56, span * k + span / 2);
    s += `<path class="w-hub${k % 2 ? ' alt' : ''}" d="${sectorPath(0, 0, 0, R0, span * k, span * (k + 1))}"/>`;
    s += `<text class="wv" x="${n2(lx)}" y="${n2(ly)}">${esc(q.var)}</text>`;
  });
  return `<svg class="wheel" viewBox="-164 -164 328 328" role="img" aria-label="Formula wheel">${s}</svg>`;
}

/* ---------------------------------------------------------- blank wheel */

function startBlank(c) {
  fmod(c);
  FS.blank = { module: c.id, quadrants: c.quadrants, total: c.question_count, start: Date.now(),
               values: {}, result: null, ms: null, timer: null };
  go('#/blank');
}

function blankView() {
  const b = FS.blank;
  if (!b) return go('#/', true);
  app.innerHTML = `<div class="quiz">
    <div class="quizbar">
      <button class="icon-btn" id="quitBtn" aria-label="Leave the blank wheel" title="Leave">✕</button>
      ${scaleHTML([], b.total, 'Formulas filled in', false)}
      <span class="timer" id="timer">${mmss(b.ms ?? Date.now() - b.start)}</span>
    </div>
    <div class="label">Blank wheel</div>
    <p class="help">Fill in all ${b.total} formulas from memory. Any order inside a quadrant.</p>
    <div class="keys sticky">${keyButtons(FORMULA_KEYS)}</div>
    <div class="quads">${b.quadrants.map((q) => `
      <section class="face"><h2 class="label">${esc(q.var)} · ${esc(q.label)}</h2>
        ${Array.from({ length: q.slots }, (_, i) => `
          <div class="slot" id="slot-${esc(q.var)}-${i}">
            <label for="in-${esc(q.var)}-${i}">${esc(q.var)} =</label>
            <input id="in-${esc(q.var)}-${i}" data-q="${esc(q.var)}" data-i="${i}" type="text" autocomplete="off"
                   autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="next">
          </div><div class="slot-msg" id="msg-${esc(q.var)}-${i}"></div>`).join('')}
      </section>`).join('')}</div>
    <div id="err" class="alert bad" hidden></div>
    <button class="btn primary block start" id="blankCheck">Check all ${b.total}</button>
    <div id="blankResult"></div>
  </div>`;

  const inputs = [...document.querySelectorAll('.slot input')];
  const ticks = [...document.querySelectorAll('.scale .t')];
  let last = inputs[0];
  const fill = () => {
    const n = inputs.filter((i) => i.value.trim()).length;
    ticks.forEach((t, i) => t.classList.toggle('fill', i < n));
    document.querySelector('.scale').setAttribute('aria-valuenow', n);
  };
  inputs.forEach((inp, n) => {
    inp.value = (b.values[inp.dataset.q] || [])[+inp.dataset.i] || '';
    inp.addEventListener('focus', () => { last = inp; });
    inp.addEventListener('input', () => {
      (b.values[inp.dataset.q] ||= [])[+inp.dataset.i] = inp.value;
      fill();
    });
    inp.addEventListener('keydown', (e) => {
      if (e.key !== 'Enter') return;
      e.preventDefault();
      (inputs[n + 1] || $('blankCheck')).focus();
    });
  });
  fill();
  bindKeys(() => last);
  $('blankCheck').onclick = blankCheck;
  $('quitBtn').onclick = () => {
    const typed = inputs.some((i) => i.value.trim());
    if (b.result || !typed || confirm('Leave the blank wheel? Your entries will be lost.')) {
      FS.blank = null;
      go(`#/${b.module}`);
    }
  };
  clearInterval(b.timer);
  if (b.result) return renderBlankResult(b, false);
  b.timer = setInterval(() => {
    const el = $('timer');
    if (!el || FS.blank !== b || b.result) return clearInterval(b.timer);
    el.textContent = mmss(Date.now() - b.start);
  }, 500);
  inputs[0].focus();
}

async function blankCheck() {
  const b = FS.blank;
  if (!b || b.result || busy) return;
  const ms = Date.now() - b.start;
  busy = true;
  $('blankCheck').disabled = true;
  try {
    const res = await api('/api/formula/blank', { module: b.module, answers: b.values });
    clearInterval(b.timer);
    b.ms = ms;
    b.result = res;
    const m = FS.mods[b.module];
    m.blanks.push({ score: res.score, total: res.total, ms });
    const wheelLevel = { id: 'W', title: 'Blank wheel' };
    Object.values(res.quadrants).forEach((q) => {
      q.missing.forEach((d) => noteMiss(m, wheelLevel, d, d));
      q.slots.filter((s) => s.status === 'correct').forEach((s) => {
        m.right[s.message] = true;
        if (m.missed[`W|${s.message}`]) m.missed[`W|${s.message}`].fixed = true;
      });
    });
    renderBlankResult(b, true);
  } catch (e) {
    showErr(e.message);
    $('blankCheck').disabled = false;
  } finally {
    busy = false;
  }
}

function renderBlankResult(b, fresh) {
  const res = b.result;
  const m = FS.mods[b.module];
  const lit = {};
  Object.entries(res.quadrants).forEach(([qv, q]) => q.slots.forEach((s, i) => {
    $(`slot-${qv}-${i}`).classList.add(s.status === 'correct' ? 'ok' : 'no');
    $(`msg-${qv}-${i}`).textContent = s.status === 'correct'
      ? `Right: ${s.message}${s.reminder ? ` · ${s.reminder}` : ''}` : s.message;
    if (s.status === 'correct') lit[qv] = (lit[qv] || 0) + 1;
  }));
  document.querySelectorAll('.slot input').forEach((el) => { el.disabled = true; });
  document.querySelector('.keys.sticky').hidden = true;
  $('blankCheck').hidden = true;
  $('timer').textContent = mmss(b.ms);
  const best = bestBlank(m);
  const missing = Object.values(res.quadrants).flatMap((q) => q.missing);
  $('blankResult').innerHTML = `
    <section class="score spaced">
      <div class="bezel">${ringSVG({ quadrants: b.quadrants, lit, tag: 'BLANK WHEEL', readout: `${res.score} OF ${res.total}`,
        legend: ['RIGHT THIS', 'TRY'], label: `${res.score} of ${res.total} formulas right` })}</div>
      <div><div class="label">Blank wheel</div><div class="big">${res.score}/${res.total}</div>
        <div class="sub">in ${mmss(b.ms)}${m.blanks.length > 1 ? ` · best this session ${best.score}/${best.total} in ${mmss(best.ms)}` : ''}</div></div>
    </section>
    ${missing.length ? `<section class="face list-card"><h2 class="label">Missing · ${missing.length}</h2>
      <div class="missing">${missing.map((d) => `<div class="f-eq">${esc(d)}</div>`).join('')}</div></section>`
      : `<p class="good">${lamp('go', 'strike')}All ${res.total}. Nice work.</p>`}
    <div class="stack">
      <button class="btn primary block" id="blankAgain">Try again</button>
      <a class="btn block" href="#/${esc(b.module)}">Back to levels</a>
    </div>
    ${wheelHTML(res.wheel)}`;
  $('blankAgain').onclick = () => startBlank(m.detail);
  if (fresh) {
    animateInstruments($('blankResult'), { powerOn: true });
    scrollToEl($('blankResult'));
  }
}
