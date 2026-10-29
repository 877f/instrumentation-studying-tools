# Instrumentation Nation

Practice problems with worked solutions for our electronics class. It's live at **https://instrumentationnation.com**.

The home screen lists the study modules. There are three kinds:

- **Worksheet chapters**, such as Chapter 2 and [Chapter 3: Electrical Calculations](#chapter-3-electrical-calculations): numeric problems from a worksheet, explained below.
- **Formula drills**, such as the Ohm's Law Wheel: you type formulas from memory. See [Ohm's Law Wheel](#ohms-law-wheel).
- **Problem sets**, such as [Household kWh](#household-kwh) and [Circuit Diagrams](#circuit-diagrams): levels of problems with several answer boxes, drawn as a table or a circuit.
- **Study guides**, such as [Geometry, Chapter 2](#study-guide-geometry-chapter-2): formula cards, practice with fresh numbers, quizzes, flashcards and saved progress, by section. Also at `/study/`.

Each worksheet chapter has three tabs:

- **Practice:** quiz yourself in one of three modes:
  - **Worksheet:** the exact numbers from the sheet
  - **Variations:** the same questions with new numbers
  - **Weak spots:** your most-missed questions first
- **Formulas:** the chapter's formula sheet.
- **Progress:** what you've mastered, plus a button to practice the questions you missed.

Progress is saved in each person's own browser. Nobody else sees it, and the server stores nothing. Progress on your phone and progress on your laptop are tracked separately.

## Typing answers

Units are optional. Without a unit, the answer is read in the unit shown in the answer box.

- These all mean the same thing: `2500`, `2,500`, `2.5e3`, `2.5 x 10^3`, `2.5k`
- Prefixes work: `556 uA`, `0.556 mA`, `40 kohm`, `2 Mohm`, `25 uS`
- Unit case doesn't matter, except **m vs M**: `m` is milli and `M` is mega
- Length and time units are converted: `80 yd` counts as 240 ft, `2 min` counts as 120 s
- In Household kWh: `1,000 Wh` counts as 1 kWh, `90 min` as 1.5 h, and money can be `$21.77`, `21.77` or `2177¢`

Answers within 1% are marked correct (0.5% in Chapter 3), and answers are shown to 3 significant figures. When an answer is off by a power of 10 or by a forgotten conversion, the feedback says which one.

## Chapter 3: Electrical Calculations

Chapter 3 is the Instrumentation, Automation & Robotics practice worksheet: 45 questions in four parts, which are the worksheet's sections.

| Part | Questions |
|---|---|
| 1 · Ohm's Law and Watt's Law | 1–30. Each has parts (a) and (b), graded separately as #1a, #1b and so on, so Part 1 has 60 |
| 2 · Energy in kWh | 31–35 |
| 3 · Efficiency | 36–40 |
| 4 · Battery Life from Amp-Hours | 41–45. 43–45 are bonus questions |

It works like Chapter 2: pick parts for one section or all four, use Worksheet, Variations or Weak spots, and review missed questions from the Progress tab or the results screen. Two things are different:

- **Tolerance:** answers within **0.5%** count, instead of 1%. A correctly rounded 3-significant-figure answer is always inside 0.5%.
- **Answers are shown** to 3 significant figures in engineering notation, keeping trailing zeros: `500 mA`, `3.60 kW`, `24.0 V`, `40.0 mW`. You can type them any way: `0.5`, `0.5 A`, `500 mA` and `500m` are all right for 500 mA. Efficiency takes `80`, `80%` or `80 %`. Hours take `50`, `50 h` or `3000 min`.

Choices I made:

- **Bonus questions 43–45** were written to fit the three answer-key entries that had no question: 20 Ah at 1.5 A (13.3 h), 5 Ah at 750 mA (6.67 h), and 40 Ah at 4 A (10.0 h).
- **Hints** say which law to use in words, such as "Ohm's law, solved for the current", and never write the formula. The worked solution after Check shows the formula, the numbers plugged in, and the answer. The Formulas tab has the full sheet.
- **New numbers** for Part 1 stay near the worksheet's own values, so an LED question keeps LED-sized numbers.
- **Hours** show as `h`, as in `50.0 h`.

The questions are in `chapters/calc.py`. `test_worksheet.py` checks every answer against the worksheet's key, both the value and how it's written.

## Ohm's Law Wheel

This drill teaches the 12 wheel formulas by deriving them from the two base equations, **V = I × R** and **P = V × I**. Every level is open from the start.

| Level | What you do |
|---|---|
| 1 · Transpose V = IR | Solve V = IR for I, for R and for V |
| 2 · Transpose P = VI | Solve P = VI for V and for I |
| 3 · Substitute | Combine both equations to get the 6 squared and square-root forms |
| 4 · Full wheel | "Write I in terms of P and R", picked at random from all 12 |
| 5 · Numeric | Plug in clean numbers, such as V = 12 V and R = 4 Ω, then find I |
| Blank wheel | Fill in all 12 slots from memory, grouped by P, I, V and R, with a timer |

How it works:

- **Typing formulas:** these all work: `I = V/R`, `V*R`, `IR`, `sqrt(P/R)`, `√(P/R)`, `P/I^2`, `P/I²`, `(V^2)/R`, `V x I`, `V ÷ R`. The `I =` at the front is optional, and case doesn't matter. `√PR` is read as √(PR), and `√P/R` as √(P) / R.
- **Checking:** the server uses sympy to test whether your answer is algebraically the same as the right one. It may use only the variables the question names, so "I in terms of V and R" answered with `P/V` is marked wrong. If you type U for voltage, it's accepted with a reminder that our class uses V. If an answer can't be read, the app says what it couldn't read instead of marking it wrong.
- **Feedback:** a wrong answer shows the right formula and how to derive it from the base equations. The Hint button only says which base equation(s) to start from. A missed question comes back two questions later, up to 3 times.
- **Stats:** kept in memory only, never saved, and gone when you close the page. The Session summary shows accuracy per level and every formula you missed.
- **No notes during questions:** the filled-in wheel appears only on results and summary screens.

## Problem sets: what they share

Household kWh and Circuit Diagrams work the same way:

- **Grading** uses the same checker as Chapter 2: prefixes, commas, the 1% tolerance, answers shown to 3 significant figures, and specific feedback on a wrong answer.
- **Hint** gives a nudge in words, never a formula.
- **Formulas** appear only after you press Check (in the worked solution) and on the results and summary screens. The question screen never shows one. The kWh module's first screen shows a one-line reminder, as requested.
- **Stats** are kept in memory only, like the Ohm's Law Wheel. Nothing is saved, and closing or reloading the page clears them. The rate setting and the custom table reset too.
- **Session summary** shows accuracy per level and each question type you missed, such as "K4 · The TOTAL kWh" or "D4 · Given P and R: find I".
- **Show answer** fills in every box and counts the question as missed.

## Household kWh

Energy = power × time, so kWh = (W × hours) ÷ 1000. The column is "Power Rating (Watts)"; nothing in the module says "watts per hour".

| Level | What you do |
|---|---|
| K1 · One appliance | Given the watts and the hours, find the kWh |
| K2 · Unit twists | The time is in minutes, or the power is in kW |
| K3 · Rearrange | Given the kWh and the hours, find the watts; or given the kWh and the watts, find the hours |
| K4 · Appliance table | 3 to 6 appliances: each row's kWh, then the TOTAL |
| K5 · Monthly cost | The table, then the kWh for a 30-day month and its cost at the rate you set |

Modes:

- **Worksheet:** fixed hours (the `worksheet_hours` column). K1 to K3 go down all 12 appliances. K4 and K5 split them into two tables of 6.
- **Variations:** random hours from each appliance's range. 10 questions for K1 to K3, 3 tables for K4 and K5.
- **Custom:** type the hours from your teacher's problem and change any wattage. Rows with no hours are left out. Turn on "Monthly cost too" for a K5-style problem. It counts toward K4 (or K5) in your stats.

Grading: each row is marked on its own, then the TOTAL. If rows are wrong but your TOTAL adds up your own rows, the feedback says so. The same goes for a monthly kWh that matches your own TOTAL, and a cost that matches your own monthly kWh. The worked solution shows W × hours = Wh, then ÷ 1000 = kWh, for every row, and names the biggest energy user.

### Defaults I chose

- **Electricity rate:** 12¢ per kWh. Change it in the box on the module page. The 12 is set once, as `RATE` in `chapters/kwh.py`.
- **Month:** 30 days, set once as `DAYS_PER_MONTH` in `chapters/kwh.py`.
- **Cost answers** are in dollars and shown to the cent, such as $59.39, instead of 3 significant figures.
- **Clean hours:** from 1 h up, hours are multiples of 0.5 h. Below 1 h, they're multiples of 6 minutes (0.1 h), so 0.3 h is 18 min and the math stays clean.
- **Worksheet hours**, picked inside each range: air conditioner 6, blow dryer 0.2, clock 24, clothes dryer 1, dishwasher 1.5, heater 4, microwave oven 0.3, range 1.5, refrigerator 10, television 4, washing machine 1, water heater 3.
- **K2 twists:** power in kW only from 250 W up (no 0.002 kW clock), time in minutes only up to 3 h. In Worksheet mode the two twists alternate down the list, and the clock is skipped.
- **The hours box** in Custom mode allows at most 24 hours per day.

### Edit the appliance list

The list is `chapters/kwh_appliances.csv`. Open it in Excel or any text editor:

```
appliance,watts,hours_min,hours_max,worksheet_hours
Air conditioner,860,4,10,6
Range,"12,200",0.5,3,1.5
```

- **watts:** the power rating. Write `12200`, or `"12,200"` in quotes because of the comma.
- **hours_min, hours_max:** the typical hours per day for Variations mode. Use the same number twice for a fixed time, as the clock does (24, 24).
- **worksheet_hours:** the fixed hours for Worksheet mode.
- To add an appliance, add a line. To remove one, delete its line. Up to 30 are allowed.

Restart the app after saving. If a line has a mistake, such as a missing number or hours_min above hours_max, the app won't start and prints the line number.

## Circuit Diagrams

Each question is a series loop drawn on the spot: a battery on the left (+ and − marked), a zigzag resistor on the right, and a current arrow labeled I. Two of V, I and R are labeled; the third shows "?". You answer in two steps: (1) the missing value, with units, then (2) the power in watts. The optional **Formula used** box, such as `I = V/R`, is checked with the Ohm's Law Wheel's formula checker. It's reported after you check but never changes the score.

| Level | What you do |
|---|---|
| D1 · Find I | V and R given: find I, then P |
| D2 · Find R | V and I given: find R, then P |
| D3 · Find V | I and R given: find V, then P |
| D4 · Mixed | D1 to D3, plus diagrams with P labeled and one of V, I or R: find the other two |
| D5 · Unit twists | D1 to D3 with mA, µA, kΩ, MΩ and mV; the worked solution converts to base units first |

Defaults I chose:

- **8 questions per level.** D4 includes all 6 kinds at least once. D5 mixes find I, find R and find V.
- **Clean values:** each diagram starts from a common voltage (1.5 V to 240 V) and resistor value. A pair is used only if the current comes out clean to 3 significant figures and the power to 4. D5 keeps the current between 10 µA and 100 mA and the power at 0.1 mW or more, so no answer is absurdly small. The value lists are at the top of `chapters/circuits.py`.
- **The formula box** checks the step 1 formula. For D4 diagrams with P labeled, that's the first unknown, such as `I = √(P/R)`.

## Study guide: Geometry, Chapter 2

Technical Math Chapter 2, in four sections: 2.1 Angles and lines, 2.2 Triangles, 2.3 Quadrilaterals, 2.4 Circles. It's on the home screen and at `/study/`. Each section has:

- **Practice:** one problem at a time with Check, Hint, Show steps and Next. Pick one kind of problem or Mixed. A wrong answer says what's off and lets you try again; it counts as a miss in your progress.
- **Formulas:** the section's formula card.
- **Cards:** flashcards. Tap, Space or Enter flips; ← and → move.
- **Textbook:** the book's own exercises, only on a computer that has the private file (see below).

The chapter page adds **Quiz** (pick sections and 5, 10 or 20 problems; no hints; score, missed problems and worked answers at the end; Retry missed) and **Progress** (per kind of problem: attempts, right answers, last seen; mastery % per section). Progress is saved in this browser only, under its own key, separate from the worksheet chapters.

**Every problem is generated.** The site is public, so the textbook's exercises are never in the repo. Each kind of problem is a generator that makes fresh numbers with the same structure, plus a solver that works out the answer, so the answer key is code. Figures are drawn as SVG from each problem's own numbers.

**Typing answers:**

- Numbers: `1,234`, `1234`, `4.43e6`, `4.43x10^6`, `4.43 × 10⁶`. Units are optional, but a typed unit must match: `ft²`, `ft^2`, `ft2` and `sq ft` are all ft², and `ft` for an area is marked wrong with a message. There are no conversions.
- Right means within **0.5 %**, or the exact value rounded half-up to the significant figures you typed (at least 2): exact 12.8 accepts 13; exact 25.76 accepts 26. When the value sits exactly on a tie, such as 9.25 to 2 figures, both 9.3 and 9.2 count.
- Angles: `25`, `25°`, `25 deg`. Radians: a decimal or a π form, `pi/8`, `π/8`, `313pi/450`.
- Naming parts of a figure: `∠ABD` = `∠DBA`, `CB` = `BC`, `ΔOEC` = `ΔCOE`. Case, spaces and the ∠ / Δ signs don't matter. Where several answers are right, any of them counts.
- Composite-figure formulas (2.3): `p = 4a + 2b`, checked for algebraic equivalence like the Ohm's Law Wheel.

**Answers are shown textbook style:** rounded to the fewest significant figures among the measured givens (exact values and whole-degree angles don't count; trailing zeros in a whole number such as 3200 aren't significant), with the unrounded value beside it. Scientific notation appears only where plain digits would need zeros that aren't significant: 1.73 × 10³ ft, but 340 m.

Choices I made:

- **2.1 #28–30 are pending:** the screenshot cut off after #27. The textbook set shows "Answer coming soon" for them, and they're never in a quiz.
- **2.3 #21–24 are built.** The figures (Figs. 2.65 and 2.66) were in the screenshots after all. The answers are worked out from the figures, not from the book's key: p = 4a + 2b, p = 4b, A = bh + a², A = a(2b − a). Check them against the book.
- **2.4 #16, #29 and #30 are shown to 4 figures** (1.239 × 10⁶ ft², 2.185 rad, 5.637 rad), because 1256, 125.2 and 323.0 have 4. The 3-figure answers are accepted too.
- **2.1 #11, "the sides adjacent to ∠DBC",** is read as the two rays BD and BC.

### The private textbook set

`content/private/ch2-textbook.json` holds the book's exercises, exact numbers and the answer-key values used as test fixtures. **`content/private/` is gitignored**, so it's never committed and never reaches Render. Where the file is absent, the Textbook tab doesn't appear. Copy it between your own computers by hand.

### Add a study chapter

A study chapter is **a folder in `content/study/`**, found at startup. No code changes:

1. Copy `content/study/geometry-ch2/` to a new folder, such as `content/study/geometry-ch3/`.
2. In `chapter.json`, set `id`, the titles, and the `sections`, each with its `formulas` card and `flashcards`.
3. In `problems.py`, write a `Type` for each kind of problem: `generate(rng)`, `valid(params)`, `view(params)` (text, hint, figure) and `solve(params)`. Figures use the helpers in `core/figures.py`.
4. Start the app. It generates problems for every type and checks that each one passes `valid()` and that its own answer grades as right, so a typo stops it with an error.
5. Optionally, add a private textbook file and name it in `chapter.json` as `"textbook"`.

`py test_study.py` checks every textbook fixture (skipped without the private file), over 100 checker cases, 200 random problems per type, the privacy rules, and the API.

## Test it on your computer

You don't need access to the hosted site to try a change. Run your own copy:

| System | Command |
|---|---|
| Linux or Mac | `./run.sh` |
| Windows | Double-click `run.bat` |

The first run sets up a private Python environment in `.venv/` and installs the requirements. After that, the script starts the site, opens it in your browser, and prints a "Phone / other device" address for phones on the same Wi-Fi.

While it runs, open pages update when you save a file:

- **CSS changes** apply in place, without a reload, so you keep your place in a quiz.
- **JavaScript and HTML changes** reload the page.
- **Python changes** restart the server, then reload the page.

Press Ctrl+C to stop it. Add `--port 5050` to use a different port. Run the tests with `./run.sh test` or `run.bat test`.

Without the scripts, `py app.py` still works if the requirements are installed; on Mac or Linux, use `python3` instead of `py`. Add `--dev` to turn on live reload.

## Host it on Render

Create a **Web Service** from this repo:

| Setting | Value |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn app:app` |

### Keep it awake

Render's free plan puts the site to sleep after 15 minutes without visitors. The next visitor then waits about a minute for it to wake up. `scripts/keepalive.py` pings `/healthz` every 10 minutes to prevent that, which leaves a 5-minute margin for a late ping.

There are two ways to run it on a schedule:

- **GitHub Actions (main, runs 24/7, free for public repos).** The job is in `.github/workflows/keepalive.yml`. See its runs on the repo's Actions tab. To pause it, run `gh workflow disable keepalive.yml --repo 877f/instrumentation-studying-tools`; use `enable` to turn it back on.
- **Windows Task Scheduler (backup, runs only while the PC is on).** A task named "Instrumentation Nation keep-awake" runs `pyw scripts\keepalive.py --once --log scripts\keepalive.log` every 10 minutes with no popup window, including on battery. It covers times when GitHub's scheduler runs late.
  - Check that it's working in `scripts\keepalive.log`.
  - Remove it with `Unregister-ScheduledTask -TaskName "Instrumentation Nation keep-awake"`.

To ping by hand, run `py scripts/keepalive.py`. Add `--url https://...` to ping a different address. Press Ctrl+C to stop.

Keeping one service awake all month uses up to 744 of Render's 750 free hours. GitHub may also run scheduled jobs a few minutes late, and it pauses them after 60 days with no commits.

## Add a module

Every module is **one data file in `chapters/` plus one line in `CHAPTERS` in `chapters/__init__.py`**. The engine code in `core/` and `static/` doesn't change. Copy the example closest to your new assignment:

| New assignment looks like | Copy |
|---|---|
| A worksheet of one-answer numeric questions | `chapters/ch02.py` |
| Formulas to learn by heart | `chapters/ohms_wheel.py` |
| Problems with several answer boxes, a table or a diagram | `chapters/kwh.py` (a table) or `chapters/circuits.py` (a circuit) |

### A worksheet chapter (numeric problems), for example Chapter 4

1. Copy `chapters/ch02.py` to `chapters/ch04.py`.
2. In the copy, replace these:
   - `PARTS`
   - `KINDS`: the problem types and their solvers
   - `TEMPLATES`: the worksheet questions
   - `FORMULAS`: the formula sheet
3. At the bottom of the copy, set `Chapter("ch4", 4, "Title", ...)`. For a worksheet that isn't a numbered chapter, also pass `name=`, `kicker=` and `tag=` so the site doesn't call it "Chapter N".
4. In `chapters/__init__.py`, import `ch04` and add `ch04.CHAPTER` to `CHAPTERS`.
5. If the chapter needs a new unit, add it to `QUANTITIES` in `core/units.py`. Watts were added this way.
6. Optionally, add a hand-calculated answer key to `KEYS` in `test_worksheet.py`.

Optional settings:

- **A different tolerance or answer format:** pass `tolerance=` and `shown=` to `Kind`. `chapters/calc.py` uses 0.5% and 3-sig-fig engineering notation.
- **Questions with parts (a) and (b):** make one template per part and give each a `label=`, such as `"1a"`. The label is what the site shows.
7. Run `py test_worksheet.py ch4`. It prints every worksheet answer and checks 300 random variations of each question.

### A formula drill, for example another formula wheel

1. Copy `chapters/ohms_wheel.py` to a new file.
2. In the copy, replace these:
   - `VARIABLES`: single letters, each with its unit quantity
   - the base equations
   - `FORMULAS`: each with its target, the variables it may use, the formula, and its derivation steps
   - `LEVELS`: which formulas each level asks, and the question wording
   - `numeric_values()`: produces a consistent set of values for the numeric level
3. In `chapters/__init__.py`, import it and add its `MODULE` to `CHAPTERS`.
4. Start the app. On startup it checks every formula against `numeric_values()`, so a typo in a formula stops it with an error.
5. Copy `test_wheel.py`, list equivalent spellings for your formulas, and run it.

### A problem set, for example series-parallel circuits

1. Copy `chapters/circuits.py` (or `chapters/kwh.py` for a table) to a new file.
2. In the copy, replace these:
   - `LEVELS`: id (a letter and a number, such as `S1`), title and one-line description
   - `generate()`: makes the givens for a session's questions
   - `valid()`: checks givens sent back by the browser
   - `view()`: the prompt, the hint (in words, no formulas), and what to draw
   - `solve()`: the answer boxes (`Answer`), the worked solution and notes
   - `FORMULAS`: the formula sheet for the results and summary screens
3. At the bottom of the copy, set `ProblemModule(id=..., title=..., ...)`. Add `modes=`, `settings=` and `custom=` only if the module needs them, as `kwh.py` does.
4. In `chapters/__init__.py`, import it and add its `MODULE` to `CHAPTERS`.
5. Start the app. On startup it generates questions for every level and checks that each passes `valid()` and solves to positive numbers, so a typo stops it with an error.
6. If it needs a new kind of drawing, add one next to `tableHTML()` and `circuitSVG()` in `static/problems.js`. Tables and series circuits work as they are.
7. Add a section for it to `test_problems.py`, then run `py test_problems.py`.

New modules show up on the home screen automatically, in the order they appear in `CHAPTERS`, each with its own instrument (see [Look and feel](#look-and-feel)).

## Look and feel

The site is styled as an instrument panel: a steel-blue panel, ivory faceplates, and an analog meter for each module.

- **Colors and fonts** are set once, at the top of `static/app.css`, with the dark-mode versions right below.
- **A worksheet chapter** gets a meter whose scale runs from 0 to its question count. The needle shows how many questions are mastered. The meter's code is in `static/instruments.js`.
- **A formula drill** gets a ring with one segment per formula. A segment lights up once you get that formula right in the current session.
- **A problem set** gets a meter from 0 to 100 showing your accuracy this session.
- **The kWh table** is styled like the textbook's: cream paper, thin brown rules and a bold upper-case header. In dark mode it turns dark sepia. On a phone it fits the screen; if a custom table is ever too wide, it scrolls sideways.
- **Part colors** follow the resistor color code: Part 1 is brown, 2 red, 3 orange, 4 yellow, 5 green, and so on.
- **Fonts** are served from `static/fonts/`, so the site makes no requests to other servers. Their licenses are in `static/fonts/OFL.txt`.
- **Motion:** needles swing and the home screen's meters sweep when the page opens, unless the device is set to reduce motion.

## Chapter 2: how ambiguous questions are read

| # | Reading used |
|---|---|
| 26, 30 | Electrons are converted to coulombs first, then t = Q ÷ I. |
| 32 | "Charge in electrons" is read as the number of electrons (2.03 × 10^23). The coulomb answer, 32,400 C, is also accepted, with a note. |
| 3, 21, 30 | 9.36 × 10^20 electrons is used as written (149.76 C). 9.375 × 10^20 would give exactly 150 C. Both are inside the 1% tolerance. |
| 50 | 133 yd = 399 ft, so A = 2068.8 CM. If 133⅓ yd (400 ft) was meant, it's 2074 CM. Both are accepted. |

Copper resistivity is **ρ = 10.37 Ω·CM/ft**, the value our class uses. It's set in one place, `RHO_CU` in `chapters/ch02.py`, and every answer, worked solution, hint and the formula sheet use it.

## Tests

```
py test_worksheet.py           # every worksheet answer to 3 sig figs, with flags (--steps adds worked solutions)
py test_wheel.py               # Ohm's Law Wheel checker: 12 formulas x spellings x variable sets
py test_app.py                 # grader and API tests
py test_problems.py            # Household kWh and Circuit Diagrams: 200 random questions per level
py test_study.py               # study guide: textbook fixtures, answer checker, 200 problems per type, privacy, API
```

`test_problems.py` checks that each kWh row is W × h ÷ 1000, the rows add up to the TOTAL, and the month and cost follow. For circuits it checks that V = I × R and that P = V × I = I² × R = V² ÷ R all agree. It flags any value that's negative, absurdly tiny or huge (the `RANGES` at the top), and prints the smallest and largest value it saw for each.

## Phone can't connect (local runs only)

If the page loads on the computer but the phone times out, the Wi-Fi probably blocks devices from reaching each other. This is common on apartment Wi-Fi. Two workarounds:

- Connect the computer to your phone's hotspot, run `py app.py` again, and open the new URL it prints.
- Turn on Windows Mobile Hotspot, connect the phone to it, and open `http://192.168.137.1:5000`.

## Files

| Path | Purpose |
|---|---|
| `app.py` | Flask server (stateless JSON API) |
| `chapters/` | One data file per module (`ch02.py`, `ohms_wheel.py`, `kwh.py`, `circuits.py`, `calc.py`) plus the `CHAPTERS` registry |
| `chapters/kwh_appliances.csv` | The Household kWh appliance list: ratings and hours. See [Edit the appliance list](#edit-the-appliance-list) |
| `core/` | Shared engine: units, number formatting, worksheet templates, grading, `formula.py` (formula parser and sympy checker), `problems.py` (problem sets) |
| `static/` | Front end, no build step: `index.html`, `app.css`, `app.js`, `formula.js` (formula drills), `problems.js` (problem sets: the kWh table, the circuit SVG), `instruments.js` (meters, the formula ring, lamps, the needle animation) |
| `static/fonts/` | Fonts used by the site, with their licenses in `OFL.txt` |
| `content/study/` | Study-guide chapters, one folder each: `chapter.json` plus `problems.py` |
| `content/private/` | Gitignored. The textbook's own exercises for the local-only Textbook set |
| `core/study.py`, `core/answers.py`, `core/figures.py` | Study-guide engine: chapter loading, answer checking and textbook-style rounding, SVG figures |
| `static/study.js`, `static/study.css` | Study-guide pages |
| `run.sh`, `run.bat` | Run the site on your own computer for testing, with live reload |
| `scripts/keepalive.py` | Pings the site so it stays awake |
