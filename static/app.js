'use strict';
/* Instrumentation Nation front end. Plain JS, no build step.
   Routes:  #/   ·   #/<chapter>/<practice|formulas|progress>   ·   #/quiz   ·   #/summary
   Progress is saved in this browser (localStorage), per chapter. The server keeps nothing.
   Meters, lamps, color bands and the progress scale come from instruments.js. */

const app = document.getElementById('app');
const KEYS = { progress: 'inn.progress.v1', prefs: 'inn.prefs.v1', session: 'inn.session.v1' };
const MODES = {
  worksheet: { label: 'Worksheet', help: 'Exact numbers from the sheet.' },
  variations: { label: 'Variations', help: 'Same questions, new numbers.' },
  weak: { label: 'Weak spots', help: 'Your most-missed questions first, with new numbers.' },
};
const TABS = ['practice', 'formulas', 'progress'];
const LOGO = '<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#121920"/>' +
             '<rect x="3" y="3" width="26" height="19" rx="3" fill="#f6f4ec"/>' +
             '<path d="M4 16A17 17 0 0 1 28 16" fill="none" stroke="#17191b" stroke-width="1.8"/>' +
             '<path d="M16 28 24 10.8" stroke="#d42b1e" stroke-width="2.4" stroke-linecap="round"/>' +
             '<rect x="3" y="22" width="26" height="7" fill="#121920"/></svg>';

const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
  del(k) { try { localStorage.removeItem(k); } catch (e) {} },
};
const canSave = (() => {
  try { localStorage.setItem('inn.test', '1'); localStorage.removeItem('inn.test'); return true; } catch (e) { return false; }
})();

let progress = store.get(KEYS.progress);
if (!progress || typeof progress.chapters !== 'object') progress = { chapters: {} };
const prefs = store.get(KEYS.prefs) || {};
let sess = store.get(KEYS.session);    // survives a phone browser reloading the tab
let lastSummary = null;
let busy = false;
let renderToken = 0;
let poweredOn = false;                 // the first home screen of a visit switches the meters on
const cache = { list: null, detail: {} };

/* ----------------------------------------------------------------- helpers */

const $ = (id) => document.getElementById(id);
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function rich(s) { return esc(s).replace(/10\^(-?\d+)/g, '10<sup>$1</sup>'); }
function pct(c, a) { return a ? Math.round((100 * c) / a) + '%' : '–'; }
function plural(n, word) { return `${n} ${word}${n === 1 ? '' : 's'}`; }
function ago(iso) {
  if (!iso) return '';
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return 'just now';
  if (s < 3600) return Math.floor(s / 60) + ' min ago';
  if (s < 86400) return Math.floor(s / 3600) + ' h ago';
  return Math.floor(s / 86400) + ' d ago';
}
function saveSess() { sess ? store.set(KEYS.session, sess) : store.del(KEYS.session); }
function scrollToEl(el) { el.scrollIntoView({ behavior: REDUCED_MOTION.matches ? 'auto' : 'smooth', block: 'start' }); }

async function api(path, body) {
  const opts = body === undefined ? {} :
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
  let r;
  try { r = await fetch(path, opts); } catch (e) {
    throw new Error("Can't reach the server. Check your connection and try again.");
  }
  let data = null;
  try { data = await r.json(); } catch (e) {}
  if (!r.ok) throw new Error((data && data.error) || `Server error (${r.status}).`);
  return data;
}

function rail(href, text) {
  return `<header class="rail">${href ? `<a class="back" href="${href}">${esc(text)}</a>` : '<span></span>'}
    <a class="brand" href="#/" aria-label="Instrumentation Nation home">${LOGO}<span>Instrumentation Nation</span></a></header>`;
}

function loadingView() {
  app.innerHTML = `<div class="loading"><div class="bezel">${miniMeterSVG({ value: 0, max: 1, label: 'Loading', idle: true })}</div>
    <p class="help" id="slow" hidden>Waking up the server. The first load can take up to a minute.</p></div>`;
  setTimeout(() => { const s = $('slow'); if (s) s.hidden = false; }, 2500);
}
async function getChapters() {
  if (!cache.list) { loadingView(); cache.list = await api('/api/chapters'); }
  return cache.list;
}
async function getChapter(cid) {
  if (!cache.detail[cid]) { loadingView(); cache.detail[cid] = await api('/api/chapters/' + encodeURIComponent(cid)); }
  return cache.detail[cid];
}

/* ------------------------------------------------- progress (this browser) */

const EMPTY = { attempts: 0, correct: 0, last_seen: null, last_correct: null };
function chProg(cid) { return (progress.chapters[cid] ||= { templates: {}, sessions: [] }); }
function tStat(cid, tid) { return chProg(cid).templates[tid] || EMPTY; }
function record(cid, tid, ok) {
  const t = chProg(cid).templates;
  const s = (t[tid] ||= { ...EMPTY });
  s.attempts += 1;
  s.correct += ok ? 1 : 0;
  s.last_seen = new Date().toISOString();
  s.last_correct = ok;
  store.set(KEYS.progress, progress);
}
function masteredCount(cid) { return Object.values(chProg(cid).templates).filter((s) => s.last_correct).length; }
function lastSeen(cid) {
  return Object.values(chProg(cid).templates).reduce((a, s) => (s.last_seen && s.last_seen > a ? s.last_seen : a), '');
}

/* ------------------------------------------------------------------ router */

function go(hash, replace) {
  if (location.hash === hash) render();
  else if (replace) { location.replace(hash); }
  else location.hash = hash;
}
window.addEventListener('hashchange', render);

async function render() {
  const token = ++renderToken;
  const [first, second] = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean);
  window.scrollTo(0, 0);
  try {
    if (!first) return await homeView(token);
    if (first === 'quiz') return sess ? quizView() : go('#/', true);
    if (first === 'summary') return lastSummary ? summaryView() : go('#/', true);
    if (Object.hasOwn(FORMULA_ROUTES, first)) return await FORMULA_ROUTES[first](second, token);   // formula.js
    if (Object.hasOwn(PROBLEM_ROUTES, first)) return await PROBLEM_ROUTES[first](second, token);   // problems.js
    return await chapterView(decodeURIComponent(first), TABS.includes(second) ? second : 'practice', token);
  } catch (e) {
    if (token === renderToken) errorView(e.message);
  }
}

function errorView(msg) {
  app.innerHTML = `${rail()}<div class="quiz"><div class="alert bad">${lamp('stop', 'strike')}<span>${esc(msg)}</span></div>
    <div class="stack"><button class="btn primary block" id="retryBtn">Try again</button><a class="btn block" href="#/">Home</a></div></div>`;
  $('retryBtn').onclick = () => { cache.list = null; cache.detail = {}; render(); };
}

/* -------------------------------------------------------------------- home */

function resumeBanner(cid) {
  if (!sess || (cid && sess.chapter !== cid)) return '';
  return `<div class="resume">${lamp('amber', 'blink')}
    <div class="resume-text"><b>Resume ${MODES[sess.mode].label}</b>
      <span>Chapter ${sess.chapterNumber} · question ${sess.idx + 1} of ${sess.questions.length}</span></div>
    <div class="row"><button class="link" id="dropBtn">Discard</button><a class="btn primary" href="#/quiz">Resume</a></div></div>`;
}
function bindResume() {
  const d = $('dropBtn');
  if (d) d.onclick = () => { sess = null; saveSess(); render(); };
}

/* The chapter's mastery meter. The same key everywhere, so the needle carries over between screens. */
function chapterMeter(c, mastered, cls = '') {
  const total = c.question_count;
  return `<div class="bezel ${cls}">${meterSVG({ key: 'ch:' + c.id, value: mastered, max: total, legend: 'MASTERED',
    tag: `CH ${c.number}`, readout: `${mastered} OF ${total}`,
    label: `Chapter ${c.number}: ${mastered} of ${total} questions mastered` })}</div>`;
}

function chapterBay(c) {
  const m = Math.min(masteredCount(c.id), c.question_count);
  const seen = lastSeen(c.id);
  return `<a class="bay" href="#/${esc(c.id)}">${chapterMeter(c, m)}
    <div class="bay-body"><div class="label">Chapter ${c.number} · ${plural(c.part_count, 'part')}</div>
      <h2 class="bay-title">${esc(c.title)}</h2>
      <p class="bay-meta">${c.question_count} questions · ${seen ? `practiced ${ago(seen)}` : 'not started yet'}</p>
      <span class="bay-go">${seen ? 'Keep practicing' : 'Start practicing'}</span></div></a>`;
}

async function homeView(token) {
  const chapters = await getChapters();
  if (token !== renderToken) return;
  app.innerHTML = `
    <header class="hero">
      <h1 class="wordmark"><span>Instrumentation</span> <span>Nation</span></h1>
      <p class="lede">Practice problems with worked solutions for our electronics class.</p>
    </header>
    ${resumeBanner()}
    <section class="bays" aria-label="Study modules">${chapters.map((c) =>
      (c.type === 'formula' ? formulaCard(c) : c.type === 'problems' ? problemCard(c) : chapterBay(c))).join('')}</section>
    <p class="fine">${canSave ? 'Chapter progress is saved in this browser. Formula drills and problem sets reset when you close the page.'
      : "This browser isn't saving progress (private mode?)."}</p>`;
  bindResume();
  animateInstruments(app, { powerOn: !poweredOn });
  poweredOn = true;
  app.querySelectorAll('.bay').forEach((b) => b.addEventListener('pointerenter', () => {
    const g = b.querySelector('[data-needle]');
    if (g) kickNeedle(g);
  }));
}

/* ------------------------------------------------------------ chapter page */

function partList(c) {
  return `<ul class="part-list">${Object.entries(c.parts).map(([n, p]) => {
    const rows = c.templates.filter((t) => t.part === +n);
    const m = rows.filter((t) => tStat(c.id, t.id).last_correct).length;
    return `<li>${band(+n)}<span>Part ${n} · ${esc(p.short)}</span><span class="pm">${m}/${rows.length}</span></li>`;
  }).join('')}</ul>`;
}

async function chapterView(cid, tab, token) {
  const c = await getChapter(cid);
  if (token !== renderToken) return;
  if (c.type === 'formula') return formulaModuleView(c);   // formula.js
  if (c.type === 'problems') return problemModuleView(c);  // problems.js
  const label = (t) => t[0].toUpperCase() + t.slice(1);
  const m = Math.min(masteredCount(c.id), c.question_count);
  app.innerHTML = `${rail('#/', 'Chapters')}
    <div class="ch-grid">
      <header class="page-head"><div class="head-row">
        <div class="head-text"><div class="label">Chapter ${c.number}</div><h1>${esc(c.title)}</h1></div>
        <div class="head-meter"><div class="bezel">${miniMeterSVG({ key: 'mini:' + c.id, value: m, max: c.question_count,
          label: `${m} of ${c.question_count} mastered` })}</div><span>${m}/${c.question_count}</span></div>
      </div></header>
      <aside class="ch-aside">${chapterMeter(c, m)}${partList(c)}</aside>
      <div class="ch-main">
        ${resumeBanner(c.id)}
        <nav class="tabs">${TABS.map((t) => `<a href="#/${esc(c.id)}/${t}" class="${t === tab ? 'on' : ''}"
          ${t === tab ? 'aria-current="page"' : ''}>${label(t)}</a>`).join('')}</nav>
        <div id="tab"></div>
      </div>
    </div>`;
  bindResume();
  ({ practice: practiceTab, formulas: formulasTab, progress: progressTab })[tab](c, $('tab'));
  animateInstruments(app);
}

function prefsFor(c) {
  const all = Object.keys(c.parts).map(Number);
  const p = Object.assign({ mode: 'worksheet', parts: all, count: 'all', shuffle: false }, prefs[c.id] || {});
  p.parts = p.parts.filter((n) => c.parts[n]);
  if (!MODES[p.mode]) p.mode = 'worksheet';
  return p;
}

function practiceTab(c, el) {
  const pf = prefsFor(c);
  const tried = Object.values(chProg(c.id).templates).some((s) => s.attempts);
  const radio = (name, value, on, text) =>
    `<label><input type="radio" name="${name}" value="${value}" ${on ? 'checked' : ''}><span>${text}</span></label>`;
  el.innerHTML = `
    <div class="face form">
      <fieldset class="field"><legend class="label">Mode</legend>
        <div class="seg">${Object.entries(MODES).map(([k, m]) => radio('mode', k, pf.mode === k, m.label)).join('')}</div>
        <p class="help" id="modeHelp"></p></fieldset>
      <fieldset class="field"><legend class="label">Parts</legend>
        <div class="parts">${Object.entries(c.parts).map(([n, p]) => `<label class="pill" title="${esc(p.title)}">
          <input type="checkbox" name="part" value="${n}" ${pf.parts.includes(+n) ? 'checked' : ''}>
          <span>${band(+n)}${n} · ${esc(p.short)}</span></label>`).join('')}</div></fieldset>
      <fieldset class="field"><legend class="label">Questions</legend>
        <div class="count-row"><div class="seg">${['5', '10', '20', 'all'].map((n) =>
          radio('count', n, String(pf.count) === n, n === 'all' ? 'All' : n)).join('')}</div>
          <label class="toggle" id="shuffleWrap"><input type="checkbox" id="shuffle" ${pf.shuffle ? 'checked' : ''}>
            <span class="switch"></span>Shuffle</label>
        </div></fieldset>
      <button class="btn primary block start" id="startBtn"></button>
      <div class="alert bad" id="startErr" hidden></div>
    </div>`;

  const sync = () => {
    pf.mode = el.querySelector('input[name=mode]:checked').value;
    pf.parts = [...el.querySelectorAll('input[name=part]:checked')].map((i) => +i.value);
    pf.count = el.querySelector('input[name=count]:checked').value;
    pf.shuffle = $('shuffle').checked;
    prefs[c.id] = pf;
    store.set(KEYS.prefs, prefs);
    const pool = pf.parts.reduce((a, n) => a + c.parts[n].count, 0);
    const n = pf.count === 'all' ? pool : Math.min(+pf.count, pool);
    $('modeHelp').textContent = pf.mode === 'weak' && !tried ? 'No history yet, so questions are picked evenly.' : MODES[pf.mode].help;
    $('shuffleWrap').hidden = pf.mode === 'weak';
    $('startBtn').textContent = n ? `Start · ${plural(n, 'question')}` : 'Pick at least one part';
    $('startBtn').disabled = !n;
  };
  el.addEventListener('change', sync);
  sync();
  $('startBtn').onclick = () => startSession(c, {
    mode: pf.mode, parts: pf.parts, count: pf.count === 'all' ? 'all' : +pf.count, shuffle: pf.shuffle,
  });
}

function formulasTab(c, el) {
  if (!c.formulas.length) { el.innerHTML = '<p class="help">No formula sheet for this chapter yet.</p>'; return; }
  el.innerHTML = `<div class="sheet">${c.formulas.map((sec) => {
    const part = /^Part (\d+)/.exec(sec.title);
    return `<section class="face"><h2 class="label">${part ? band(+part[1]) : ''}${esc(sec.title)}</h2>
      ${sec.items.map((f) => `<div class="f"><div class="f-name">${esc(f.name)}</div>
        <div class="f-eq">${rich(f.formula)}</div>${f.note ? `<div class="f-note">${rich(f.note)}</div>` : ''}</div>`).join('')}
    </section>`;
  }).join('')}</div>`;
}

function progressTab(c, el) {
  const ts = c.templates.map((t) => ({ ...t, s: tStat(c.id, t.id) }));
  const answered = ts.reduce((a, t) => a + t.s.attempts, 0);
  const correct = ts.reduce((a, t) => a + t.s.correct, 0);
  const mastered = ts.filter((t) => t.s.last_correct).length;
  const missed = ts.filter((t) => t.s.last_correct === false);
  el.innerHTML = `
    ${chapterMeter(c, mastered, 'only-narrow')}
    <div class="readouts">
      <div class="readout"><b>${mastered}/${ts.length}</b><span>Mastered</span></div>
      <div class="readout"><b>${pct(correct, answered)}</b><span>Accuracy</span></div>
      <div class="readout"><b>${answered}</b><span>Answers</span></div>
    </div>
    ${missed.length ? `<button class="btn primary block" id="missBtn">Practice ${plural(missed.length, 'missed question')}</button>` : ''}
    <p class="help legend">Mastered means right on your last try. Saved on this device only.</p>
    ${Object.entries(c.parts).map(([n, p]) => {
      const rows = ts.filter((t) => t.part === +n);
      return `<details class="face part"><summary>${band(+n)}<span>Part ${n} · ${esc(p.short)}</span>
          <span class="pm">${rows.filter((t) => t.s.last_correct).length}/${rows.length} mastered</span></summary>
        <ul class="rows">${rows.map((t) => `
          <li><span class="id">#${t.id}</span><span class="txt">${rich(t.text)}</span>
            <span class="stat">${t.s.attempts
              ? `${lamp(t.s.last_correct ? 'go' : 'stop')}<span>${t.s.correct}/${t.s.attempts}<small>${ago(t.s.last_seen)}</small></span>`
              : '<small>not tried</small>'}</span></li>`).join('')}
        </ul></details>`;
    }).join('')}
    ${answered ? `<p class="reset"><button class="link danger" id="resetBtn">Reset Chapter ${c.number} progress</button></p>` : ''}`;
  if (missed.length) {
    $('missBtn').onclick = () => startSession(c, {
      mode: 'variations', template_ids: missed.map((t) => t.id), count: 'all', shuffle: true,
    });
  }
  if (answered) {
    $('resetBtn').onclick = () => {
      if (!confirm(`Reset your Chapter ${c.number} progress on this device?`)) return;
      delete progress.chapters[c.id];
      store.set(KEYS.progress, progress);
      render();
    };
  }
}

async function startSession(c, opts) {
  const btn = $('startBtn') || $('missBtn') || $('retryNew');
  if (btn) btn.disabled = true;
  try {
    const r = await api('/api/session', { chapter: c.id, ...opts, stats: chProg(c.id).templates });
    sess = { chapter: c.id, chapterNumber: c.number, mode: r.mode, questions: r.questions,
             idx: 0, results: [], answered: false, feedback: null };
    saveSess();
    go('#/quiz');
  } catch (e) {
    const err = $('startErr');
    if (err) { err.textContent = e.message; err.hidden = false; } else alert(e.message);
    if (btn) btn.disabled = false;
  }
}

/* -------------------------------------------------------------------- quiz */

function keys(q) {
  const k = [['×10^', 'x10^'], ['µ', 'µ'], ['n', 'n'], ['m', 'm'], ['k', 'k'], ['M', 'M']];
  if (q.unit !== 'electrons') k.push([q.unit, q.unit]);
  return k;
}

function markTick(i, cls, answered) {
  const t = document.querySelectorAll('.scale .t')[i];
  if (t) t.className = `t ${cls}${(i + 1) % 5 === 0 ? ' maj' : ''}`;
  const sc = document.querySelector('.scale');
  if (sc && answered !== undefined) sc.setAttribute('aria-valuenow', answered);
}
function resultMark(r) { return r.correct ? 'ok' : r.revealed ? 'rev' : 'no'; }

function verdictHTML(kind, title, answer, extra, strike) {
  const color = { ok: 'go', no: 'stop', neutral: 'amber' }[kind];
  return `<section class="face verdict ${kind}">${lamp(color, strike ? 'strike' : '')}
    <div class="v-body"><div class="v-title">${title}</div><div class="v-answer">${answer}</div>${extra}</div></section>`;
}

function quizView() {
  const q = sess.questions[sess.idx];
  const n = sess.questions.length;
  const h = tStat(sess.chapter, q.template_id);
  const placeholder = q.unit === 'electrons' ? 'Number of electrons' : `Answer in ${q.unit}`;
  app.innerHTML = `<div class="quiz">
    <div class="quizbar">
      <button class="icon-btn" id="quitBtn" aria-label="End session" title="End session">✕</button>
      ${scaleHTML(sess.results.map(resultMark), n, `Question ${sess.idx + 1} of ${n}`)}
      <span class="qcount">${sess.idx + 1}/${n}</span>
    </div>
    <article class="face qcard">
      <div class="label">${band(q.part)}Ch ${sess.chapterNumber} · Part ${q.part}: ${esc(q.part_title)}</div>
      <p class="qtext">${rich(q.text)}</p>
      <div class="qtags">#${q.template_id} · ${q.varied ? 'new numbers' : 'worksheet numbers'}${h.attempts ? ` · ${h.correct}/${h.attempts} right before` : ''}</div>
      <form id="ansForm" autocomplete="off">
        <div class="ansrow">
          <input id="ans" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"
                 enterkeyhint="done" aria-label="${esc(placeholder)}" placeholder="${esc(placeholder)}">
          <button class="btn primary" id="checkBtn" type="submit">Check</button>
        </div>
        <div class="keys">${keys(q).map(([label, ins]) =>
          `<button type="button" class="key" data-ins="${esc(ins)}">${esc(label)}</button>`).join('')}</div>
        <p class="formats">Unit optional · 2.5k = 2.5e3 = 2.5 x 10^3</p>
      </form>
      <div id="err" class="alert bad" hidden></div>
      <div class="links"><button class="link" id="hintBtn" type="button">Hint</button>
        <button class="link" id="giveBtn" type="button">Show answer</button></div>
      <div id="hint" class="hint" hidden><b>Formula:</b> ${rich(q.hint)}</div>
    </article>
    <div id="fb" aria-live="polite"></div>
  </div>`;

  const input = $('ans');
  $('ansForm').onsubmit = (e) => { e.preventDefault(); submitAnswer(); };
  $('hintBtn').onclick = () => { $('hint').hidden = !$('hint').hidden; };
  $('giveBtn').onclick = giveUp;
  $('quitBtn').onclick = () => {
    if (sess.results.length === 0 || confirm('End this session and see your results?')) finish();
  };
  document.querySelectorAll('.key').forEach((b) => {
    b.addEventListener('pointerdown', (e) => e.preventDefault());   // keep the phone keyboard open
    b.addEventListener('click', () => insertAtCursor(input, b.dataset.ins));
  });
  if (sess.answered && sess.feedback) {
    input.value = sess.feedback.your || '';
    lockInputs();
    showFeedback(sess.feedback.res, false);
  } else {
    input.focus();
  }
}

function insertAtCursor(input, text) {
  if (input.disabled) return;
  const s = input.selectionStart ?? input.value.length;
  const e = input.selectionEnd ?? s;
  input.value = input.value.slice(0, s) + text + input.value.slice(e);
  input.setSelectionRange(s + text.length, s + text.length);
  input.focus();
}

function showErr(msg) { const e = $('err'); e.textContent = msg; e.hidden = false; }

function lockInputs() {
  ['ans', 'checkBtn', 'giveBtn'].forEach((id) => { $(id).disabled = true; });
  document.querySelectorAll('.key').forEach((b) => { b.disabled = true; });
}

async function submitAnswer() {
  if (sess.answered || busy) return;
  const q = sess.questions[sess.idx];
  const raw = $('ans').value.trim();
  if (!raw) return showErr('Type an answer first, or tap Show answer.');
  $('err').hidden = true;
  busy = true;
  $('checkBtn').disabled = true;
  try {
    const res = await api('/api/check', { chapter: q.chapter, template_id: q.template_id, params: q.params, answer: raw });
    if (res.status === 'unparsed') return showErr(res.message);
    finishQuestion(res, raw);
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
    if (sess && !sess.answered && $('checkBtn')) $('checkBtn').disabled = false;
  }
}

async function giveUp() {
  if (sess.answered || busy) return;
  const q = sess.questions[sess.idx];
  busy = true;
  try {
    finishQuestion(await api('/api/reveal', { chapter: q.chapter, template_id: q.template_id, params: q.params }), '');
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
  }
}

function finishQuestion(res, raw) {
  const q = sess.questions[sess.idx];
  const ok = res.status === 'correct';
  record(sess.chapter, q.template_id, ok);
  sess.answered = true;
  sess.feedback = { res, your: raw };
  sess.results.push({ template_id: q.template_id, part: q.part, text: q.text, correct: ok,
                      revealed: res.status === 'revealed', alternate: !!res.alternate, your: raw,
                      correct_answer: res.correct_answer });
  saveSess();
  lockInputs();
  showFeedback(res, true);
}

function showFeedback(res, scroll) {
  const ok = res.status === 'correct';
  const revealed = res.status === 'revealed';
  const last = sess.idx === sess.questions.length - 1;
  const notes = res.notes || [];
  const title = ok ? (res.alternate ? 'Accepted' : 'Correct') : revealed ? 'Answer' : 'Not quite';
  markTick(sess.idx, resultMark(sess.results[sess.idx] || { correct: ok, revealed }), sess.results.length);
  $('fb').innerHTML = `
    ${verdictHTML(ok ? 'ok' : revealed ? 'neutral' : 'no', title, rich(res.correct_answer),
      !ok && res.read_as ? `<div class="v-you">You: ${rich(res.read_as)}</div>` : '', scroll)}
    ${res.message ? `<div class="alert warn">${rich(res.message)}</div>` : ''}
    <details class="face solution" ${!ok || notes.length ? 'open' : ''}><summary>Worked solution</summary>
      <ol>${res.steps.map((s) => `<li>${rich(s)}</li>`).join('')}</ol>
      ${notes.map((n) => `<div class="note">${rich(n)}</div>`).join('')}
    </details>
    <button class="btn primary block next" id="nextBtn">${last ? 'Finish' : 'Next question'}</button>`;
  $('nextBtn').onclick = next;
  if (scroll) scrollToEl($('fb'));
  $('nextBtn').focus({ preventScroll: true });
}

function next() {
  if (sess.idx >= sess.questions.length - 1) return finish();
  sess.idx += 1;
  sess.answered = false;
  sess.feedback = null;
  saveSess();
  quizView();
  window.scrollTo(0, 0);
}

function finish() {
  const done = sess;
  sess = null;
  saveSess();
  if (!done.results.length) return go(`#/${done.chapter}`, true);
  const p = chProg(done.chapter);
  p.sessions = [...(p.sessions || []), {
    finished: new Date().toISOString(), mode: done.mode,
    answered: done.results.length, correct: done.results.filter((r) => r.correct).length,
  }].slice(-20);
  store.set(KEYS.progress, progress);
  lastSummary = done;
  delete needleMemory.summary;      // every result swings up from zero
  go('#/summary', true);
}

/* ----------------------------------------------------------------- summary */

function summaryView() {
  const d = lastSummary;
  const res = d.results;
  const correct = res.filter((r) => r.correct).length;
  const missed = res.filter((r) => !r.correct);
  const alts = res.filter((r) => r.alternate);
  const skipped = d.questions.length - res.length;
  app.innerHTML = `${rail(`#/${esc(d.chapter)}`, `Chapter ${d.chapterNumber}`)}
    <section class="score">
      <div class="bezel">${meterSVG({ key: 'summary', value: correct, max: res.length, legend: 'CORRECT',
        tag: `CH ${d.chapterNumber}`, readout: `${correct} OF ${res.length}`, label: `${correct} of ${res.length} correct` })}</div>
      <div><div class="label">${MODES[d.mode].label} · Chapter ${d.chapterNumber}</div>
        <div class="big">${correct}/${res.length}</div>
        <div class="sub">${pct(correct, res.length)} correct${skipped ? ` · ${skipped} not answered` : ''}</div></div>
    </section>
    ${missed.length ? `<section class="face list-card"><h2 class="label">Missed · ${missed.length}</h2>
      <ul class="rows two">${missed.map((r) => `<li><span class="id">#${r.template_id}</span><div>${rich(r.text)}
        <div class="v-you">Answer <span class="mono">${rich(r.correct_answer)}</span> · you: ${r.revealed ? 'showed answer'
          : `<span class="mono">${esc(r.your)}</span>`}</div></div></li>`).join('')}
      </ul></section>` : `<p class="good">${lamp('go', 'strike')}No misses. Nice work.</p>`}
    ${alts.length ? `<p class="help">Accepted under the other reading of the wording: ${alts.map((r) => '#' + r.template_id).join(', ')}.
      Check which one your teacher wants.</p>` : ''}
    <div class="stack">
      ${missed.length ? `<button class="btn primary block" id="retrySame">Retry missed · same numbers</button>
        <button class="btn block" id="retryNew">Retry missed · new numbers</button>` : ''}
      <a class="btn block ${missed.length ? '' : 'primary'}" href="#/${esc(d.chapter)}">Back to chapter</a>
    </div>`;
  animateInstruments(app);
  if (!missed.length) return;
  $('retrySame').onclick = () => {
    sess = { chapter: d.chapter, chapterNumber: d.chapterNumber, mode: d.mode, idx: 0, results: [],
             answered: false, feedback: null, questions: d.questions.filter((q, i) => res[i] && !res[i].correct) };
    saveSess();
    go('#/quiz');
  };
  $('retryNew').onclick = () => startSession({ id: d.chapter, number: d.chapterNumber }, {
    mode: 'variations', template_ids: [...new Set(missed.map((r) => r.template_id))], count: 'all', shuffle: true,
  });
}

render();
