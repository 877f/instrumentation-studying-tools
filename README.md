# Chapter 2 Study Tool

Quiz app for the Electronics Fundamentals Chapter 2 worksheet: the 54 worksheet questions, plus variations of them. It runs on your computer, and you open it from your phone or laptop on the same Wi-Fi.

## Run it

1. Install Flask once: `py -m pip install -r requirements.txt`
2. Start the server: `py app.py` (or double-click `run.bat`)
3. Open the **Phone / other device** URL it prints, for example `http://192.168.12.34:5000`

On this computer, `http://localhost:5000` also works. Press Ctrl+C in the window to stop the server.

On Mac/Linux, use `python3` instead of `py`. If port 5000 is busy, run `py app.py --port 5050`.

## Modes

| Mode | What it does |
|---|---|
| Worksheet | Exact numbers from the sheet, in order. Use it to check your own work. |
| Variations | Same wording, new random numbers that are easy to work by hand or calculator. |
| Weak spots | New numbers, picked mostly from templates you have missed. A miss on your last try counts double. |

You can filter by Part (1 to 5), choose 5 / 10 / 20 / All questions, and shuffle.

Each question has a **Hint** button (shows the formula only) and a **Show answer** button (counts as a miss). After you answer, you get the correct answer and a worked solution. A session ends with a summary of the templates you missed, with buttons to retry them.

## Typing answers

Units are optional. Without a unit, the answer is read in the unit shown under the question (C, V, J, A, s, S, Ω, ft, CM, or a count of electrons).

- These all mean the same thing: `2500`, `2,500`, `2.5e3`, `2.5 x 10^3`, `2.5k`
- Prefixes work: `556 uA`, `556 µA`, `0.556 mA`, `40 kohm`, `2 Mohm`, `25 uS`
- Unit case doesn't matter (`5 ms` on a conductance question means 5 mS), except **m vs M**: `m` is milli and `M` is mega
- Length and time units are converted: `80 yd` counts as 240 ft, `2 min` counts as 120 s

Grading allows 1% error. Answers are shown to 3 significant figures. If you are off by exactly a power of 10, or by a forgotten conversion (×60, ×3600, ×3, ×12, or 6.25 × 10^18), the app says which one.

## How ambiguous questions are read

| # | Reading used |
|---|---|
| 26, 30 | Electrons are converted to coulombs first (Q = N ÷ 6.25 × 10^18), then t = Q ÷ I. |
| 32 | "Charge in electrons" is read as the **number of electrons** (2.03 × 10^23). The coulomb answer (32,400 C) is also accepted, with a note. |
| 3, 21, 30 | 9.36 × 10^20 electrons = 149.76 C, used as written. 9.375 × 10^20 would give exactly 150 C. Both are inside the 1% tolerance. |
| 50 | 133 yd = 399 ft, so A = 2074.8 CM. If 133⅓ yd (400 ft) was meant, it's 2080 CM. Both are accepted. |
| 50, 52 | "Limit resistance to" gives the minimum wire size. "Maximum resistance" gives the longest wire allowed. |

The constants are 6.25 × 10^18 electrons per coulomb, and ρ = 10.4 Ω·CM/ft for copper.

## Check the answer key

```
py test_worksheet.py           # all 54 worksheet answers, 3 sig figs, with flags
py test_worksheet.py --steps   # the same, plus every worked solution
py test_app.py                 # grader and API tests (uses a temporary progress file)
```

## Progress

Stats are saved in `progress.json` next to `app.py`: attempts, correct answers, and the last time you saw each template, plus a short session log. To start over, use **See all 54 templates → Reset progress**, or delete the file.

## Phone can't connect

If the page loads on the computer but the phone's browser times out, check these causes in order:

1. **Different network.** The phone must be on the same Wi-Fi as the computer, not on mobile data.
2. **Windows Firewall.** The first time you run the app, Windows may ask whether to allow Python. Click Allow. If you clicked Cancel, open an admin PowerShell and run:
   `New-NetFirewallRule -DisplayName "Ch2 Study Tool" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -RemoteAddress LocalSubnet`
3. **Client isolation.** Managed apartment Wi-Fi often blocks devices on the network from talking to each other, for privacy. The internet still works, but the phone can't reach your computer. You can't turn this off from your side.

Fallbacks when isolation is the problem:

- **Phone hotspot (easiest).** Turn on the phone's hotspot and connect the computer to it. Restart `py app.py` and open the new URL it prints on the phone. The phone is the router here, so nothing blocks it. This uses little or no mobile data, because the traffic stays between the two devices.
- **Windows Mobile Hotspot.** On the computer, go to Settings → Network & internet → Mobile hotspot → On. Connect the phone to that network and open `http://192.168.137.1:5000`.
- **USB tethering (Android).** Plug the phone into the computer and turn on Settings → Network → Hotspot & tethering → USB tethering. Restart `py app.py` and use the URL it prints.
- **Laptop only.** `http://localhost:5000` always works on the computer that runs the server.

## Files

| File | Purpose |
|---|---|
| `app.py` | Flask server, sessions, progress file |
| `questions.py` | The 54 templates: wording, worksheet numbers, solvers, hints, variation ranges |
| `grader.py` | Answer parsing (sci notation, prefixes, units) and grading |
| `static/index.html` | The whole frontend (plain HTML/JS, no build step) |
| `test_worksheet.py`, `test_app.py` | Answer key printout and tests |
