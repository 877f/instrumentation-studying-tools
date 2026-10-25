"""Print all 54 Worksheet-mode answers (3 sig figs) and flag anything odd.

    py test_worksheet.py           answers + flags
    py test_worksheet.py --steps   also print every worked solution

Checks, per template:
  * the solver's answer matches an independent hand-written answer key
  * the answer is positive, finite and in a plausible range
  * the rounded 3-sig-fig answer, typed back in, grades as correct
  * 300 random variations all solve, render, and grade their own answer correct
Worksheet numbers that look like rounding/typos are listed as heads-ups.
"""
import math
import random
import sys

import grader
from questions import E_PER_C, TEMPLATES, PARTS, fmt_answer, fmt_num

E = E_PER_C
RHO = 10.4

# Independent answer key: written straight from the formulas, not via the solver.
KEY = {
    1: 6.25e18 / E, 2: 3.125e19 / E, 3: 9.36e20 / E, 4: 8 * E, 5: 3.5 * E, 6: 4.375e19 / E, 7: 12 * E, 8: 7.5e19 / E,
    9: 24 / 4, 10: 150 / 15, 11: 45 / 9, 12: 12 * 3, 13: 9 * (6.25e18 / E), 14: 90 / 15, 15: 75 / (3.125e19 / E),
    16: 24 * 8, 17: (48 / 6) * E, 18: 120 / (4.375e19 / E), 19: 18 * (7.5e19 / E), 20: 160 / 20, 21: 5 * (9.36e20 / E),
    22: 15 / 3, 23: 45 / 9, 24: 120 / 60, 25: 2 * 180, 26: (6.25e18 / E) / 4, 27: (3.125e19 / E) / 9000,
    28: 0.5 * 2700 * E, 29: 1.5 * 7200, 30: (9.36e20 / E) / 3, 31: (7.5e19 / E) / 1800, 32: 6 * 5400 * E,
    33: (4.375e19 / E) / 1200, 34: 25 / 2,
    35: 1 / 200, 36: 1 / 500, 37: 1 / 1e3, 38: 1 / 2.5e6, 39: 1 / 100, 40: 1 / 50e3,
    41: 1 / 25e-6, 42: 1 / 500e-9, 43: 1 / 2e-3, 44: 1 / 100e-6,
    45: 2 * 1250 / RHO, 46: RHO * 300 / 1.5, 47: RHO * 175 / 800, 48: RHO * 250 / 0.75, 49: 1.25 * 1600 / RHO,
    50: RHO * 399 / 2, 51: RHO * 225 / 2500, 52: 3 * 900 / RHO, 53: RHO * 150 / 3000, 54: RHO * 180 / 1,
}

# Loose "is this physically sensible for a textbook problem" ranges, per answer quantity.
RANGES = {
    "charge": (1e-3, 1e6), "electrons": (1e15, 1e26), "voltage": (1e-2, 1e4), "energy": (1e-3, 1e6),
    "current": (1e-6, 1e3), "time": (1e-3, 1e6), "conductance": (1e-9, 10), "resistance": (1e-3, 1e9),
    "length": (1, 1e5), "area": (100, 1e6),
}

HEADS_UP = {
    3: "9.36e20 electrons = 149.76 C (not a round number). 9.375e20 would give exactly 150 C. Same at 3 s.f.",
    21: "Uses 9.36e20 electrons: 748.8 J. With 9.375e20 it would be 750 J (0.16% apart, both accepted).",
    30: "Uses 9.36e20 electrons: 49.92 s. With 9.375e20 it would be 50 s (0.16% apart, both accepted).",
    32: "Wording 'charge in electrons': app answers the NUMBER of electrons; 32,400 C is also accepted.",
    50: "133 yd = 399 ft -> 2074.8 CM. If 133 1/3 yd (400 ft) was meant: 2080 CM (both accepted).",
}

ASCII = str.maketrans({"×": "x", "Ω": "ohm", "µ": "u", "÷": "/", "ρ": "rho", "·": "-", "⅓": " 1/3", "→": "->",
                       "↔": "<->", "≈": "~"})


def a(s):
    return s.translate(ASCII)


def main():
    show_steps = "--steps" in sys.argv
    problems = []
    rng = random.Random(1234)

    print("WORKSHEET ANSWERS (3 significant figures)")
    print("=" * 78)
    part = None
    for t in TEMPLATES:
        if t.part != part:
            part = t.part
            print(f"\nPart {part}: {PARTS[part]}")
        ans, steps = t.solve(t.worksheet)
        flag = []

        if not math.isclose(ans, KEY[t.id], rel_tol=1e-9):
            flag.append(f"SOLVER MISMATCH: key says {fmt_num(KEY[t.id], 6)}")
        lo, hi = RANGES[t.quantity]
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
            text = t.render(p)
            if not (math.isfinite(v) and v > 0) or "{" in text:
                flag.append(f"BAD VARIATION {p}")
                break
            r = grader.check(t, p, fmt_num(v).replace(" × 10^", "e"))
            if r["status"] != "correct":
                flag.append(f"VARIATION SELF-GRADE FAILED {p}")
                break

        mark = "  <-- FLAG: " + "; ".join(flag) if flag else ""
        print(f"  {t.id:>2}. {a(fmt_answer(ans, t.quantity)):<32}{mark}")
        if show_steps:
            print(f"      Q: {a(t.render(t.worksheet))}")
            for s in steps:
                print(f"       - {a(s)}")
            for n in t.notes(t.worksheet):
                print(f"       * {a(n)}")
        if flag:
            problems.append((t.id, flag))

    print("\nHEADS-UPS (worksheet wording/numbers worth checking with your teacher)")
    print("-" * 78)
    for tid, msg in HEADS_UP.items():
        print(f"  #{tid}: {msg}")

    print("\nRESULT")
    print("-" * 78)
    if problems:
        print(f"  {len(problems)} template(s) flagged: {', '.join('#' + str(i) for i, _ in problems)}")
        sys.exit(1)
    print("  All 54 answers match the independent key, are in a sensible range, and grade")
    print("  correctly when typed back in. 300 variations per template passed too.")


if __name__ == "__main__":
    main()
