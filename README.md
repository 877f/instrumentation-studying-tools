# Instrumentation Nation

Practice problems with worked solutions for our electronics class. It's live at **https://instrumentationnation.com**.

The home screen lists the study modules. There are two kinds:

- **Worksheet chapters**, such as Chapter 2: numeric problems from a worksheet, explained below.
- **Formula drills**, such as the Ohm's Law Wheel: you type formulas from memory. See [Ohm's Law Wheel](#ohms-law-wheel).

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

Answers within 1% are marked correct, and answers are shown to 3 significant figures. When an answer is off by a power of 10 or by a forgotten conversion, the feedback says which one.

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

Every module is **one data file in `chapters/` plus one line in `CHAPTERS` in `chapters/__init__.py`**. The engine code in `core/` and `static/` doesn't change. Copy the example closest to your new assignment.

### A worksheet chapter (numeric problems), for example Chapter 3

1. Copy `chapters/ch02.py` to `chapters/ch03.py`.
2. In the copy, replace these:
   - `PARTS`
   - `KINDS`: the problem types and their solvers
   - `TEMPLATES`: the worksheet questions
   - `FORMULAS`: the formula sheet
3. At the bottom of the copy, set `Chapter("ch3", 3, "Title", ...)`.
4. In `chapters/__init__.py`, import `ch03` and add `ch03.CHAPTER` to `CHAPTERS`.
5. If the chapter needs a new unit, add it to `QUANTITIES` in `core/units.py`. Watts were added this way.
6. Optionally, add a hand-calculated answer key to `KEYS` in `test_worksheet.py`.
7. Run `py test_worksheet.py ch3`. It prints every worksheet answer and checks 300 random variations of each question.

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

New modules show up on the home screen automatically, in the order they appear in `CHAPTERS`, each with its own instrument (see [Look and feel](#look-and-feel)).

## Look and feel

The site is styled as an instrument panel: a steel-blue panel, ivory faceplates, and an analog meter for each module.

- **Colors and fonts** are set once, at the top of `static/app.css`, with the dark-mode versions right below.
- **A worksheet chapter** gets a meter whose scale runs from 0 to its question count. The needle shows how many questions are mastered. The meter's code is in `static/instruments.js`.
- **A formula drill** gets a ring with one segment per formula. A segment lights up once you get that formula right in the current session.
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
```

## Phone can't connect (local runs only)

If the page loads on the computer but the phone times out, the Wi-Fi probably blocks devices from reaching each other. This is common on apartment Wi-Fi. Two workarounds:

- Connect the computer to your phone's hotspot, run `py app.py` again, and open the new URL it prints.
- Turn on Windows Mobile Hotspot, connect the phone to it, and open `http://192.168.137.1:5000`.

## Files

| Path | Purpose |
|---|---|
| `app.py` | Flask server (stateless JSON API) |
| `chapters/` | One data file per module (`ch02.py`, `ohms_wheel.py`) plus the `CHAPTERS` registry |
| `core/` | Shared engine: units, number formatting, worksheet templates, grading, `formula.py` (formula parser and sympy checker) |
| `static/` | Front end, no build step: `index.html`, `app.css`, `app.js`, `formula.js` (formula drills), `instruments.js` (meters, the formula ring, lamps, the needle animation) |
| `static/fonts/` | Fonts used by the site, with their licenses in `OFL.txt` |
| `run.sh`, `run.bat` | Run the site on your own computer for testing, with live reload |
| `scripts/keepalive.py` | Pings the site so it stays awake |
