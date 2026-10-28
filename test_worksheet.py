"""Print every chapter's Worksheet-mode answers (3 sig figs) and flag anything odd.

    py test_worksheet.py                 all chapters
    py test_worksheet.py ch2             one chapter
    py test_worksheet.py ch2 --steps     also print every worked solution

Checks, per template:
  * the answer matches the chapter's independent hand-written key (if it has one)
  * the answer is positive, finite and in a plausible range
  * the rounded 3-sig-fig answer, typed back in, grades as correct
  * 300 random variations all solve, render, and grade their own answer correct
"""
import math
import random
import sys

from chapters import BY_ID, CHAPTERS
from core import grader
from core.fmt import fmt_num

E = 6.25e18
RHO = 10.37

# Independent answer keys: written straight from the formulas, not via the solvers.
KEYS = {
    "ch2": {
        1: 6.25e18 / E, 2: 3.125e19 / E, 3: 9.36e20 / E, 4: 8 * E, 5: 3.5 * E, 6: 4.375e19 / E, 7: 12 * E,
        8: 7.5e19 / E, 9: 24 / 4, 10: 150 / 15, 11: 45 / 9, 12: 12 * 3, 13: 9 * (6.25e18 / E), 14: 90 / 15,
        15: 75 / (3.125e19 / E), 16: 24 * 8, 17: (48 / 6) * E, 18: 120 / (4.375e19 / E), 19: 18 * (7.5e19 / E),
        20: 160 / 20, 21: 5 * (9.36e20 / E), 22: 15 / 3, 23: 45 / 9, 24: 120 / 60, 25: 2 * 180,
        26: (6.25e18 / E) / 4, 27: (3.125e19 / E) / 9000, 28: 0.5 * 2700 * E, 29: 1.5 * 7200, 30: (9.36e20 / E) / 3,
        31: (7.5e19 / E) / 1800, 32: 6 * 5400 * E, 33: (4.375e19 / E) / 1200, 34: 25 / 2,
        35: 1 / 200, 36: 1 / 500, 37: 1 / 1e3, 38: 1 / 2.5e6, 39: 1 / 100, 40: 1 / 50e3,
        41: 1 / 25e-6, 42: 1 / 500e-9, 43: 1 / 2e-3, 44: 1 / 100e-6,
        45: 2 * 1250 / RHO, 46: RHO * 300 / 1.5, 47: RHO * 175 / 800, 48: RHO * 250 / 0.75, 49: 1.25 * 1600 / RHO,
        50: RHO * 399 / 2, 51: RHO * 225 / 2500, 52: 3 * 900 / RHO, 53: RHO * 150 / 3000, 54: RHO * 180 / 1,
    },
    # Electrical Calculations: keyed by question label ("1a"), from the worksheet's own answer key.
    "calc": {
        "1a": 2 * 12, "1b": 2 ** 2 * 12, "2a": 120 / 3, "2b": 120 * 3, "3a": 60 / 120, "3b": 120 ** 2 / 60,
        "4a": 15 * 240, "4b": 240 / 15, "5a": (25 / 100) ** 0.5, "5b": (25 * 100) ** 0.5, "6a": 8 * 24, "6b": 24 / 8,
        "7a": 1200 / 5, "7b": 1200 / 5 ** 2, "8a": 110 / 220, "8b": 110 ** 2 / 220, "9a": (500 / 48) ** 0.5,
        "9b": (500 * 48) ** 0.5, "10a": 36 / 12, "10b": 12 ** 2 / 36, "11a": 3.3 * 0.5, "11b": 3.3 / 0.5,
        "12a": 2 / 100, "12b": 2 ** 2 / 100, "13a": 75 / 15, "13b": 15 ** 2 / 75, "14a": 64 / 4, "14b": 64 / 4 ** 2,
        "15a": 9 / 3, "15b": 9 ** 2 / 3, "16a": 2400 / 240, "16b": 240 ** 2 / 2400, "17a": 0.1 * 470,
        "17b": 0.1 ** 2 * 470, "18a": 24 / 8, "18b": 24 ** 2 / 8, "19a": 1.5 * 40, "19b": 1.5 ** 2 * 40,
        "20a": (100 / 16) ** 0.5, "20b": (100 * 16) ** 0.5, "21a": 48 / 32, "21b": 48 ** 2 / 32, "22a": 720 / 6,
        "22b": 720 / 6 ** 2, "23a": 0.5 / 5, "23b": 5 ** 2 / 0.5, "24a": 6 / 0.25, "24b": 6 * 0.25, "25a": 360 / 120,
        "25b": 120 ** 2 / 360, "26a": 0.4 * 150, "26b": 0.4 ** 2 * 150, "27a": 18 / 9, "27b": 18 ** 2 / 9,
        "28a": 40 / 2, "28b": 40 / 2 ** 2, "29a": 200 / 50, "29b": 50 ** 2 / 200, "30a": 5 * 20, "30b": 5 ** 2 * 20,
        "31": 1500 * 6 / 1000, "32": 20 * 240 * 8 / 1000, "33": (4 * 15 * 6 + 200 * 4 + 65 * 8) / 1000,
        "34": 7200 * 6 / 1000, "35": 5 * 5000 * 12 / 1000, "36": 200 / 250 * 100, "37": 300 / 0.85,
        "38": 400 * 0.9, "39": 135 / 150 * 100, "40": 800 / 0.92, "41": 100 / 2, "42": 7.2 / 0.5,
        "43": 20 / 1.5, "44": 5 / 0.75, "45": 40 / 4,
    },
}

# The answer exactly as an answer key writes it (Electrical Calculations: 3 sig figs, engineering notation).
SHOWN = {
    "calc": {
        "1a": "24.0 V", "1b": "48.0 W", "2a": "40.0 Ω", "2b": "360 W", "3a": "500 mA", "3b": "240 Ω", "4a": "3.60 kW",
        "4b": "16.0 Ω", "5a": "500 mA", "5b": "50.0 V", "6a": "192 W", "6b": "3.00 Ω", "7a": "240 V", "7b": "48.0 Ω",
        "8a": "500 mA", "8b": "55.0 W", "9a": "3.23 A", "9b": "155 V", "10a": "3.00 A", "10b": "4.00 Ω",
        "11a": "1.65 W", "11b": "6.60 Ω", "12a": "20.0 mA", "12b": "40.0 mW", "13a": "5.00 A", "13b": "3.00 Ω",
        "14a": "16.0 V", "14b": "4.00 Ω", "15a": "3.00 A", "15b": "27.0 W", "16a": "10.0 A", "16b": "24.0 Ω",
        "17a": "47.0 V", "17b": "4.70 W", "18a": "3.00 A", "18b": "72.0 W", "19a": "60.0 V", "19b": "90.0 W",
        "20a": "2.50 A", "20b": "40.0 V", "21a": "1.50 A", "21b": "72.0 W", "22a": "120 V", "22b": "20.0 Ω",
        "23a": "100 mA", "23b": "50.0 Ω", "24a": "24.0 Ω", "24b": "1.50 W", "25a": "3.00 A", "25b": "40.0 Ω",
        "26a": "60.0 V", "26b": "24.0 W", "27a": "2.00 A", "27b": "36.0 W", "28a": "20.0 V", "28b": "10.0 Ω",
        "29a": "4.00 A", "29b": "12.5 Ω", "30a": "100 V", "30b": "500 W", "31": "9.00 kWh", "32": "38.4 kWh",
        "33": "1.68 kWh", "34": "43.2 kWh", "35": "300 kWh", "36": "80.0 %", "37": "353 W", "38": "360 W",
        "39": "90.0 %", "40": "870 W", "41": "50.0 h", "42": "14.4 h", "43": "13.3 h", "44": "6.67 h", "45": "10.0 h",
    },
}

# Worksheet wording/numbers worth checking with the teacher.
HEADS_UP = {
    "ch2": {
        3: "9.36e20 electrons = 149.76 C (not a round number). 9.375e20 would give exactly 150 C. Same at 3 s.f.",
        21: "Uses 9.36e20 electrons: 748.8 J. With 9.375e20 it would be 750 J (0.16% apart, both accepted).",
        30: "Uses 9.36e20 electrons: 49.92 s. With 9.375e20 it would be 50 s (0.16% apart, both accepted).",
        32: "Wording 'charge in electrons': app answers the NUMBER of electrons; 32,400 C is also accepted.",
        50: "133 yd = 399 ft -> 2068.8 CM. If 133 1/3 yd (400 ft) was meant: 2074 CM (both accepted).",
    },
}

# Loose "is this physically sensible for a textbook problem" ranges, per answer quantity.
RANGES = {
    "charge": (1e-3, 1e6), "electrons": (1e15, 1e26), "voltage": (1e-2, 1e4), "energy": (1e-3, 1e6),
    "current": (1e-6, 1e3), "time": (1e-3, 1e6), "conductance": (1e-9, 10), "resistance": (1e-3, 1e9),
    "length": (1, 1e5), "area": (100, 1e6), "power": (1e-3, 1e5), "kwh": (1e-3, 1e4), "percent": (1, 100),
    "hours": (0.1, 1000),
}

ASCII = str.maketrans({"×": "x", "Ω": "ohm", "µ": "u", "÷": "/", "ρ": "rho", "·": "-", "⅓": " 1/3", "→": "->"})


def a(s):
    return s.translate(ASCII)


def check_chapter(ch, show_steps):
    problems = []
    labels = {t.label: t.id for t in ch.templates}
    key = {labels.get(k, k): v for k, v in KEYS.get(ch.id, {}).items()}     # keys may be labels, like "1a"
    want = {labels.get(k, k): v for k, v in SHOWN.get(ch.id, {}).items()}
    rng = random.Random(1234)
    title = "" if ch.title == ch.name else f": {a(ch.title)}"
    print(f"\n{a(ch.name).upper()}{title}  (worksheet answers, 3 significant figures)")
    print("=" * 78)
    part = None
    for t in ch.templates:
        if t.part != part:
            part = t.part
            print(f"\nPart {part}: {ch.parts[part].title}")
        ans, steps = t.solve(t.worksheet)
        flag = []

        if t.id in key and not math.isclose(ans, key[t.id], rel_tol=1e-9):
            flag.append(f"SOLVER MISMATCH: key says {fmt_num(key[t.id], 6)}")
        if t.id in want and grader.shown(t, ans) != want[t.id]:
            flag.append(f"SHOWN AS {a(grader.shown(t, ans))}, the key writes {a(want[t.id])}")
        lo, hi = RANGES.get(t.quantity, (0, math.inf))
        if not (math.isfinite(ans) and ans > 0):
            flag.append("NOT A POSITIVE FINITE NUMBER")
        elif not (lo <= ans <= hi):
            flag.append(f"OUTSIDE PLAUSIBLE RANGE {lo:g}..{hi:g}")

        typed = fmt_num(ans).replace(" × 10^", "e")
        res = grader.check(t, t.worksheet, typed)
        if res["status"] != "correct":
            flag.append(f"ROUNDED ANSWER '{typed}' GRADED {res['status']}")

        for _ in range(300):
            p = t.generate(rng)
            v, _s = t.solve(p)
            if not (math.isfinite(v) and v > 0) or "{" in t.render(p):
                flag.append(f"BAD VARIATION {p}")
                break
            if grader.check(t, p, fmt_num(v).replace(" × 10^", "e"))["status"] != "correct":
                flag.append(f"VARIATION SELF-GRADE FAILED {p}")
                break

        mark = "  <-- FLAG: " + "; ".join(flag) if flag else ""
        print(f"  {t.label:>3}. {a(grader.shown(t, ans)):<32}{mark}")
        if show_steps:
            print(f"      Q: {a(t.render(t.worksheet))}")
            for s in steps:
                print(f"       - {a(s)}")
            for n in t.notes(t.worksheet):
                print(f"       * {a(n)}")
        if flag:
            problems.append(t.label)

    if missing := [i for i in key if i not in ch.by_id]:
        problems.append(f"key has unknown ids {missing}")
    if HEADS_UP.get(ch.id):
        print("\nHEADS-UPS (worksheet wording/numbers worth checking with your teacher)")
        print("-" * 78)
        for tid, msg in HEADS_UP[ch.id].items():
            print(f"  #{tid}: {msg}")
    return problems


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    chapters = [BY_ID[x] for x in args] if args else [c for c in CHAPTERS if c.type == "worksheet"]
    all_problems = {ch.id: check_chapter(ch, "--steps" in sys.argv) for ch in chapters}

    print("\nRESULT")
    print("-" * 78)
    flagged = {cid: p for cid, p in all_problems.items() if p}
    if flagged:
        for cid, p in flagged.items():
            print(f"  {cid}: flagged {', '.join('#' + str(i) for i in p)}")
        sys.exit(1)
    total = sum(len(ch.templates) for ch in chapters)
    print(f"  All {total} answers are in a sensible range and grade correctly when typed back in;")
    print("  those with a hand-written key match it. 300 variations per template passed too.")


if __name__ == "__main__":
    main()
