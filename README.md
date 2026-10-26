# Instrumentation Nation

Practice problems with worked solutions for our electronics class. It's live at **https://instrumentationnation.com**.

Each chapter has three tabs:

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

## Run it locally

```
py -m pip install -r requirements.txt
py app.py
```

Open the URL it prints. Phones on the same Wi-Fi can use the "Phone / other device" address. On Mac or Linux, use `python3` instead of `py`.

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

## Add a chapter

1. Copy `chapters/ch02.py` to `chapters/ch03.py`.
2. In the copy, replace `PARTS`, the `KINDS` (problem types with their solvers), `TEMPLATES` (the worksheet questions) and `FORMULAS` (the formula sheet). At the bottom, set `Chapter("ch3", 3, "Title", ...)`.
3. In `chapters/__init__.py`, add `ch03` to `CHAPTERS`.
4. If the chapter needs a new unit, such as watts, add it to `QUANTITIES` in `core/units.py`.
5. Optionally, add a hand-calculated answer key to `KEYS` in `test_worksheet.py`.
6. Run `py test_worksheet.py ch3`. It prints every worksheet answer and checks 300 random variations of each question.

The new chapter shows up on the home screen automatically.

## Chapter 2: how ambiguous questions are read

| # | Reading used |
|---|---|
| 26, 30 | Electrons are converted to coulombs first, then t = Q ÷ I. |
| 32 | "Charge in electrons" is read as the number of electrons (2.03 × 10^23). The coulomb answer, 32,400 C, is also accepted, with a note. |
| 3, 21, 30 | 9.36 × 10^20 electrons is used as written (149.76 C). 9.375 × 10^20 would give exactly 150 C. Both are inside the 1% tolerance. |
| 50 | 133 yd = 399 ft, so A = 2074.8 CM. If 133⅓ yd (400 ft) was meant, it's 2080 CM. Both are accepted. |

## Tests

```
py test_worksheet.py           # every worksheet answer to 3 sig figs, with flags (--steps adds worked solutions)
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
| `chapters/` | One file per chapter: questions, solvers, hints, formula sheet |
| `core/` | Shared engine: units, number formatting, templates, grading |
| `static/` | Front end: `index.html`, `app.css`, `app.js` (no build step) |
| `scripts/keepalive.py` | Pings the site so it stays awake |
