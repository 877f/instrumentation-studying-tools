"""Circuit Diagrams: a battery and one resistor in a series loop. Two of V, I and R are
labeled on the diagram and the third shows "?". Find it, then the power.

Content only. The engine is core/problems.py; static/problems.js draws the diagram as an
inline SVG from the labels in view(). The optional "Formula used" box is checked against
the Ohm's Law Wheel's formulas (chapters/ohms_wheel.py), so both modules agree.
"""
import math
from decimal import Decimal
from fractions import Fraction

from chapters.ohms_wheel import MODULE as WHEEL
from core.fmt import fmt_answer, fmt_eng, g
from core.problems import Answer, Level, ProblemModule, Solution

QUESTIONS = 8      # per session
MAX_VALUE = 1e8    # largest given accepted back from the browser

# Values the diagrams use. A voltage-resistance pair is kept only when the current and the
# power come out clean too (see pairs() below), so every answer is a tidy number.
VOLTS = "1.5 3 4.5 6 9 12 15 18 20 24 30 36 48 60 100 120 240"
OHMS = "1.5 2 2.5 3 4 5 6 8 10 12 15 16 20 24 25 30 40 48 50 60 75 80 100 120 150 200 240 300 400 480 600 1000 1200"
# Level D5: small currents through kilohm and megohm resistors, so every diagram needs a prefix.
VOLTS_D5 = "0.5 0.75 1.5 3 4.5 5 6 9 12 15 18 24 30 48"
OHMS_D5 = ("1k 1.2k 1.5k 2k 2.2k 2.4k 3k 4k 4.7k 5k 6k 8k 10k 12k 15k 20k 22k 24k 30k 47k 50k "
           "100k 120k 150k 200k 1M 2M")

UNIT = {"V": "V", "I": "A", "R": "Ω", "P": "W"}
NAME = {"V": "Voltage", "I": "Current", "R": "Resistance", "P": "Power"}
QTY = {"V": "voltage", "I": "current", "R": "resistance", "P": "power"}
# type -> (givens on the diagram, answers in step order)
TYPES = {
    "find-I": (("V", "R"), ("I", "P")),
    "find-R": (("V", "I"), ("R", "P")),
    "find-V": (("I", "R"), ("V", "P")),
    "PV": (("P", "V"), ("I", "R")),
    "PI": (("P", "I"), ("V", "R")),
    "PR": (("P", "R"), ("I", "V")),
}
LEVEL_TYPES = {"D1": ["find-I"], "D2": ["find-R"], "D3": ["find-V"], "D4": list(TYPES),
               "D5": ["find-I", "find-R", "find-V"]}
LEVELS = [
    Level("D1", "Find I", "V and R are labeled. Find I, then P."),
    Level("D2", "Find R", "V and I are labeled. Find R, then P."),
    Level("D3", "Find V", "I and R are labeled. Find V, then P."),
    Level("D4", "Mixed", "Any of D1 to D3, plus diagrams with P labeled: find the other two."),
    Level("D5", "Unit twists", "mA, µA, kΩ, MΩ and mV. Change to base units before solving."),
]
# Hints never show a formula: the quiz this practices for allows no notes.
HINTS = {
    "find-I": "You know V and R. Start from Ohm's law and get I by itself. "
              "Once you know V, I and R, any of the power formulas works.",
    "find-R": "You know V and I. Start from Ohm's law and get R by itself. Then use any of the power formulas.",
    "find-V": "You know I and R. Ohm's law gives V straight away. Then use any of the power formulas.",
    "PV": "You know P and V. The power equation gives I, then Ohm's law gives R.",
    "PI": "You know P and I. The power equation gives V, then Ohm's law gives R.",
    "PR": "You know P and R. Combine the power equation with Ohm's law to get I (expect a square root), "
          "then Ohm's law gives V.",
}
WHEEL_FORMULA = {(f.target, frozenset(f.knowns)): f for f in WHEEL.formulas}


# ------------------------------------------------------------------ values

def value(text):
    """"4.7k" -> Fraction(4700): exact, so clean-number checks don't trip on float noise."""
    mult = {"k": 1000, "M": 10 ** 6}.get(text[-1], 1)
    return Fraction(text.rstrip("kM")) * mult


def clean(x, sig):
    """True if x is a terminating decimal with at most `sig` significant figures (0.25, 1.5, 4700)."""
    d = x.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d != 1:
        return False
    return len((Decimal(x.numerator) / Decimal(x.denominator)).normalize().as_tuple().digits) <= sig


def pairs(volts, ohms, amps, watts):
    """Every (V, R) whose current is clean to 3 significant figures and power to 4, inside the given ranges."""
    out = []
    for V in map(value, volts.split()):
        for R in map(value, ohms.split()):
            I, P = V / R, V * V / R
            if amps[0] <= I <= amps[1] and watts[0] <= P <= watts[1] and clean(I, 3) and clean(P, 4):
                out.append((V, R))
    return out


PAIRS = pairs(VOLTS, OHMS, (Fraction(1, 20), 20), (Fraction(1, 10), 3000))
PAIRS_D5 = pairs(VOLTS_D5, OHMS_D5, (Fraction(1, 10 ** 5), Fraction(1, 10)), (Fraction(1, 10 ** 4), 10))
assert len(PAIRS) >= 60 and len(PAIRS_D5) >= 40, "circuits: too few clean value pairs"


# ---------------------------------------------------------------- questions

def generate(level, mode, rng, settings):
    types = LEVEL_TYPES[level.id]
    seq = types * (QUESTIONS // len(types))
    seq += rng.sample(types, QUESTIONS - len(seq))      # every kind at least once, then random extras
    rng.shuffle(seq)
    chosen = rng.sample(PAIRS_D5 if level.id == "D5" else PAIRS, QUESTIONS)
    out = []
    for t, (V, R) in zip(seq, chosen):
        every = {"V": V, "R": R, "I": V / R, "P": V * V / R}
        out.append({"type": t, **{k: float(every[k]) for k in TYPES[t][0]}})
    return out


def valid(level, p):
    if not isinstance(p, dict) or p.get("type") not in LEVEL_TYPES.get(level.id, ()):
        return False
    givens = TYPES[p["type"]][0]
    return set(p) == {"type", *givens} and all(
        isinstance(p[k], (int, float)) and not isinstance(p[k], bool) and math.isfinite(p[k])
        and 0 < p[k] <= MAX_VALUE for k in givens)


def label(level, k, x):
    """How a value is written on the diagram: prefixes in D5 (4.7 kΩ), plain base units before that."""
    return fmt_eng(x, UNIT[k], sig=6) if level.id == "D5" else f"{x:,.6g} {UNIT[k]}"


def view(level, p):
    t = p["type"]
    givens, (a, b) = TYPES[t]
    labels = {k: label(level, k, p[k]) if k in p else None for k in ("V", "I", "R")}
    if t.startswith("find-"):
        prompt = f"Find the {NAME[a].lower()} {a}, then the power P in watts."
    else:
        prompt = f"The power is labeled. Find {a} and {b}."
    desc = ", ".join(f"{k} = {label(level, k, p[k])}" for k in givens) + f"; find {a} and {b}"
    hint = HINTS[t]
    type_label = f"Find {a}" if t.startswith("find-") else f"P and {givens[1]} labeled"
    if level.id == "D5":
        hint = "First change every value to base units: volts, amps and ohms. " + hint
        type_label += " · prefixes"
    return {"type": t, "type_label": type_label, "prompt": prompt, "hint": hint, "desc": desc,
            "layout": {"kind": "diagram", "labels": labels, "power": label(level, "P", p["P"]) if "P" in p else None}}


def complete(t, p):
    """All four of V, I, R and P from the two givens."""
    V, I, R, P = p.get("V"), p.get("I"), p.get("R"), p.get("P")
    if t == "find-I":
        I = V / R
    elif t == "find-R":
        R = V / I
    elif t == "find-V":
        V = I * R
    elif t == "PV":
        I = P / V
        R = V / I
    elif t == "PI":
        V = P / I
        R = V / I
    else:                      # PR
        I = math.sqrt(P / R)
        V = I * R
    if P is None:
        P = V * I
    return {k: float(f"{x:.10g}") for k, x in (("V", V), ("I", I), ("R", R), ("P", P))}


def solve(level, p):
    t = p["type"]
    givens, (a, b) = TYPES[t]
    v = complete(t, p)
    q = {k: f"{g(v[k])} {UNIT[k]}" for k in v}         # plain base-unit values for the working

    def ans(k):
        return fmt_answer(v[k], QTY[k])

    steps = []
    if level.id == "D5":
        changed = [f"{label(level, k, p[k])} = {q[k]}" for k in givens if label(level, k, p[k]) != q[k]]
        if changed:
            steps.append("Change to base units: " + "; ".join(changed) + ".")
    first = {
        "find-I": f"I = V / R = {q['V']} / {q['R']} = {ans('I')}",
        "find-R": f"R = V / I = {q['V']} / {q['I']} = {ans('R')}",
        "find-V": f"V = I × R = {q['I']} × {q['R']} = {ans('V')}",
        "PV": f"I = P / V = {q['P']} / {q['V']} = {ans('I')}",
        "PI": f"V = P / I = {q['P']} / {q['I']} = {ans('V')}",
        "PR": f"I = √(P / R) = √({q['P']} / {q['R']}) = √{g(v['P'] / v['R'])} = {ans('I')}",
    }[t]
    second = {
        "PV": f"R = V / I = {q['V']} / {q['I']} = {ans('R')} (or R = V² / P)",
        "PI": f"R = V / I = {q['V']} / {q['I']} = {ans('R')} (or R = P / I²)",
        "PR": f"V = I × R = {q['I']} × {q['R']} = {ans('V')} (or V = √(P × R))",
    }.get(t, f"P = V × I = {q['V']} × {q['I']} = {ans('P')}")
    steps += [f"Step 1: {first}", f"Step 2: {second}"]
    steps.append(f"Check the power three ways: V × I = {g(v['V'] * v['I'])} W, I² × R = {g(v['I'] ** 2 * v['R'])} W, "
                 f"V² / R = {g(v['V'] ** 2 / v['R'])} W. They agree.")

    other = givens[1]
    if t.startswith("find-"):
        knowns = " and ".join(givens)
        answers = [Answer(a, f"Step 1 · {NAME[a]} {a}", QTY[a], v[a], f"Find {a} from {knowns}"),
                   Answer("P", "Step 2 · Power P", "power", v["P"], f"Power P, after finding {a}")]
    else:
        answers = [Answer(k, f"Step {i} · {NAME[k]} {k}", QTY[k], v[k], f"Given P and {other}: find {k}")
                   for i, k in enumerate((a, b), start=1)]
    headline = " · ".join(f"{k} = {ans(k)}" for k in (a, b))
    return Solution(answers, steps, headline, formula=WHEEL_FORMULA[(a, frozenset(givens))])


# Review screens only (results and session summary), never during questions.
FORMULAS = [
    {"title": "Ohm's law", "items": [
        {"name": "Voltage", "formula": "V = I × R", "note": None},
        {"name": "Current", "formula": "I = V / R", "note": None},
        {"name": "Resistance", "formula": "R = V / I", "note": None},
    ]},
    {"title": "Power", "items": [
        {"name": "Power, three ways", "formula": "P = V × I = I² × R = V² / R",
         "note": "Once you know V, I and R, all three give the same answer."},
        {"name": "Current, from P", "formula": "I = P / V · I = √(P / R)", "note": None},
        {"name": "Voltage, from P", "formula": "V = P / I · V = √(P × R)", "note": None},
        {"name": "Resistance, from P", "formula": "R = V² / P · R = P / I²", "note": None},
    ]},
    {"title": "Prefixes", "items": [
        {"name": "Smaller", "formula": "m = × 10^-3 · µ = × 10^-6", "note": "2.5 mA = 0.0025 A"},
        {"name": "Bigger", "formula": "k = × 10^3 · M = × 10^6", "note": "4.7 kΩ = 4700 Ω"},
    ]},
]

MODULE = ProblemModule(
    id="circuits",
    title="Circuit Diagrams",
    badge="CIRCUIT",
    intro="Read a series circuit, find the missing value, then the power. "
          "Nothing is saved: your stats reset when you close the page.",
    levels=LEVELS,
    generate=generate,
    valid=valid,
    view=view,
    solve=solve,
    formulas=FORMULAS,
    checker=WHEEL,
)
