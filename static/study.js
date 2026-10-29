'use strict';
/* Study-guide chapters (type "study"), e.g. Geometry, Chapter 2. Loaded after problems.js and before app.js.
   Uses app.js helpers at call time (app, $, esc, rich, api, go, pct, plural, ago, rail, store, canSave, busy,
   renderToken, getChapters, getChapter, verdictHTML, showErr, insertAtCursor, scrollToEl) and instruments.js
   (meterSVG, miniMeterSVG, scaleHTML, lamp, band, animateInstruments).
   Routes:  #/study                                    the study-guide chapters
            #/study/<chapter>[/sections|quiz|cards|progress]
            #/study/<chapter>/<section>[/practice|formulas|cards|textbook]
            #/study/<chapter>/quiz/run   ·   #/study/<chapter>/quiz/results
   Progress (attempts, right answers, last seen, per kind of problem) is saved in this browser only.
   Figures arrive from the server as ready-to-draw primitives (core/figures.py); figureSVG() just draws them. */

const SG_KEYS = { progress: 'inn.study.v1', prefs: 'inn.study.prefs.v1', quiz: 'inn.study.quiz.v1' };
const SG = { prog: null, prefs: null, quiz: undefined, lastQuiz: null, practice: {}, textbook: {}, deck: null };
const CH_TABS = { sections: 'Sections', quiz: 'Quiz', cards: 'Cards', progress: 'Progress' };
const SEC_TABS = { practice: 'Practice', formulas: 'Formulas', cards: 'Cards', textbook: 'Textbook' };
const STUDY_ROUTES = { study: (arg, token) => studyRoute(token) };

/* ------------------------------------------------------- progress (this browser) */

const SG_EMPTY = { attempts: 0, correct: 0, last_seen: null, last_correct: null };
function sgProg() {
  if (!SG.prog) {
    const p = store.get(SG_KEYS.progress);
    SG.prog = p && typeof p.chapters === 'object' ? p : { chapters: {} };
  }
  return SG.prog;
}
function sgCh(cid) { return (sgProg().chapters[cid] ||= { types: {}, quizzes: [] }); }
function sgStat(cid, tid) { return sgCh(cid).types[tid] || SG_EMPTY; }
function sgRecord(cid, tid, ok) {
  const s = (sgCh(cid).types[tid] ||= { ...SG_EMPTY });
  s.attempts += 1;
  s.correct += ok ? 1 : 0;
  s.last_seen = new Date().toISOString();
  s.last_correct = ok;
  store.set(SG_KEYS.progress, sgProg());
}
function sgMastery(cid, tids) {
  const m = tids.filter((t) => sgStat(cid, t).last_correct).length;
  return { m, n: tids.length, pct: tids.length ? Math.round((100 * m) / tids.length) : 0 };
}
function sgLastSeen(cid, tids) {
  return tids.reduce((a, t) => { const s = sgStat(cid, t).last_seen; return s && s > a ? s : a; }, '');
}
function secTypes(sec) { return sec.types.map((t) => t.id); }
function sgPrefs() { return (SG.prefs ||= store.get(SG_KEYS.prefs) || {}); }
function sgSavePrefs() { store.set(SG_KEYS.prefs, sgPrefs()); }
function sgQuiz() { if (SG.quiz === undefined) SG.quiz = store.get(SG_KEYS.quiz); return SG.quiz; }
function sgSaveQuiz() { SG.quiz ? store.set(SG_KEYS.quiz, SG.quiz) : store.del(SG_KEYS.quiz); }
function secBand(c, sid) { return band(c.sections.findIndex((s) => s.id === sid) + 1); }
function multiline(s) { return rich(s).replace(/\n/g, '<br>'); }

/* ------------------------------------------------------------------- figures */

function figureSVG(f) {
  if (!f) return '';
  const body = f.items.map((it) => {
    if (it.t === 'path') return `<path d="${it.d}" class="${it.c}"/>`;
    if (it.t === 'circle') return `<circle cx="${it.x}" cy="${it.y}" r="${it.r}" class="${it.c}"/>`;
    return `<text x="${it.x}" y="${it.y}" class="${it.c}" text-anchor="${it.a}">${esc(it.s)}</text>`;
  }).join('');
  // drawn at its own width (capped by the card), so label text is the same size in every figure
  return `<figure class="sg-fig"><svg viewBox="${f.vb.join(' ')}" width="${Math.round(f.vb[2])}" role="img"
    aria-label="${esc(f.alt)}">${body}</svg></figure>`;
}

/* ------------------------------------------------------------------- router */

async function studyRoute(token) {
  const [, cid, a, b] = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
  if (!cid) return studyLandingView(token);
  const c = await getChapter(cid);
  if (token !== renderToken) return;
  if (c.type !== 'study') return go('#/', true);
  if (a === 'quiz' && b === 'run') return sgQuiz() && sgQuiz().chapter === c.id ? quizRunView(c) : go(`#/study/${c.id}/quiz`, true);
  if (a === 'quiz' && b === 'results') return SG.lastQuiz ? quizResultsView(c) : go(`#/study/${c.id}/quiz`, true);
  const sec = c.sections.find((s) => s.id === a);
  if (sec) return sectionView(c, sec, Object.hasOwn(SEC_TABS, b) ? b : 'practice');
  return chapterPage(c, Object.hasOwn(CH_TABS, a) ? a : 'sections');
}

/* ---------------------------------------------------------- home and landing */

function studyMeter(c, ms, cls = '') {
  return `<div class="bezel ${cls}">${meterSVG({ key: 'st:' + c.id, value: ms.m, max: ms.n, legend: 'MASTERED', tag: c.tag,
    readout: `${ms.m} OF ${ms.n}`, label: `${c.title}: ${ms.m} of ${ms.n} kinds of problem mastered` })}</div>`;
}

function studyCard(c) {
  const ms = sgMastery(c.id, c.type_ids);
  const seen = sgLastSeen(c.id, c.type_ids);
  return `<a class="bay" href="#/study/${esc(c.id)}">${studyMeter(c, ms)}
    <div class="bay-body"><div class="label">${esc(c.kicker)} · ${plural(c.section_count, 'section')}</div>
      <h2 class="bay-title">${esc(c.title)}</h2>
      <p class="bay-meta">${c.type_ids.length} kinds of problem · ${seen ? `practiced ${ago(seen)}` : 'not started yet'}</p>
      <span class="bay-go">${seen ? 'Keep studying' : 'Start studying'}</span></div></a>`;
}

async function studyLandingView(token) {
  const list = (await getChapters()).filter((c) => c.type === 'study');
  if (token !== renderToken) return;
  app.innerHTML = `${rail('#/', 'Home')}
    <header class="page-head"><div class="label">Study guide</div><h1>Study guide</h1>
      <p class="lede">Formula cards, practice with fresh numbers, quizzes and flashcards.</p></header>
    <section class="bays" aria-label="Study-guide chapters">${list.map(studyCard).join('')}</section>
    <p class="fine">${canSave ? 'Progress is saved in this browser only.' : "This browser isn't saving progress (private mode?)."}</p>`;
  animateInstruments(app);
}

/* -------------------------------------------------------------- chapter page */

function sectionList(c) {
  return `<ul class="part-list">${c.sections.map((s, i) => {
    const ms = sgMastery(c.id, secTypes(s));
    return `<li>${band(i + 1)}<a href="#/study/${esc(c.id)}/${esc(s.id)}">${esc(s.id)} · ${esc(s.title)}</a>
      <span class="pm">${ms.m}/${ms.n}</span></li>`;
  }).join('')}</ul>`;
}

function chapterPage(c, tab) {
  const ms = sgMastery(c.id, c.type_ids);
  app.innerHTML = `${rail('#/', 'Chapters')}
    <div class="ch-grid">
      <header class="page-head"><div class="head-row">
        <div class="head-text"><div class="label">${esc(c.kicker)}</div><h1>${esc(c.title)}</h1></div>
        <div class="head-meter"><div class="bezel">${miniMeterSVG({ key: 'stmini:' + c.id, value: ms.m, max: ms.n,
          label: `${ms.m} of ${ms.n} mastered` })}</div><span>${ms.m}/${ms.n}</span></div>
      </div><p class="lede">${esc(c.intro)}</p></header>
      <aside class="ch-aside">${studyMeter(c, ms)}${sectionList(c)}</aside>
      <div class="ch-main">
        <nav class="tabs">${Object.entries(CH_TABS).map(([t, label]) => `<a href="#/study/${esc(c.id)}/${t}"
          class="${t === tab ? 'on' : ''}" ${t === tab ? 'aria-current="page"' : ''}>${label}</a>`).join('')}</nav>
        <div id="tab"></div>
      </div>
    </div>`;
  ({ sections: sectionsTab, quiz: quizTab, cards: chapterCardsTab, progress: studyProgressTab })[tab](c, $('tab'));
  animateInstruments(app);
}

function sectionsTab(c, el) {
  el.innerHTML = `<div class="levels">${c.sections.map((s) => {
    const ms = sgMastery(c.id, secTypes(s));
    const seen = sgLastSeen(c.id, secTypes(s));
    const [ch, n] = s.id.split('.');
    return `<a class="face level sg-sec" href="#/study/${esc(c.id)}/${esc(s.id)}">
      <span class="bubble" aria-hidden="true"><b>${esc(ch)}</b><i>${esc(n || '')}</i></span>
      <span class="lvl-body"><span class="lvl-title">${esc(s.id)} · ${esc(s.title)}</span>
        <span class="lvl-desc">${esc(s.topics)}</span>
        <span class="lvl-stat"><span class="leds" aria-hidden="true">${secTypes(s).map((t) =>
          `<i class="${sgStat(c.id, t).last_correct ? 'on' : ''}"></i>`).join('')}</span>
          <span>${ms.pct}% mastered${seen ? ` · ${ago(seen)}` : ''}</span></span></span>
      <span class="chev" aria-hidden="true"></span></a>`;
  }).join('')}</div>
  <p class="fine">Pick a section for its formula card, practice with fresh numbers and flashcards.
    The Quiz tab mixes sections. ${canSave ? 'Progress is saved in this browser only.' : "This browser isn't saving progress."}</p>`;
}

/* --------------------------------------------------------------- section page */

function sectionView(c, sec, tab) {
  const tabs = Object.keys(SEC_TABS).filter((t) => t !== 'textbook' || (c.textbook && sec.textbook));
  if (!tabs.includes(tab)) tab = 'practice';
  const ms = sgMastery(c.id, secTypes(sec));
  app.innerHTML = `${rail(`#/study/${esc(c.id)}`, c.title)}
    <div class="sg-page">
      <header class="page-head"><div class="head-row">
        <div class="head-text"><div class="label sg-kick">${secBand(c, sec.id)}${esc(c.kicker)} · Section ${esc(sec.id)}</div>
          <h1>${esc(sec.title)}</h1></div>
        <div class="head-meter sg-always"><div class="bezel">${miniMeterSVG({ key: `stsec:${c.id}:${sec.id}`, value: ms.m,
          max: ms.n, label: `${ms.m} of ${ms.n} kinds mastered` })}</div><span>${ms.m}/${ms.n}</span></div>
      </div></header>
      <nav class="tabs">${tabs.map((t) => `<a href="#/study/${esc(c.id)}/${esc(sec.id)}/${t}" class="${t === tab ? 'on' : ''}"
        ${t === tab ? 'aria-current="page"' : ''}>${SEC_TABS[t]}</a>`).join('')}</nav>
      <div id="tab"></div>
    </div>`;
  animateInstruments(app);
  const el = $('tab');
  if (tab === 'formulas') return sgFormulaCard(sec, el);
  if (tab === 'cards') return deckView(el, sec.flashcards.map((f) => ({ ...f, sec: sec.id })), `${c.id}|${sec.id}`);
  if (tab === 'textbook') return textbookTab(c, sec, el);
  return sgPracticeTab(c, sec, el);
}

function sgFormulaCard(sec, el) {
  el.innerHTML = `<div class="sheet">${sec.formulas.map((g) => `<section class="face"><h2 class="label">${esc(g.title)}</h2>
    ${g.items.map((f) => `<div class="f"><div class="f-name">${esc(f.name)}</div><div class="f-eq">${multiline(f.formula)}</div>
      ${f.note ? `<div class="f-note">${rich(f.note)}</div>` : ''}</div>`).join('')}</section>`).join('')}</div>`;
}

/* ------------------------------------------------- one problem: practice and textbook */

function answerForm(q, quiz) {
  return `<form id="ansForm" autocomplete="off">
      <div class="ansrow">
        <input id="ans" type="text" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false"
          enterkeyhint="${quiz ? 'next' : 'done'}" aria-label="${esc(q.answer.placeholder)}" placeholder="${esc(q.answer.placeholder)}">
        <button class="btn primary" id="checkBtn" type="submit">${quiz ? 'Submit' : 'Check'}</button>
      </div>
      <div class="keys">${q.answer.keys.map(([label, ins]) =>
        `<button type="button" class="key" data-ins="${esc(ins)}">${esc(label)}</button>`).join('')}</div>
      <p class="formats">${esc(q.answer.formats)}</p>
    </form>
    <div id="err" class="alert bad" hidden></div>`;
}

function sgBindKeys() {
  const input = $('ans');
  document.querySelectorAll('.key').forEach((b) => {
    b.addEventListener('pointerdown', (e) => e.preventDefault());    // keep the phone keyboard open
    b.addEventListener('click', () => insertAtCursor(input, b.dataset.ins));
  });
}

function qCardHTML(c, q, { quiz = false, tag = '' } = {}) {
  const h = sgStat(c.id, q.type);
  return `<article class="face qcard sg-q">
      <div class="label">${secBand(c, q.section)}${esc(q.section)} · ${esc(q.type_title)}${tag ? ` · ${esc(tag)}` : ''}</div>
      ${figureSVG(q.figure)}
      <p class="qtext">${multiline(q.text)}</p>
      ${quiz ? '' : `<div class="qtags">${h.attempts ? `${h.correct}/${h.attempts} right before on this kind` : 'New kind of problem for you'}</div>`}
      ${answerForm(q, quiz)}
      ${quiz ? '' : `<div class="links"><button class="link" id="hintBtn" type="button">Hint</button>
        <button class="link" id="stepsBtn" type="button">Show steps</button></div>
        <div id="hint" class="hint" hidden><b>Hint:</b> ${rich(q.hint || 'No hint for this one.')}</div>`}
    </article>`;
}

/* `st` holds one problem: { q, recorded, res, your }. `opts.next` loads the next one. */
function sgProblemView(c, el, st, opts) {
  el.innerHTML = `${opts.head || ''}${qCardHTML(c, st.q, { tag: opts.tag })}
    <div id="fb" aria-live="polite"></div>
    <button class="btn block next" id="nextBtn">${esc(opts.nextLabel || 'Next problem')}</button>`;
  const input = $('ans');
  $('ansForm').onsubmit = (e) => { e.preventDefault(); sgProblemCheck(c, st); };
  $('hintBtn').onclick = () => { $('hint').hidden = !$('hint').hidden; };
  $('stepsBtn').onclick = () => sgProblemSteps(c, st);
  $('nextBtn').onclick = () => opts.next();
  sgBindKeys();
  if (st.res) {
    input.value = st.your || '';
    sgProblemFeedback(st, false);
  } else if (opts.focus !== false) {
    input.focus({ preventScroll: true });
  }
}

async function sgProblemCheck(c, st) {
  if (busy || (st.res && st.res.status !== 'incorrect')) return;
  const raw = $('ans').value.trim();
  if (!raw) return showErr('Type an answer first, or tap Show steps.');
  $('err').hidden = true;
  busy = true;
  $('checkBtn').disabled = true;
  try {
    const res = await api('/api/study/check', { chapter: c.id, type: st.q.type, params: st.q.params, answer: raw });
    if (res.status === 'unparsed') return showErr(res.message);
    if (!st.recorded) {
      sgRecord(c.id, st.q.type, res.status === 'correct');
      st.recorded = true;
      st.firstMiss = res.status !== 'correct';
    }
    st.res = res;
    st.your = raw;
    sgProblemFeedback(st, true);
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
    if ($('checkBtn') && !(st.res && st.res.status !== 'incorrect')) $('checkBtn').disabled = false;
  }
}

async function sgProblemSteps(c, st) {
  if (st.res && st.res.status !== 'incorrect') {
    const d = document.querySelector('#fb details.solution');
    if (d) { d.open = true; scrollToEl(d); }
    return;
  }
  if (busy) return;
  busy = true;
  try {
    const res = await api('/api/study/reveal', { chapter: c.id, type: st.q.type, params: st.q.params });
    if (!st.recorded) { sgRecord(c.id, st.q.type, false); st.recorded = true; }
    st.res = res;
    st.your = $('ans').value.trim();
    sgProblemFeedback(st, true);
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
  }
}

function solutionHTML(res, open) {
  return `<details class="face solution" ${open ? 'open' : ''}><summary>Worked steps</summary>
    <ol>${res.steps.map((s) => `<li>${rich(s)}</li>`).join('')}</ol>
    ${(res.notes || []).map((n) => `<div class="note">${rich(n)}</div>`).join('')}</details>`;
}

function answerLine(res) {
  return res.unrounded ? `<div class="v-you">Unrounded: <span class="mono">${rich(res.unrounded)}</span></div>` : '';
}

function sgProblemFeedback(st, scroll) {
  const res = st.res;
  const done = res.status !== 'incorrect';
  ['ans', 'checkBtn'].forEach((id) => { $(id).disabled = done; });
  document.querySelectorAll('.key').forEach((b) => { b.disabled = done; });
  $('stepsBtn').textContent = done ? 'Worked steps' : 'Show steps';
  const you = res.read_as ? `<div class="v-you">You: ${rich(res.read_as)}</div>` : '';
  if (res.status === 'correct') {
    $('fb').innerHTML = verdictHTML('ok', 'Correct', rich(res.answer), answerLine(res) +
      (st.firstMiss ? '<div class="v-you">Counted as a miss in your progress: it took more than one try.</div>' : ''), scroll)
      + solutionHTML(res, false);
  } else if (res.status === 'revealed') {
    $('fb').innerHTML = verdictHTML('neutral', 'Answer', rich(res.answer), answerLine(res), scroll) + solutionHTML(res, true);
  } else {
    $('fb').innerHTML = verdictHTML('no', 'Not quite', `<span class="sg-msg">${rich(res.message || 'Try again.')}</span>`,
      you + '<div class="row sg-retry"><button class="link" id="retryBtn" type="button">Try again</button></div>', scroll);
    $('retryBtn').onclick = () => { $('fb').innerHTML = ''; const i = $('ans'); i.focus(); i.select(); };
  }
  $('nextBtn').classList.toggle('primary', done);
  if (scroll) scrollToEl($('fb'));
  if (done) $('nextBtn').focus({ preventScroll: true });
}

/* Practice: fresh problems from one section, mixed or one kind. */
async function sgPracticeTab(c, sec, el) {
  const key = `${c.id}|${sec.id}`;
  const pf = sgPrefs()[key] || {};
  const typeOk = sec.types.some((t) => t.id === pf.type);
  el.innerHTML = `<div class="sg-pick"><label class="label" for="ptype">Kind of problem</label>
      <select id="ptype" class="sg-select"><option value="">Mixed: every kind in ${esc(sec.id)}</option>
        ${sec.types.map((t) => `<option value="${esc(t.id)}" ${typeOk && t.id === pf.type ? 'selected' : ''}>${esc(t.title)}</option>`).join('')}
      </select></div>
    <div id="pbox"><div class="loading sg-inline"></div></div>`;
  $('ptype').onchange = () => {
    sgPrefs()[key] = { type: $('ptype').value || null };
    sgSavePrefs();
    nextPractice(c, sec, true);
  };
  const st = SG.practice[key];
  if (st && (!typeOk || !pf.type || st.q.type === pf.type)) return showPractice(c, sec, st, false);
  nextPractice(c, sec, false);
}

async function nextPractice(c, sec, focus = true) {
  const key = `${c.id}|${sec.id}`;
  const pf = sgPrefs()[key] || {};
  const type = sec.types.some((t) => t.id === pf.type) ? pf.type : null;
  const prev = SG.practice[key];
  if (busy) return;
  busy = true;
  try {
    const r = await api('/api/study/problem', { chapter: c.id, section: sec.id, type, avoid: prev ? prev.q.type : null });
    SG.practice[key] = { q: r.question, recorded: false, res: null, your: '' };
    if ($('pbox')) showPractice(c, sec, SG.practice[key], focus);
  } catch (e) {
    if ($('pbox')) $('pbox').innerHTML = `<div class="alert bad">${lamp('stop')}<span>${esc(e.message)}</span></div>`;
  } finally {
    busy = false;
  }
}

function showPractice(c, sec, st, focus) {
  sgProblemView(c, $('pbox'), st, { next: () => { nextPractice(c, sec, true); window.scrollTo(0, 0); }, focus });
}

/* Textbook set: the exact exercises, read from the private file when this computer has it. */
async function textbookTab(c, sec, el) {
  const key = `${c.id}|${sec.id}`;
  let tb = SG.textbook[key];
  if (!tb) {
    el.innerHTML = '<div class="loading sg-inline"></div>';
    try {
      const r = await api(`/api/study/${encodeURIComponent(c.id)}/textbook/${encodeURIComponent(sec.id)}`);
      tb = SG.textbook[key] = { items: r.items, idx: 0, states: {} };
    } catch (e) {
      el.innerHTML = `<div class="alert bad">${lamp('stop')}<span>${esc(e.message)}</span></div>`;
      return;
    }
  }
  showTextbook(c, sec, el, tb);
}

function showTextbook(c, sec, el, tb) {
  const item = tb.items[tb.idx];
  const last = tb.idx === tb.items.length - 1;
  const move = (d) => { tb.idx = (tb.idx + d + tb.items.length) % tb.items.length; showTextbook(c, sec, el, tb); window.scrollTo(0, 0); };
  const head = `<div class="sg-tbbar">
      <button class="icon-btn" id="tbPrev" type="button" aria-label="Previous exercise">‹</button>
      <select id="tbPick" class="sg-select" aria-label="Exercise">${tb.items.map((it, i) =>
        `<option value="${i}" ${i === tb.idx ? 'selected' : ''}>${esc(it.label)}${it.pending ? ' · coming soon' : ''}</option>`).join('')}</select>
      <button class="icon-btn" id="tbNext" type="button" aria-label="Next exercise">›</button>
      <span class="qcount">${tb.idx + 1}/${tb.items.length}</span></div>
    <p class="help flush">Textbook set: the book's own exercises. Only on this computer; it never goes online.</p>`;
  if (item.pending) {
    el.innerHTML = `${head}<article class="face qcard sg-q"><div class="label">${esc(item.label)}${item.figure_name ? ` · ${esc(item.figure_name)}` : ''}</div>
      <p class="qtext">${multiline(item.text)}</p>
      <div class="alert warn">Answer coming soon. This one isn't graded yet.</div></article>
      <button class="btn block next primary" id="nextBtn">${last ? 'Back to the first one' : 'Next exercise'}</button>`;
    $('nextBtn').onclick = () => move(1);
  } else {
    const st = (tb.states[tb.idx] ||= { q: item.question, recorded: false, res: null, your: '' });
    sgProblemView(c, el, st, { head, tag: `${item.label}${item.figure_name ? ' · ' + item.figure_name : ''}`,
      next: () => move(1), nextLabel: last ? 'Back to the first one' : 'Next exercise' });
  }
  $('tbPrev').onclick = () => move(-1);
  $('tbNext').onclick = () => move(1);
  $('tbPick').onchange = (e) => { tb.idx = +e.target.value; showTextbook(c, sec, el, tb); };
}

/* ---------------------------------------------------------------------- quiz */

function quizPrefs(c) {
  const p = Object.assign({ sections: c.sections.map((s) => s.id), count: 10 }, sgPrefs()[c.id] || {});
  p.sections = p.sections.filter((s) => c.sections.some((x) => x.id === s));
  if (![5, 10, 20].includes(p.count)) p.count = 10;
  return p;
}

function quizTab(c, el) {
  const pf = quizPrefs(c);
  const z = sgQuiz();
  const resume = z && z.chapter === c.id ? `<div class="resume">${lamp('amber', 'blink')}
      <div class="resume-text"><b>Quiz in progress</b><span>question ${z.idx + 1} of ${z.questions.length}</span></div>
      <div class="row"><button class="link" id="dropBtn">Discard</button><a class="btn primary" href="#/study/${esc(c.id)}/quiz/run">Resume</a></div></div>` : '';
  el.innerHTML = `${resume}<div class="face form">
      <fieldset class="field"><legend class="label">Sections</legend>
        <div class="parts">${c.sections.map((s, i) => `<label class="pill"><input type="checkbox" name="qsec" value="${esc(s.id)}"
          ${pf.sections.includes(s.id) ? 'checked' : ''}><span>${band(i + 1)}${esc(s.id)} · ${esc(s.title)}</span></label>`).join('')}</div></fieldset>
      <fieldset class="field"><legend class="label">Questions</legend>
        <div class="seg">${[5, 10, 20].map((n) => `<label><input type="radio" name="qcount" value="${n}" ${pf.count === n ? 'checked' : ''}>
          <span>${n}</span></label>`).join('')}</div></fieldset>
      <p class="help">No hints or steps during a quiz. You get your score and every worked answer at the end.</p>
      <button class="btn primary block start" id="quizGo"></button>
      <div class="alert bad" id="startErr" hidden></div>
    </div>`;
  const sync = () => {
    pf.sections = [...el.querySelectorAll('input[name=qsec]:checked')].map((i) => i.value);
    pf.count = +el.querySelector('input[name=qcount]:checked').value;
    sgPrefs()[c.id] = pf;
    sgSavePrefs();
    $('quizGo').textContent = pf.sections.length ? `Start quiz · ${pf.count} questions` : 'Pick at least one section';
    $('quizGo').disabled = !pf.sections.length;
  };
  el.addEventListener('change', sync);
  sync();
  $('quizGo').onclick = () => startQuiz(c, pf.sections, pf.count);
  if ($('dropBtn')) $('dropBtn').onclick = () => { SG.quiz = null; sgSaveQuiz(); quizTab(c, el); };
}

async function startQuiz(c, sections, count, questions) {
  if (busy) return;
  busy = true;
  try {
    const qs = questions || (await api('/api/study/quiz', { chapter: c.id, sections, count })).questions;
    SG.quiz = { chapter: c.id, sections, questions: qs, idx: 0, results: [] };
    sgSaveQuiz();
    go(`#/study/${c.id}/quiz/run`);
  } catch (e) {
    const err = $('startErr');
    if (err) { err.textContent = e.message; err.hidden = false; } else alert(e.message);
  } finally {
    busy = false;
  }
}

function quizRunView(c) {
  const z = sgQuiz();
  const q = z.questions[z.idx];
  const n = z.questions.length;
  app.innerHTML = `<div class="quiz">
    <div class="quizbar">
      <button class="icon-btn" id="quitBtn" aria-label="End quiz" title="End quiz">✕</button>
      ${scaleHTML(z.results.map(() => 'fill'), n, `Question ${z.idx + 1} of ${n}`)}
      <span class="qcount">${z.idx + 1}/${n}</span>
    </div>
    ${qCardHTML(c, q, { quiz: true })}
    <p class="help center">Answers are marked at the end.</p>
  </div>`;
  sgBindKeys();
  $('ans').focus({ preventScroll: true });
  $('ansForm').onsubmit = (e) => { e.preventDefault(); quizSubmit(c); };
  $('quitBtn').onclick = () => {
    if (!z.results.length) { SG.quiz = null; sgSaveQuiz(); return go(`#/study/${c.id}/quiz`, true); }
    if (confirm('End the quiz now and mark what you answered?')) finishQuiz(c);
  };
}

async function quizSubmit(c) {
  const z = sgQuiz();
  const q = z.questions[z.idx];
  const raw = $('ans').value.trim();
  if (busy) return;
  if (!raw) return showErr('Type an answer first.');
  busy = true;
  $('checkBtn').disabled = true;
  try {
    const res = await api('/api/study/check', { chapter: c.id, type: q.type, params: q.params, answer: raw });
    if (res.status === 'unparsed') return showErr(res.message);
    sgRecord(c.id, q.type, res.status === 'correct');
    z.results.push({ correct: res.status === 'correct', your: raw, res });
    z.idx += 1;
    sgSaveQuiz();
    if (z.idx >= z.questions.length) return finishQuiz(c);
    quizRunView(c);
    window.scrollTo(0, 0);
  } catch (e) {
    showErr(e.message);
  } finally {
    busy = false;
    if ($('checkBtn')) $('checkBtn').disabled = false;
  }
}

function finishQuiz(c) {
  const z = sgQuiz();
  SG.quiz = null;
  sgSaveQuiz();
  const answered = z.results.length;
  const p = sgCh(c.id);
  p.quizzes = [...(p.quizzes || []), { finished: new Date().toISOString(), answered,
    correct: z.results.filter((r) => r.correct).length }].slice(-20);
  store.set(SG_KEYS.progress, sgProg());
  SG.lastQuiz = { ...z, questions: z.questions.slice(0, answered) };
  delete needleMemory['stquiz'];
  go(`#/study/${c.id}/quiz/results`, true);
}

function quizResultsView(c) {
  const z = SG.lastQuiz;
  const res = z.results;
  const correct = res.filter((r) => r.correct).length;
  const missed = res.map((r, i) => ({ r, q: z.questions[i] })).filter((x) => !x.r.correct);
  app.innerHTML = `${rail(`#/study/${esc(c.id)}/quiz`, c.title)}
    <section class="score">
      <div class="bezel">${meterSVG({ key: 'stquiz', value: correct, max: Math.max(res.length, 1), legend: 'CORRECT', tag: c.tag,
        readout: `${correct} OF ${res.length}`, label: `${correct} of ${res.length} correct` })}</div>
      <div><div class="label">Quiz · ${esc(c.title)}</div><div class="big">${correct}/${res.length}</div>
        <div class="sub">${pct(correct, res.length)} correct</div></div>
    </section>
    ${missed.length ? `<h2 class="label sg-h">Missed · ${missed.length}</h2>
      <div class="sg-missed">${missed.map(({ r, q }, i) => `<article class="face sg-miss">
        <div class="label">${secBand(c, q.section)}${esc(q.section)} · ${esc(q.type_title)}</div>
        ${figureSVG(q.figure)}
        <p class="sg-miss-q">${multiline(q.text)}</p>
        <div class="v-you">You: <span class="mono">${esc(r.your)}</span>${r.res.message ? ` · ${rich(r.res.message)}` : ''}</div>
        <div class="sg-miss-a">Answer: <span class="mono">${rich(r.res.answer)}</span></div>
        ${answerLine(r.res)}
        ${solutionHTML(r.res, false)}</article>`).join('')}</div>`
      : `<p class="good">${lamp('go', 'strike')}No misses. Nice work.</p>`}
    <div class="stack">
      ${missed.length ? '<button class="btn primary block" id="retryMissed">Retry missed</button>' : ''}
      <button class="btn block ${missed.length ? '' : 'primary'}" id="newQuiz">New quiz</button>
      <a class="btn block" href="#/study/${esc(c.id)}">Back to ${esc(c.title)}</a>
    </div>`;
  animateInstruments(app);
  if (missed.length) $('retryMissed').onclick = () => startQuiz(c, z.sections, missed.length, missed.map((x) => x.q));
  $('newQuiz').onclick = () => startQuiz(c, z.sections, quizPrefs(c).count);
}

/* ---------------------------------------------------------------- flashcards */

function chapterCardsTab(c, el) {
  const key = `${c.id}|cards`;
  const chosen = (sgPrefs()[key] || {}).sections || c.sections.map((s) => s.id);
  el.innerHTML = `<div class="parts sg-filter">${c.sections.map((s, i) => `<label class="pill"><input type="checkbox" name="csec"
      value="${esc(s.id)}" ${chosen.includes(s.id) ? 'checked' : ''}><span>${band(i + 1)}${esc(s.id)}</span></label>`).join('')}</div>
    <div id="deckBox"></div>`;
  const build = () => {
    const ids = [...el.querySelectorAll('input[name=csec]:checked')].map((i) => i.value);
    sgPrefs()[key] = { sections: ids };
    sgSavePrefs();
    const cards = c.sections.filter((s) => ids.includes(s.id)).flatMap((s) => s.flashcards.map((f) => ({ ...f, sec: s.id })));
    deckView($('deckBox'), cards, `${c.id}|${ids.join(',')}`);
  };
  el.querySelectorAll('input[name=csec]').forEach((i) => i.addEventListener('change', build));
  build();
}

function deckView(el, cards, key) {
  if (!cards.length) { el.innerHTML = '<p class="help">Pick at least one section.</p>'; SG.deck = null; return; }
  if (!SG.deck || SG.deck.key !== key) {
    const shuffle = !!sgPrefs().shuffleCards;
    SG.deck = { key, base: cards, cards: shuffle ? shuffled(cards) : cards, idx: 0, flipped: false, shuffle };
  }
  SG.deck.el = el;
  drawDeck();
}

function shuffled(a) {
  const b = [...a];
  for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; }
  return b;
}

function drawDeck() {
  const d = SG.deck;
  const card = d.cards[d.idx];
  d.el.innerHTML = `<div class="sg-deck">
      <div class="sg-deck-top"><span class="label">Card ${d.idx + 1} of ${d.cards.length} · ${esc(card.sec)}</span>
        <label class="toggle"><input type="checkbox" id="deckShuffle" ${d.shuffle ? 'checked' : ''}><span class="switch"></span>Shuffle</label></div>
      <button class="face sg-card ${d.flipped ? 'flipped' : ''}" id="sgFlip" type="button" aria-live="polite"
        aria-label="${d.flipped ? 'Answer' : 'Question'}: ${esc(d.flipped ? card.back : card.front)}. Tap to flip.">
        <span class="label">${d.flipped ? 'Answer' : 'Question'}</span>
        <span class="sg-card-text">${multiline(d.flipped ? card.back : card.front)}</span>
        <span class="sg-card-hint">${d.flipped ? 'Tap to see the question' : 'Tap to flip'}</span>
      </button>
      <div class="sg-deck-nav"><button class="btn" id="deckPrev" type="button">Previous</button>
        <button class="btn primary" id="deckNext" type="button">Next</button></div>
      <p class="help center">Space or Enter flips · ← and → move between cards</p>
    </div>`;
  $('sgFlip').onclick = deckFlip;
  $('deckPrev').onclick = () => deckMove(-1);
  $('deckNext').onclick = () => deckMove(1);
  $('deckShuffle').onchange = (e) => {
    d.shuffle = e.target.checked;
    sgPrefs().shuffleCards = d.shuffle;
    sgSavePrefs();
    d.cards = d.shuffle ? shuffled(d.base) : d.base;
    d.idx = 0;
    d.flipped = false;
    drawDeck();
  };
}

function deckFlip() {
  if (!SG.deck) return;
  SG.deck.flipped = !SG.deck.flipped;
  drawDeck();
  $('sgFlip').focus({ preventScroll: true });
}
function deckMove(dir) {
  const d = SG.deck;
  if (!d) return;
  d.idx = (d.idx + dir + d.cards.length) % d.cards.length;
  d.flipped = false;
  drawDeck();
  $(dir > 0 ? 'deckNext' : 'deckPrev').focus({ preventScroll: true });
}
document.addEventListener('keydown', (e) => {
  if (!$('sgFlip') || e.target.closest('input, select, textarea') || e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.key === 'ArrowRight') { e.preventDefault(); deckMove(1); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); deckMove(-1); }
  else if ((e.key === ' ' || e.key === 'Enter') && !e.target.closest('button, a, label')) { e.preventDefault(); deckFlip(); }
});

/* ------------------------------------------------------------------ progress */

function studyProgressTab(c, el) {
  const all = c.sections.flatMap((s) => secTypes(s).map((t) => sgStat(c.id, t)));
  const answered = all.reduce((a, s) => a + s.attempts, 0);
  const right = all.reduce((a, s) => a + s.correct, 0);
  const ms = sgMastery(c.id, c.type_ids);
  const quizzes = (sgCh(c.id).quizzes || []).slice(-5).reverse();
  el.innerHTML = `${studyMeter(c, ms, 'only-narrow')}
    <div class="readouts">
      <div class="readout"><b>${ms.pct}%</b><span>Mastered</span></div>
      <div class="readout"><b>${pct(right, answered)}</b><span>Accuracy</span></div>
      <div class="readout"><b>${answered}</b><span>Answers</span></div>
    </div>
    <p class="help legend">Mastered means your last answer on that kind of problem was right, first try.
      Saved on this device only. Tap a kind to practice it.</p>
    ${c.sections.map((s, i) => {
      const sm = sgMastery(c.id, secTypes(s));
      return `<details class="face part" ${i === 0 && answered ? 'open' : ''}><summary>${band(i + 1)}<span>${esc(s.id)} · ${esc(s.title)}</span>
          <span class="pm">${sm.pct}%</span></summary>
        <ul class="rows">${s.types.map((t) => {
          const st = sgStat(c.id, t.id);
          return `<li><span class="id">${lamp(st.attempts ? (st.last_correct ? 'go' : 'stop') : '')}</span>
            <button class="link sg-type" data-sec="${esc(s.id)}" data-type="${esc(t.id)}">${esc(t.title)}</button>
            <span class="stat">${st.attempts ? `<span>${st.correct}/${st.attempts}<small>${ago(st.last_seen)}</small></span>` : '<small>not tried</small>'}</span></li>`;
        }).join('')}</ul></details>`;
    }).join('')}
    ${quizzes.length ? `<section class="face list-card sg-quizzes"><h2 class="label">Recent quizzes</h2><ul class="rows two">${quizzes.map((q) =>
      `<li><span class="id">${pct(q.correct, q.answered)}</span><span>${q.correct} of ${q.answered} right · ${ago(q.finished)}</span></li>`).join('')}</ul></section>` : ''}
    ${answered ? `<p class="reset"><button class="link danger" id="resetBtn">Reset ${esc(c.title)} progress</button></p>` : ''}`;
  el.querySelectorAll('.sg-type').forEach((b) => {
    b.onclick = () => {
      sgPrefs()[`${c.id}|${b.dataset.sec}`] = { type: b.dataset.type };
      sgSavePrefs();
      delete SG.practice[`${c.id}|${b.dataset.sec}`];
      go(`#/study/${c.id}/${b.dataset.sec}/practice`);
    };
  });
  if (answered) {
    $('resetBtn').onclick = () => {
      if (!confirm(`Reset your ${c.title} progress on this device?`)) return;
      delete sgProg().chapters[c.id];
      store.set(SG_KEYS.progress, sgProg());
      render();
    };
  }
}
