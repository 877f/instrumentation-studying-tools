"""Study guide: textbook fixtures, the answer checker, every generator, privacy and the API.

    py test_study.py

1. Fixtures   every exercise in content/private/ch2-textbook.json comes out of its solver at the
              brief's Exact value, its listed answers grade as right, and its shown answer matches.
              Skipped, not failed, on a computer without the private file.
2. Checker    unit spellings, significant figures and ties, π forms, name sets, formulas.
3. Generators 200 seeds per kind of problem: valid givens that survive a round trip through JSON,
              positive answers, squared units for areas, the triangle inequality, a hypotenuse longer
              than its legs, figures that draw, and the shown answer graded as right.
4. Privacy    the private file is gitignored, untracked, never staged by "git add", and not served.
5. API        end to end through Flask's test client.
"""
import json
import math
import os
import random
import subprocess
import sys
from decimal import Decimal
from fractions import Fraction

import app as server
from chapters import BY_ID
from core.answers import PI, Ident, Num, Sym, fmt_sig, sig_figs

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
GEO = BY_ID["geometry-ch2"]
N = 200
failures, passed = [], [0]


def check(ok, msg):
    if ok:
        passed[0] += 1
    else:
        failures.append(msg)


def section(title):
    print(f"\n== {title}")


def status(ans, raw):
    return ans.check(raw)["status"]


# ------------------------------------------------------------------ fixtures

def close_to_fixture(value, exact):
    """Within one unit in the fixture's last printed digit (the brief's values are rounded or cut)."""
    places = len(exact.split(".")[1]) if "." in exact else 0
    return abs(Decimal(value) - Decimal(exact)) <= Decimal(1).scaleb(-places)


def fixture_tests():
    section("1. TEXTBOOK FIXTURES (content/private/ch2-textbook.json)")
    data = GEO.textbook()
    if data is None:
        print("  SKIPPED: the private file isn't on this computer. Nothing else depends on it.")
        return
    counts = {"exact": 0, "accepted": 0, "shown": 0, "pending": 0}
    for item in data["items"]:
        where = f"{item['section']} #{item['number']}"
        if item.get("pending"):
            counts["pending"] += 1
            check("type" not in item, f"{where}: a pending item must not name a type")
            continue
        t = GEO.by_type.get(item["type"])
        if t is None or not t.valid(item["params"]):
            check(False, f"{where}: unknown type or invalid params {item.get('params')}")
            continue
        a = t.solve(item["params"]).answer
        if "exact" in item:
            counts["exact"] += 1
            check(close_to_fixture(a.value, item["exact"]), f"{where}: solver {a.value} != Exact {item['exact']}")
            check(status(a, a.number()) == "correct", f"{where}: its own shown number {a.number()} isn't accepted")
        if "shown" in item:
            counts["shown"] += 1
            check(a.shown() == item["shown"], f"{where}: shown {a.shown()!r}, expected {item['shown']!r}")
        for raw in item.get("accepted", []):
            counts["accepted"] += 1
            got = a.check(raw)
            check(got["status"] == "correct", f"{where}: {raw!r} should be right, got {got['status']}: {got['message']}")
        print(f"  {where:<9} {item['type']:<16} -> {a.shown()}")
    print(f"  {counts['exact']} Exact values, {counts['shown']} shown answers, {counts['accepted']} accepted answers, "
          f"{counts['pending']} pending items")
    items = GEO.textbook_items("2.1")
    check(sum(1 for i in items if i["pending"]) == 3, "2.1: #28-30 should come back as pending")


# ------------------------------------------------------------------- checker

def checker_tests():
    section("2. CHECKER")
    cases = 0

    def expect(ans, raw, want, needle=None):
        nonlocal cases
        cases += 1
        got = ans.check(raw)
        ok = got["status"] == want and (needle is None or (needle.lower() in (got["message"] or "").lower()))
        check(ok, f"{raw!r} -> {got['status']} ({got['message']}), expected {want}" + (f" with {needle!r}" if needle else ""))

    n = Num(Decimal(1234), "length", "ft", 4)
    for raw in ("1,234", "1234", "1234 ft", "1.234e3", "1.234 x 10^3 feet"):
        expect(n, raw, "correct")

    big = Num(Decimal("4434050.07"), "area", "yd", 2)
    for raw in ("4.43e6", "4.43x10^6", "4.43 x 10^6", "4.43×10⁶", "4.4e6 yd^2", "4.4 × 10^6 sq yd", "4,434,050 yd²"):
        expect(big, raw, "correct")
    expect(big, "4.43e6 yd", "incorrect", "length unit")

    sq = Num(Decimal(12), "area", "ft", 2)
    for raw in ("12 ft²", "12 ft^2", "12 sq ft", "12 square feet", "12 ft2", "12 sq. ft."):
        expect(sq, raw, "correct")
    expect(sq, "12 ft", "incorrect", "area")
    expect(sq, "12 in^2", "incorrect", "ft²")
    expect(sq, "12 furlongs", "unparsed")
    expect(sq, "twelve", "unparsed")

    # significant figures: the typed figures decide the rounding, at least 2
    p = Num(Decimal("12.8"), "length", "m", 2)
    for raw, want in (("12.8", "correct"), ("13", "correct"), ("12", "incorrect"), ("10", "incorrect")):
        expect(p, raw, want)
    c = Num(Decimal("25.76106"), "length", "in", 2)
    for raw, want in (("25.8", "correct"), ("26", "correct"), ("25.76", "correct"), ("25.5", "incorrect")):
        expect(c, raw, want)
    tie = Num(Decimal("9.25"), "area", "m", 2)
    for raw, want in (("9.25", "correct"), ("9.3", "correct"), ("9.2", "correct"), ("9.1", "incorrect")):
        expect(tie, raw, want)
    expect(Num(Decimal("9.2500001"), "area", "m", 2), "9.2", "incorrect")       # not a tie: 9.2 is 0.54 % off
    k = Num(Decimal(1559), "length", "cm", 3)
    for raw, want in (("1.56e3", "correct"), ("1.6e3", "correct"), ("1559", "correct"), ("1.5e3", "incorrect")):
        expect(k, raw, want)
    expect(Num(Decimal(40014), "area", "mm", 3), "4.00e4", "correct")

    ang = Num(Decimal(25), "angle")
    for raw in ("25", "25°", "25 deg", "25 degrees", "25.0", "25º"):
        expect(ang, raw, "correct")
    expect(ang, "25 rad", "incorrect", "degrees")
    expect(ang, "65", "incorrect")

    r8 = Num(Decimal("22.5") * PI / 180, "radian", sig=3, pi=Fraction(1, 8),
             slips=[(Decimal("22.5"), "That's still in degrees. Multiply by π/180.")])
    for raw in ("pi/8", "π/8", "0.393", "0.3927 rad", "(1/8)π", "0.125pi", "1π/8"):
        expect(r8, raw, "correct")
    expect(r8, "22.5", "incorrect", "degrees")
    expect(r8, "pi/4", "incorrect")
    expect(r8, "22.5°", "incorrect", "radians")
    r29 = Num(Decimal("125.2") * PI / 180, "radian", sig=4, pi=Fraction("125.2") / 180)
    for raw in ("313pi/450", "626π/900", "2.185", "2.19"):
        expect(r29, raw, "correct")

    names = Ident([["DBC"], ["EBD"]], 2, "angle", "ABCDE", "∠DBC and ∠EBD")
    for raw in ("∠DBC and ∠EBD", "CBD, DBE", "dbc ebd", "∠ D B C ∠ E B D", "DBCEBD", "angles DBC and EBD"):
        expect(names, raw, "correct")
    expect(names, "∠DBC", "unparsed")
    expect(names, "∠DBC and ∠CBD", "unparsed")
    expect(names, "∠ABD and ∠DBC", "incorrect")
    expect(names, "∠XYZ and ∠DBC", "incorrect", "no point")
    expect(names, "∠DB", "unparsed")
    chord = Ident([["BC"], ["EC"]], 2, "pair", "ABCDEFO", "BC and EC")
    expect(chord, "CB and CE", "correct")
    tri = Ident([["OEC"]], 1, "set3", "ABCDEFO", "ΔOEC", "Δ")
    expect(tri, "ΔCOE", "correct")
    expect(tri, "triangle eco", "correct")
    secant = Ident([["AD", "AB", "BD", "OC"]], 1, "pair", "ABCDEFO", "AD")
    expect(secant, "line DA", "correct")
    expect(secant, "AD and AB", "correct")       # two names for the same line: both right

    f = Sym("p", "4a + 2b", "abh", "perimeter", slips=[("5a + 2b", "Leave out the dashed side.")])
    for raw in ("p = 4a + 2b", "2b+4a", "P = 2(2a + b)", "4*a + 2*b"):
        expect(f, raw, "correct")
    expect(f, "4a + 2b + h", "incorrect")
    expect(f, "5a + 2b", "incorrect", "dashed")
    expect(f, "A = 4a + 2b", "incorrect", "perimeter")
    expect(f, "p = 4a + 2c", "unparsed")
    area = Sym("A", "bh + a^2", "abh", "area")
    for raw in ("A = bh + a²", "a^2 + hb", "a*a + b*h"):
        expect(area, raw, "correct")

    for d, n_, want in (("9.25", 2, "9.3"), ("1559", 3, "1.56 × 10^3"), ("40014", 3, "4.00 × 10^4"), ("340", 2, "340"),
                        ("0.199958", 3, "0.200"), ("76.96", 3, "77.0"), ("4434050.07", 2, "4.4 × 10^6"),
                        ("1238993.88", 4, "1.239 × 10^6"), ("12.8", 2, "13"), ("83.0", 3, "83.0")):
        cases += 1
        check(fmt_sig(Decimal(d), n_) == want, f"fmt_sig({d}, {n_}) = {fmt_sig(Decimal(d), n_)!r}, expected {want!r}")
    for s, want in (("3200", 2), ("16.0", 3), ("0.0952", 3), ("9.200", 4), ("1256", 4), ("60.0", 3), ("340", 2),
                    ("4.00", 3), ("85", 2)):
        cases += 1
        check(sig_figs(s) == want, f"sig_figs({s!r}) = {sig_figs(s)}, expected {want}")
    print(f"  {cases} checker cases")


# ---------------------------------------------------------------- generators

def generator_tests():
    section(f"3. GENERATORS ({N} seeds per kind of problem)")
    for t in GEO.types:
        bad = 0
        for seed in range(N):
            rng = random.Random(seed * 7919 + 1)
            p = json.loads(json.dumps(t.generate(rng)))
            where = f"{t.id} seed {seed} {p}"
            if not t.valid(p):
                check(False, f"{where}: generated givens fail valid()")
                bad += 1
                continue
            sol = t.solve(p)
            a = sol.answer
            q = GEO.question(t, p)
            check(q["text"] and "None" not in q["text"] and "{" not in q["text"] and ".." not in q["text"],
                  f"{where}: odd question text {q['text']!r}")
            check(all(isinstance(s, str) and s for s in sol.steps), f"{where}: empty worked step")
            if q["figure"]:
                vb = q["figure"]["vb"]
                check(vb[2] > 0 and vb[3] > 0 and all(math.isfinite(x) for x in vb), f"{where}: figure box {vb}")
            for k, v in p.items():
                if isinstance(v, str) and v and v[0].isdigit():
                    check(Decimal(v) > 0, f"{where}: given {k} = {v} is not positive")
            if isinstance(a, Num):
                ok = a.value.is_finite() and a.value > 0
                check(ok, f"{where}: answer {a.value}")
                if a.dim == "area":
                    check(a.unit_label.endswith("²"), f"{where}: area unit {a.unit_label}")
                if a.dim == "angle":
                    check(0 < a.value < 360, f"{where}: angle {a.value}")
                check(status(a, a.number()) == "correct", f"{where}: shown {a.shown()} isn't accepted")
            elif isinstance(a, Ident):
                raw = " and ".join(sorted(item)[0] for item in a.items[:a.pick])
                check(status(a, raw) == "correct", f"{where}: right names {raw!r} not accepted")
            else:
                check(status(a, a.shown()) == "correct", f"{where}: formula {a.shown()} not accepted")
            if t.id in ("area_heron",) or (t.id == "perimeter" and p["variant"] == "sides"):
                s = sorted(float(p[k]) for k in ("base", "left", "right"))
                check(s[2] < s[0] + s[1], f"{where}: triangle inequality")
            if t.id == "pythag" and p["given"] != "ab":
                check(float(p["v2"]) > float(p["v1"]), f"{where}: c must be longer than the leg")
            if t.id == "area_isosceles" or (t.id == "perimeter" and p["variant"] == "isosceles"):
                check(float(p["base"]) < 2 * float(p["leg"]), f"{where}: isosceles base too long")
            # tampering: an extra key, a negative given, a huge given
            check(not t.valid({**p, "zzz": 1}), f"{where}: extra key accepted")
            for k, v in p.items():
                if isinstance(v, str) and v[:1].isdigit():
                    check(not t.valid({**p, k: "-" + v}), f"{where}: negative {k} accepted")
                    check(not t.valid({**p, k: "1e99"}), f"{where}: 1e99 for {k} accepted")
        print(f"  {t.section} {t.id:<17} {N - bad}/{N} valid")


# ------------------------------------------------------------------- privacy

def git(*args):
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True)


def privacy_tests():
    section("4. PRIVACY")
    path = "content/private/ch2-textbook.json"
    check(git("check-ignore", "-q", path).returncode == 0, f"{path} is not gitignored")
    check(git("ls-files", "content/private").stdout.strip() == "", "content/private is tracked by git")
    would_add = git("ls-files", "--others", "--exclude-standard").stdout.split()
    check(not any(f.startswith("content/private") for f in would_add), "git add would stage content/private")
    c = server.app.test_client()
    for url in ("/static/../content/private/ch2-textbook.json", "/content/private/ch2-textbook.json",
                "/static/%2e%2e/content/private/ch2-textbook.json"):
        check(c.get(url).status_code == 404, f"{url} is served")
    print("  ignored, untracked, never staged, not served")


# ----------------------------------------------------------------------- API

def api_tests():
    section("5. API")
    c = server.app.test_client()
    ids = [x["id"] for x in c.get("/api/chapters").get_json()]
    check("geometry-ch2" in ids, "geometry chapter missing from /api/chapters")
    d = c.get("/api/chapters/geometry-ch2").get_json()
    check([s["id"] for s in d["sections"]] == ["2.1", "2.2", "2.3", "2.4"], "sections")
    check(all(s["formulas"] and s["flashcards"] and s["types"] for s in d["sections"]), "every section needs content")
    r = c.get("/study/")
    check(r.status_code in (301, 302) and r.headers["Location"].endswith("/#/study"), "/study/ redirect")

    for sec in ("2.1", "2.2", "2.3", "2.4"):
        q = c.post("/api/study/problem", json={"chapter": "geometry-ch2", "section": sec}).get_json()["question"]
        check(q["section"] == sec and "answer" in q and "value" not in json.dumps(q["answer"]), f"{sec}: problem shape")
        body = {"chapter": "geometry-ch2", "type": q["type"], "params": q["params"]}
        rev = c.post("/api/study/reveal", json=body).get_json()
        check(rev["status"] == "revealed" and rev["steps"], f"{sec}: reveal")
        if q["answer"]["kind"] == "number":
            raw = rev["answer"].split(" ≈ ")[-1]
            got = c.post("/api/study/check", json={**body, "answer": raw}).get_json()
            check(got["status"] == "correct", f"{sec}: its own answer {raw!r} graded {got['status']}: {got['message']}")
        check(c.post("/api/study/check", json={**body, "answer": "zzz"}).get_json()["status"] in ("unparsed", "incorrect"),
              f"{sec}: junk answer")

    one = c.post("/api/study/problem", json={"chapter": "geometry-ch2", "section": "2.2", "type": "area_heron"}).get_json()
    check(one["question"]["type"] == "area_heron", "pick one kind")
    check(c.post("/api/study/problem", json={"chapter": "geometry-ch2", "section": "2.1", "type": "area_heron"})
          .status_code == 400, "kind outside its section -> 400")
    check(c.post("/api/study/problem", json={"chapter": "nope", "section": "2.1"}).status_code == 400, "bad chapter -> 400")

    qz = c.post("/api/study/quiz", json={"chapter": "geometry-ch2", "sections": ["2.1", "2.4"], "count": 10}).get_json()
    check(len(qz["questions"]) == 10 and {q["section"] for q in qz["questions"]} == {"2.1", "2.4"}, "quiz: 10 from 2.1 + 2.4")
    check(c.post("/api/study/quiz", json={"chapter": "geometry-ch2", "sections": []}).status_code == 400, "quiz, no sections")

    heron = {"chapter": "geometry-ch2", "type": "area_heron",
             "params": {"base": "415", "left": "239", "right": "322", "unit": "cm", "up": 1}}
    got = c.post("/api/study/check", json={**heron, "answer": "3.84e4 cm^2"}).get_json()
    check(got["status"] == "correct" and got["answer"] == "3.84 × 10^4 cm²", f"check heron: {got}")
    bad = {**heron, "params": {**heron["params"], "right": "999"}}
    check(c.post("/api/study/check", json={**bad, "answer": "1"}).status_code == 400, "impossible triangle -> 400")
    check(c.post("/api/study/check", json={**heron, "type": "nope", "answer": "1"}).status_code == 400, "bad type -> 400")
    check(c.post("/api/study/check", json={**heron, "params": "junk", "answer": "1"}).status_code == 400, "junk -> 400")

    path = GEO.textbook_path
    if GEO.textbook() is not None:
        tb = c.get("/api/study/geometry-ch2/textbook/2.2")
        check(tb.status_code == 200 and len(tb.get_json()["items"]) == 26, "textbook 2.2: 26 items")
    GEO.textbook_path = os.path.join(HERE, "content", "private", "not-here.json")
    try:
        check(c.get("/api/study/geometry-ch2/textbook/2.2").status_code == 404, "textbook without the file -> 404")
        check(c.get("/api/chapters/geometry-ch2").get_json()["textbook"] is False, "detail says no textbook")
    finally:
        GEO.textbook_path = path
    print("  routes, shapes, grading and refusals")


def report():
    section("RESULT")
    if failures:
        print(f"  {len(failures)} FAILURE(S) of {passed[0] + len(failures)} checks:")
        for f in failures[:60]:
            print("   - " + f)
        sys.exit(1)
    print(f"  All {passed[0]} checks passed.")


if __name__ == "__main__":
    fixture_tests()
    checker_tests()
    generator_tests()
    privacy_tests()
    api_tests()
    report()
