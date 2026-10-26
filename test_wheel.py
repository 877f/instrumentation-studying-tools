"""Ohm's Law Wheel checker test.

    py test_wheel.py

1. Each of the 12 formulas, typed many equivalent ways, must be marked correct.
2. Every question x every formula's right-hand side (all 12 variable sets):
   only the matching formula passes, and any answer that uses a variable the
   question doesn't allow must fail with the "only allows" message.
3. Input that can't be read is reported as unreadable (with a reason), never
   marked wrong.
4. U for V is accepted with a reminder.
5. Level 5 numbers, and 6. the blank wheel.
"""
import random
import sys

from chapters import BY_ID
from core.fmt import fmt_eng, fmt_num
from core.units import QUANTITIES

M = BY_ID["ohms-wheel"]

SPELLINGS = {
    "P:VI": ["V*I", "VI", "IV", "V x I", "V × I", "v*i", "(V)(I)", "P = V*I", "p=vi", "V·I"],
    "P:IR": ["I^2*R", "I^2 R", "I²R", "I**2*R", "R*I^2", "I*I*R", "I(IR)", "p = i^2 r", "(I^2)R", "R I²"],
    "P:VR": ["V^2/R", "(V^2)/R", "V²/R", "V*V/R", "V**2/R", "V^2 ÷ R", "V/R*V", "P = V^2/R", "(V/R)V", "v²/r"],
    "I:VR": ["V/R", "v/r", "V ÷ R", "I = V/R", "(V)/(R)", "V*R^-1", "V/(R)", "1/R*V", "V / R", "i=v/r"],
    "I:PV": ["P/V", "p/v", "P ÷ V", "I = P/V", "P*V^-1", "(P)/(V)", "1/V*P", "P/(V)"],
    "I:PR": ["sqrt(P/R)", "√(P/R)", "SQRT(P/R)", "(P/R)^0.5", "(P/R)^(1/2)", "sqrt(P)/sqrt(R)", "√P/√R",
             "I = sqrt(P/R)", "√(P÷R)", "sqrt(P*R)/R"],
    "V:IR": ["I*R", "IR", "RI", "I x R", "I × R", "V = IR", "v = ir", "(I)(R)", "I R", "R*I"],
    "V:PI": ["P/I", "P ÷ I", "V = P/I", "p/i", "P*I^-1", "(P)/I"],
    "V:PR": ["sqrt(P*R)", "√(PR)", "sqrt(PR)", "√PR", "(PR)^0.5", "sqrt(P)*sqrt(R)", "√P√R", "V = √(P×R)",
             "(P*R)^(1/2)", "SQRT(R*P)"],
    "R:VI": ["V/I", "v/i", "V ÷ I", "R = V/I", "V*I^-1", "(V)/(I)"],
    "R:VP": ["V^2/P", "V²/P", "(V^2)/P", "V*V/P", "V**2/P", "R = V^2/P", "V/P*V", "v^2/p"],
    "R:PI": ["P/I^2", "P/I²", "P/(I^2)", "P/(I*I)", "P/I/I", "P*I^-2", "R = P/I^2", "P ÷ I²", "p/i^2", "P/I**2"],
}

UNREADABLE = ["", "V//R", "V/", "(V/R", "V/R)", "abc", "I2R", "V^R", "V = I = R", "IR = V", "V^99", "2..5",
              "√", "²V", "V$R"]

ASCII = str.maketrans({"²": "^2", "√": "sqrt", "×": "x", "÷": "/", "Ω": "ohm", "µ": "u", "·": "*", "✓": "ok",
                       "³": "^3", "…": "..."})
failures = []


def a(s):
    return str(s).translate(ASCII)


def check(key, raw):
    return M.check_symbolic(M.by_key[key], raw)


def section(title):
    print(f"\n{title}\n" + "-" * 78)


def spellings():
    section("1. EQUIVALENT SPELLINGS (all must be marked correct)")
    for f in M.formulas:
        tries = SPELLINGS[f.key]
        bad = [(s, check(f.key, s)) for s in tries]
        bad = [(s, r) for s, r in bad if r["status"] != "correct"]
        print(f"  {a(f.display):<16} {len(tries) - len(bad):>2}/{len(tries)} pass")
        for s, r in bad:
            failures.append(f"spelling {f.key} {a(s)!r}: {r['status']} {a(r['message'])}")
            print(f"      FAIL {a(s)!r}: {r['status']}: {a(r['message'])}")


def variable_sets():
    section("2. VARIABLE SETS: each question (row) answered with each formula's right side (column)")
    print("     = correct    v rejected for using a variable the question doesn't allow    x not equivalent")
    print("  " + " " * 15 + " ".join(f"{f.key:>5}" for f in M.formulas))
    counts = {"=": 0, "v": 0, "x": 0}
    for q in M.formulas:
        row = []
        for f in M.formulas:
            r = check(q.key, f.expr_text)
            disallowed = set(f.knowns) - set(q.knowns)
            if f.key == q.key:
                ok, mark = r["status"] == "correct", "="
            elif disallowed:
                ok, mark = r["status"] == "incorrect" and "only allows" in (r["message"] or ""), "v"
            else:
                ok, mark = r["status"] == "incorrect", "x"
            if not ok:
                failures.append(f"variable set: question {q.key} answered {f.expr_text}: {r['status']} {r['message']}")
                mark = "!"
            counts[mark] = counts.get(mark, 0) + 1
            row.append(f"{mark:>5}")
        print(f"  {a(q.display):<15}" + " ".join(row))
        # Solving for the wrong variable must be caught too.
        other = next(v for v in M.variables if v != q.target)
        r = check(q.key, f"{other} = {q.expr_text}")
        if r["status"] != "incorrect" or "You solved for" not in (r["message"] or ""):
            failures.append(f"wrong left side not caught for {q.key}")
    print(f"\n  {counts['=']} correct, {counts['v']} wrong-variable rejections, {counts['x']} not-equivalent rejections")


def unreadable():
    section("3. UNREADABLE INPUT (must explain what it couldn't read, not mark wrong)")
    for raw in UNREADABLE:
        r = check("I:VR", raw)
        ok = r["status"] == "unparsed" and r["message"]
        if not ok:
            failures.append(f"unreadable {raw!r}: got {r['status']}")
        print(f"  {'ok  ' if ok else 'FAIL'} {a(repr(raw)):<14} -> {a(r['message'])}")


def u_for_v():
    section("4. U FOR V (accepted, with a reminder)")
    for key, raw in [("I:VR", "U/R"), ("V:IR", "U = IR"), ("P:VR", "U^2/R"), ("R:VP", "u²/p")]:
        r = check(key, raw)
        ok = r["status"] == "correct" and r["reminder"] and "class uses V" in r["reminder"]
        if not ok:
            failures.append(f"U for V {raw!r}: {r['status']} {r['reminder']}")
        print(f"  {'ok  ' if ok else 'FAIL'} {raw:<8} -> {r['status']}: {a(r['reminder'])}")


def numeric():
    section("5. LEVEL 5 NUMERIC (40 random problems per formula)")
    rng = random.Random(7)
    for f in M.formulas:
        t = M.numeric_template(f)
        unit = QUANTITIES[t.quantity].unit
        ok_count = 0
        for _ in range(40):
            p = t.generate(rng)
            v, _ = t.solve(p)
            plain = fmt_num(v).replace(" × 10^", "e")
            prefixed = fmt_eng(v, unit).replace("µ", "u").replace("Ω", "ohm")
            results = [M.check_numeric(f, p, plain)["status"] == "correct",
                       M.check_numeric(f, p, prefixed)["status"] == "correct",
                       "power of 10" in (M.check_numeric(f, p, repr(v * 10))["message"] or "")]
            if all(results):
                ok_count += 1
            else:
                failures.append(f"numeric {f.key} {p}: plain/prefixed/x10 = {results}")
        print(f"  {a(f.display):<16} {ok_count}/40   e.g. {a(t.render(t.generate(rng)))}")


def blank_wheel():
    section("6. BLANK WHEEL")
    rng = random.Random(3)
    answers = {}
    for qv in M.quadrants:
        exprs = [f.expr_text for f in M.formulas if f.target == qv]
        rng.shuffle(exprs)
        answers[qv] = exprs
    full = M.grade_blank(answers)
    ok = full["score"] == 12
    print(f"  {'ok  ' if ok else 'FAIL'} all 12 in shuffled order -> {full['score']}/12")
    if not ok:
        failures.append(f"blank wheel all correct scored {full['score']}")

    mixed = M.grade_blank({"P": ["V*I", "VI", ""], "I": ["V/R", "P/R", "I = sqrt(P/R)"],
                           "V": ["V = P/I", "P = IR", "P/I"], "R": ["V/I", "R*1", "V²/P"]})
    want = {"P": ["correct", "duplicate", "blank"], "I": ["correct", "incorrect", "correct"],
            "V": ["correct", "incorrect", "duplicate"], "R": ["correct", "incorrect", "correct"]}
    got = {qv: [s["status"] for s in q["slots"]] for qv, q in mixed["quadrants"].items()}
    ok = got == want and mixed["score"] == 6
    print(f"  {'ok  ' if ok else 'FAIL'} duplicate / blank / wrong quadrant / wrong box -> {mixed['score']}/12, {got}")
    if not ok:
        failures.append(f"blank wheel mixed: {got} score {mixed['score']}")


def main():
    spellings()
    variable_sets()
    unreadable()
    u_for_v()
    numeric()
    blank_wheel()
    section("RESULT")
    if failures:
        print(f"  {len(failures)} FAILURE(S):")
        for f in failures:
            print("   - " + a(f))
        sys.exit(1)
    total = sum(len(v) for v in SPELLINGS.values())
    print(f"  All passed: {total} equivalent spellings, 144 question x variable-set checks, "
          f"{len(UNREADABLE)} unreadable inputs, U-for-V, 480 numeric problems, blank wheel.")


if __name__ == "__main__":
    main()
