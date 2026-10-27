"""Household kWh and Circuit Diagrams: 200 random questions per level, checked for consistency.

    py test_problems.py

For every level of both modules:
  kWh       each row = W × h ÷ 1000, the rows add up to the TOTAL, month = TOTAL × 30,
            cost = month × rate ÷ 100, and hours are on the clean grid
  circuits  V = I × R, and P = V × I = I² × R = V² ÷ R all agree, and the step 1 formula
            from the Ohm's Law Wheel gives the step 1 answer
and in both: no value is negative, absurdly tiny or huge (anything outside RANGES is flagged),
the right answers (3 significant figures, commas, prefixes) are marked correct, common slips
get their own message, questions and hints never show a formula, and the API works end to end.
"""
import math
import random
import sys

import sympy

import app as server
from chapters import BY_ID
from chapters.circuits import TYPES, complete
from chapters.kwh import APPLIANCES, DAYS_PER_MONTH, hour_choices
from core.fmt import fmt_eng, fmt_num
from core.formula import symbol

KWH, CIRCUITS = BY_ID["kwh"], BY_ID["circuits"]
N = 200
# Loose "is this sensible for a textbook problem" ranges. Anything outside is flagged as a failure.
RANGES = {
    "watts": (1, 20_000), "hours": (0.1, 24), "row kWh": (0.01, 50), "TOTAL kWh": (0.01, 200),
    "monthly kWh": (0.3, 6000), "cost $": (0.01, 1000),
    "V": (0.1, 500), "I": (1e-5, 20), "R": (1, 1e7), "P": (1e-4, 3000),
}
ASCII = str.maketrans({"×": "x", "Ω": "ohm", "µ": "u", "÷": "/", "·": "-", "²": "^2", "√": "sqrt", "¢": "c", "−": "-"})
failures, flags = [], []
seen = {k: [math.inf, -math.inf] for k in RANGES}


def a(s):
    return str(s).translate(ASCII)


def fail(msg):
    failures.append(a(msg))


def note(name, x, where):
    lo, hi = RANGES[name]
    s = seen[name]
    s[0], s[1] = min(s[0], x), max(s[1], x)
    if not (math.isfinite(x) and lo <= x <= hi):
        flags.append(a(f"{where}: {name} = {x:g} is outside {lo:g}..{hi:g}"))


def rel(x, y):
    return abs(x - y) <= 1e-9 * max(abs(x), abs(y))


def typed(x):
    """The answer as a student would type it: 3 significant figures, with thousands commas."""
    s = fmt_num(x)
    if "×" in s:
        return s.replace(" × 10^", "e")
    whole, _, frac = s.partition(".")
    return f"{int(whole):,}" + (f".{frac}" if frac else "")


def no_formula(text, where):
    if any(ch in text for ch in "=×÷*/^√²"):
        fail(f"{where}: shows a formula during the question: {text!r}")


def section(title):
    print(f"\n{title}\n" + "-" * 78)


# ----------------------------------------------------------------- kWh

def kwh_level(lv, mode, rng):
    rate = 12
    count = 0
    while count < N:
        for q in KWH.session(lv, mode, rng, {"settings": {"rate": rate}}):
            count += 1
            p, where = q["params"], f"{lv.id} {mode} {q['desc']}"
            no_formula(q["hint"], where + " hint")
            no_formula(q["prompt"], where + " prompt")
            sol = KWH._solve(lv, p)
            val = {x.key: x.value for x in sol.answers}
            rows = p["rows"]
            if p["type"] in ("find-w", "find-h"):
                r = rows[0]
                w = val.get("w0", r.get("watts"))
                h = val.get("h0", r.get("hours"))
                if not rel(w * h / 1000, r["kwh"]):
                    fail(f"{where}: {w} W x {h} h != {r['kwh']} kWh")
                if "w0" in val and not any(rel(w, x.watts) for x in APPLIANCES):
                    fail(f"{where}: rearranged watts {w} isn't an appliance rating")
                note("watts", w, where)
                note("hours", h, where)
                note("row kWh", r["kwh"], where)
            else:
                rowv = [val[f"r{i}"] for i in range(len(rows))]
                for r, e in zip(rows, rowv):
                    if not rel(e, r["watts"] * r["hours"] / 1000):
                        fail(f"{where}: {r['name']} {e} kWh != W x h / 1000")
                    note("watts", r["watts"], where)
                    note("hours", r["hours"], where)
                    note("row kWh", e, where)
                    if mode == "variations":
                        app_ = next(x for x in APPLIANCES if x.name == r["name"])
                        if r["hours"] not in hour_choices(app_.lo, app_.hi):
                            fail(f"{where}: {r['name']} hours {r['hours']} not on the clean grid")
                if "total" in val:
                    if not rel(val["total"], sum(rowv)):
                        fail(f"{where}: TOTAL {val['total']} != sum of rows {sum(rowv)}")
                    note("TOTAL kWh", val["total"], where)
                    if not 3 <= len(rows) <= 6:
                        fail(f"{where}: {len(rows)} rows in a table (want 3 to 6)")
                if "month" in val:
                    if not rel(val["month"], val["total"] * DAYS_PER_MONTH):
                        fail(f"{where}: month {val['month']} != TOTAL x {DAYS_PER_MONTH}")
                    if not rel(val["cost"], val["month"] * p["rate"] / 100):
                        fail(f"{where}: cost {val['cost']} != month x rate / 100")
                    note("monthly kWh", val["month"], where)
                    note("cost $", val["cost"], where)
            # grading: right answers pass, a x10 slip doesn't
            right = {k: (f"${v:,.2f}" if k == "cost" else typed(v)) for k, v in val.items()}
            res = KWH.check(lv, p, right)
            if res["status"] != "correct":
                fail(f"{where}: right answers graded {res['status']}: {[(f['key'], f['message']) for f in res['fields']]}")
            k0 = sol.answers[0].key
            if KWH.check(lv, p, {**right, k0: repr(val[k0] * 10)})["status"] != "incorrect":
                fail(f"{where}: a 10x answer was not marked wrong")
            if count >= N:
                break
    return count


def kwh_slips():
    section("kWh: specific feedback")
    lv = KWH.levels_by_id
    cases = []

    def expect(level, p, answers, key, text, label):
        res = KWH.check(lv[level], p, answers)
        f = next(x for x in res["fields"] if x["key"] == key)
        ok = text.lower() in (f["message"] or "").lower()
        cases.append(ok)
        print(f"  {'ok  ' if ok else 'FAIL'} {label:<52} -> {a(f['message'])}")
        if not ok:
            fail(f"slip '{label}': got {f['status']} {f['message']}")

    tv = {"type": "kwh", "rows": [{"name": "Television", "watts": 250, "hours": 4}]}
    expect("K1", tv, {"r0": "1000"}, "r0", "watt-hours", "forgot to divide by 1000")
    expect("K1", tv, {"r0": "1,000 Wh"}, "r0", "", "typed Wh: converted, 1000 Wh = 1 kWh")
    if KWH.check(lv["K1"], tv, {"r0": "1,000 Wh"})["status"] != "correct":
        fail("1,000 Wh should be accepted as 1 kWh")
    mw = {"type": "kwh-min", "rows": [{"name": "Microwave oven", "watts": 800, "hours": 0.3}]}
    expect("K2", mw, {"r0": "14.4"}, "r0", "minutes", "used minutes as hours")
    rg = {"type": "kwh-kw", "rows": [{"name": "Range", "watts": 12200, "hours": 1.5}]}
    expect("K2", rg, {"r0": "0.0183"}, "r0", "already in kW", "divided kW by 1000 again")
    fh = {"type": "find-h", "rows": [{"name": "Heater", "kwh": 5.288, "watts": 1322}]}
    expect("K3", fh, {"h0": "0.004"}, "h0", "1000 times too small", "find hours, forgot x 1000")
    if KWH.check(lv["K3"], fh, {"h0": "240 min"})["status"] != "correct":
        fail("240 min should be accepted as 4 h")
    table = {"type": "table", "rows": [{"name": "Clock", "watts": 2, "hours": 24},
                                       {"name": "Television", "watts": 250, "hours": 4},
                                       {"name": "Refrigerator", "watts": 500, "hours": 10}]}
    # rows wrong, but the TOTAL adds up the student's own rows
    expect("K4", table, {"r0": "0.48", "r1": "1", "r2": "50", "total": "51.48"}, "total",
           "matches the sum of your own rows", "TOTAL matches own wrong rows")
    monthly = {**table, "type": "monthly", "rate": 12}
    right = {"r0": "0.048", "r1": "1", "r2": "5", "total": "6.048", "month": "181.44"}
    expect("K5", monthly, {**right, "cost": "2177"}, "cost", "cents", "cost given in cents as dollars")
    if KWH.check(lv["K5"], monthly, {**right, "cost": "2177¢"})["status"] != "correct":
        fail("2177¢ should be accepted as $21.77")
    if KWH.check(lv["K5"], monthly, {**right, "cost": "$21.77"})["status"] != "correct":
        fail("$21.77 should be accepted")
    expect("K5", monthly, {**right, "cost": "0.73"}, "cost", "one day", "cost for one day, not 30")
    expect("K5", monthly, {**right, "total": "7", "month": "210", "cost": "25.20"}, "month",
           "matches your own total", "monthly carried from own wrong TOTAL")


def kwh_tests():
    section(f"kWh: {N} random questions per level (and the worksheet)")
    rng = random.Random(42)
    for lv in KWH.levels:
        n = kwh_level(lv, "variations", rng)
        w = kwh_level(lv, "worksheet", rng)
        print(f"  {lv.id} {a(lv.title):<16} {n} variations + {w} worksheet checked")
    kwh_slips()


# ------------------------------------------------------------ circuits

def circuit_level(lv, rng):
    count = 0
    while count < N:
        for q in CIRCUITS.session(lv, None, rng, {}):
            count += 1
            p, t, where = q["params"], q["params"]["type"], f"{lv.id} {q['desc']}"
            no_formula(q["hint"], where + " hint")
            no_formula(q["prompt"], where + " prompt")
            sol = CIRCUITS._solve(lv, p)
            v = complete(t, p)
            V, I, R, P = v["V"], v["I"], v["R"], v["P"]
            for name, x in v.items():
                note(name, x, where)
            if not (rel(V, I * R) and rel(P, V * I) and rel(P, I * I * R) and rel(P, V * V / R)):
                fail(f"{where}: V={V} I={I} R={R} P={P} don't agree")
            for k in p:
                if k != "type" and not rel(p[k], v[k]):
                    fail(f"{where}: given {k} changed")
            unknowns = TYPES[t][1]
            if any(k in p for k in unknowns):
                fail(f"{where}: an answer is in the question data")
            if sum(x is None for x in q["layout"]["labels"].values()) != (1 if t.startswith("find-") else 2):
                fail(f"{where}: wrong number of '?' labels")
            # the step 1 formula from the Ohm's Law Wheel gives the step 1 answer
            f = sol.formula
            got = float(f.expr.subs({symbol(k): sympy.nsimplify(p[k]) for k in f.knowns}))
            if not rel(got, v[f.target]):
                fail(f"{where}: formula {f.display} gives {got}, answer is {v[f.target]}")
            # grading: plain, prefixed and formula
            plain = {x.key: typed(x.value) for x in sol.answers}
            unit = {"I": "A", "V": "V", "R": "ohm", "P": "W"}
            pref = {x.key: fmt_eng(x.value, unit[x.key]).replace("µ", "u") for x in sol.answers}
            for name, ans in (("plain", plain), ("prefixed", pref)):
                res = CIRCUITS.check(lv, p, ans, f.expr_text)
                if res["status"] != "correct" or res["formula"]["status"] != "correct":
                    fail(f"{where}: {name} {ans} -> {res['status']}, formula {res['formula']['status']}")
            k0 = sol.answers[0].key
            res = CIRCUITS.check(lv, p, {**plain, k0: repr(v[k0] * 1000)}, "")
            if res["status"] != "incorrect" or res["formula"]["status"] != "blank":
                fail(f"{where}: 1000x answer not marked wrong (or blank formula not reported)")
            # a wrong formula is reported, never scored
            res = CIRCUITS.check(lv, p, plain, "P/I" if f.key != "V:PI" else "I*R")
            if res["status"] != "correct" or res["formula"]["status"] != "incorrect":
                fail(f"{where}: wrong formula changed the score or wasn't reported")
            if count >= N:
                break
    return count


def circuit_tests():
    section(f"Circuit Diagrams: {N} random questions per level")
    rng = random.Random(7)
    for lv in CIRCUITS.levels:
        n = circuit_level(lv, rng)
        print(f"  {lv.id} {a(lv.title):<16} {n} checked: P = VI = I^2 R = V^2/R, formula, grading")
    lv = CIRCUITS.levels_by_id
    d5 = {"type": "find-I", "V": 12.0, "R": 4700.0}
    for raw in ["2.55 mA", "2.553m", "0.00255", "2.55e-3 A", "2553 uA"]:
        if CIRCUITS.check(lv["D5"], d5, {"I": raw, "P": "30.6 mW"})["status"] != "correct":
            fail(f"D5 12 V / 4.7 kohm: {raw!r} should be correct")
    res = CIRCUITS.check(lv["D5"], d5, {"I": "2.55", "P": "0.0306"})
    if "power of 10" not in (res["fields"][0]["message"] or ""):
        fail(f"D5 forgot the prefix: {res['fields'][0]['message']}")
    seen_types = {q["params"]["type"] for _ in range(20) for q in CIRCUITS.session(lv["D4"], None, random.Random(), {})}
    if seen_types != set(TYPES):
        fail(f"D4 mix is missing kinds: {set(TYPES) - seen_types}")


# ----------------------------------------------------------------- API

def api_tests():
    section("API")
    c = server.app.test_client()

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            fail("API: " + msg)

    mods = c.get("/api/chapters").get_json()
    check([(m["id"], m["type"]) for m in mods] == [("ch2", "worksheet"), ("ohms-wheel", "formula"),
                                                    ("kwh", "problems"), ("circuits", "problems")],
          "home lists Chapter 2, Ohm's Law Wheel, Household kWh, Circuit Diagrams")
    d = c.get("/api/chapters/circuits").get_data(as_text=True)
    check("V = I" not in d and "√" not in d and "I²" not in d, "circuits detail does not leak formulas")
    dk = c.get("/api/chapters/kwh").get_json()
    check(dk["reminder"] and len(dk["appliances"]) == len(APPLIANCES) and dk["settings"][0]["default"] == 12,
          "kWh detail: reminder line, appliance list, rate default 12")
    check(len(c.get("/api/problems/kwh/formulas").get_json()) == 2 and
          c.get("/api/problems/nope/formulas").status_code == 404, "formula sheets (review screens)")

    def session(**body):
        return c.post("/api/problems/session", json=body)

    for mid, levels in (("kwh", ["K1", "K2", "K3", "K4", "K5"]), ("circuits", ["D1", "D2", "D3", "D4", "D5"])):
        for lv in levels:
            r = session(module=mid, level=lv, mode="variations" if mid == "kwh" else None)
            qs = r.get_json()["questions"] if r.status_code == 200 else []
            ok = bool(qs)
            for q in qs:
                rv = c.post("/api/problems/reveal", json={"module": mid, "level": lv, "params": q["params"]}).get_json()
                ans = {f["key"]: f["short"] for f in rv["fields"]}
                res = c.post("/api/problems/check", json={"module": mid, "level": lv, "params": q["params"],
                                                         "answers": ans}).get_json()
                ok = ok and res["status"] == "correct" and rv["status"] == "revealed"
            check(ok, f"{mid} {lv}: session, reveal, and the revealed answers check as correct ({len(qs)} questions)")

    r = session(module="kwh", level="K5", mode="custom", settings={"rate": 15},
                rows=[{"name": "Heater", "watts": 1500, "hours": 2.5}, {"name": "Clock", "watts": 2, "hours": 24}])
    q = r.get_json()["questions"][0] if r.status_code == 200 else {}
    check(q.get("params", {}).get("rate") == 15 and q["params"]["custom"] and len(q["params"]["rows"]) == 2,
          "custom table with edited wattage and the rate setting")
    check(session(module="kwh", level="K4", mode="custom", rows=[{"name": "Clock", "watts": -2, "hours": 1}])
          .status_code == 400, "custom: negative watts -> 400")
    check(session(module="kwh", level="K5", mode="worksheet", settings={"rate": 0}).status_code == 400,
          "rate of 0 -> 400")
    check(session(module="kwh", level="K9", mode="worksheet").status_code == 400, "unknown level -> 400")
    check(session(module="kwh", level="K1", mode="weird").status_code == 400, "unknown mode -> 400")
    body = {"module": "circuits", "level": "D1", "params": {"type": "find-I", "V": 12, "R": 4}}
    check(c.post("/api/problems/check", json={**body, "answers": {"I": "3", "P": "36"}, "formula": "V/R"})
          .get_json()["status"] == "correct", "check: 12 V / 4 ohm -> 3 A, 36 W")
    check(c.post("/api/problems/check", json={**body, "params": {"type": "find-I", "V": -12, "R": 4}})
          .status_code == 400, "negative given -> 400")
    check(c.post("/api/problems/check", json={**body, "params": {"type": "find-I", "V": 12, "R": 4, "I": 3}})
          .status_code == 400, "extra key (an answer) in params -> 400")
    check(c.post("/api/problems/check", json={**body, "level": "D2"}).status_code == 400, "type outside the level -> 400")
    check(c.post("/api/problems/check", json={**body, "params": "junk"}).status_code == 400, "junk params -> 400")
    check(c.post("/api/problems/check", json={**body, "module": "ohms-wheel"}).status_code == 400,
          "problem API rejects the formula module")
    unread = c.post("/api/problems/check", json={**body, "answers": {"I": "abc", "P": "36"}}).get_json()
    check(unread["status"] == "unparsed" and unread["fields"][0]["message"], "unreadable answer -> says why, not graded")


def report():
    section("RANGES SEEN (flagged if outside the sensible range)")
    for k, (lo, hi) in seen.items():
        print(f"  {k:<12} {lo:>12.6g} .. {hi:<12.6g}   allowed {RANGES[k][0]:g} .. {RANGES[k][1]:g}")
    section("RESULT")
    if flags:
        print(f"  {len(flags)} UNREASONABLE VALUE(S):")
        for f in flags[:40]:
            print("   - " + f)
    if failures:
        print(f"  {len(failures)} FAILURE(S):")
        for f in failures[:60]:
            print("   - " + f)
    if flags or failures:
        sys.exit(1)
    print(f"  All passed: {N} questions per level x 10 levels (plus the kWh worksheet), slips, API.")


if __name__ == "__main__":
    kwh_tests()
    circuit_tests()
    api_tests()
    report()
