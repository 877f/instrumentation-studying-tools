"""Grader + API smoke tests.

    py test_app.py
"""
import sys

import app as server
from chapters import BY_ID as CHAPTERS
from core import grader

CH2 = CHAPTERS["ch2"]
failures = []


def expect(tid, raw, status, contains=None):
    t = CH2.by_id[tid]
    res = grader.check(t, t.worksheet, raw)
    ok = res["status"] == status and (contains is None or contains.lower() in (res["message"] or "").lower())
    if not ok:
        failures.append(f"#{tid} {raw!r}: expected {status}{' + ' + repr(contains) if contains else ''}, "
                        f"got {res['status']}: {res['message']}")
    return res


def grader_tests():
    # number formats and prefixes
    for raw in ["40k", "40 kohm", "40kΩ", "4e4", "40000", "40,000", "40 KOHM", "4 x 10^4", "4×10⁴", "40 kilohms"]:
        expect(41, raw, "correct")
    for raw in ["2M", "2 megohms", "2 meg", "2e6 ohms", "2 MΩ"]:
        expect(42, raw, "correct")
    expect(42, "2 mohm", "incorrect", "prefix case slip")
    expect(41, "40", "incorrect", "power of 10")
    expect(41, "40", "incorrect", "40 kohm")
    for raw in ["556 uA", "556µA", "0.556 mA", "5.56e-4", "5.56 x 10^-4 A", "556 micro amps"]:
        expect(27, raw, "correct")
    expect(27, "556", "incorrect", "556 uA")
    expect(27, "0.556", "incorrect", "power of 10")
    expect(27, "0.0333", "incorrect", "not 60 s")              # used 60 s per hour
    expect(24, "2", "correct")
    expect(24, "120", "incorrect", "minutes")
    # Part 1 / electrons
    for raw in ["1", "1 C", "1 c", "1 coulomb"]:
        expect(1, raw, "correct")
    expect(1, "6.25e18", "incorrect", "electrons and coulombs")
    for raw in ["5e19", "5 x 10^19 electrons", "5×10¹⁹", "5*10^19", "5.0E+19"]:
        expect(4, raw, "correct")
    expect(4, "8", "incorrect", "electrons and coulombs")
    expect(4, "8 C", "incorrect", "wrong kind of unit")
    # #32 ambiguity: both readings accepted, the coulomb one with a note
    expect(32, "2.03e23", "correct")
    r = expect(32, "32400", "correct", "other reading")
    if not r["alternate"]:
        failures.append("#32 '32400' should be flagged as the alternate reading")
    expect(32, "32400 C", "correct", "other reading")
    expect(32, "32400 V", "incorrect", "wrong kind of unit")
    # Part 4
    for raw in ["5 mS", "5 ms", "0.005", "5m", "5 mmho", "0.005 siemens"]:
        expect(35, raw, "correct")
    expect(35, "200", "incorrect", "reciprocal")
    expect(35, "5", "incorrect", "5 mS")
    expect(35, "5 MS", "incorrect", "prefix case slip")
    # time answers: seconds, any case, other time units converted
    for raw in ["0.25", "250 ms", "0.25 S", "0.25 sec"]:
        expect(26, raw, "correct")
    # Part 5: tolerance and conversions
    # ρ = 10.37: #47 = 2.2684 Ω, #46 = 2074 CM, #45 = 241.08 ft
    expect(47, "2.27", "correct")
    expect(47, "2.268", "correct")
    expect(47, "27.2", "incorrect", "inches to feet")
    expect(46, "2074", "correct")
    expect(46, "2.07k", "correct")
    expect(46, "2.07 kcmil", "correct")
    expect(46, "691", "incorrect", "yards to feet")
    for raw in ["241", "241 ft", "80.4 yd", "2893 in", "241 FT"]:
        expect(45, raw, "correct")
    expect(18, "17.1", "correct")
    # wrong / unreadable
    expect(9, "6 A", "incorrect", "wrong kind of unit")
    expect(9, "-6", "incorrect", "wrong sign")
    expect(9, "6.2", "incorrect", "close")
    expect(9, "6.5", "incorrect", "not within 1%")
    expect(9, "abc", "unparsed")
    expect(9, "", "unparsed")
    expect(9, "6 zz", "unparsed", "unit")


def api_tests():
    c = server.app.test_client()

    def check(cond, msg):
        if not cond:
            failures.append("API: " + msg)

    r = c.get("/")
    check(r.status_code == 200 and b"Instrumentation Nation" in r.data, "index page")
    check(c.get("/static/app.js").status_code == 200 and c.get("/static/app.css").status_code == 200, "static files")
    r = c.get("/healthz")
    check(r.status_code == 200 and r.data == b"ok", "healthz")

    chapters = c.get("/api/chapters").get_json()
    check([(ch["id"], ch["type"]) for ch in chapters][:2] == [("ch2", "worksheet"), ("ohms-wheel", "formula")]
          and chapters[0]["question_count"] == 54, "module list: chapter 2, then the Ohm's Law Wheel")
    d = c.get("/api/chapters/ch2").get_json()
    check(len(d["templates"]) == 54 and set(d["parts"]) == {"1", "2", "3", "4", "5"} and d["formulas"], "chapter detail")
    check(c.get("/api/chapters/nope").status_code == 404, "unknown chapter -> 404")

    def session(**body):
        return c.post("/api/session", json={"chapter": "ch2", **body})

    qs = session(mode="worksheet", parts=[1, 2, 3, 4, 5], count="all").get_json()["questions"]
    check([q["template_id"] for q in qs] == list(range(1, 55)), "worksheet session = 1..54 in order")
    check(all(q["params"] == CH2.by_id[q["template_id"]].worksheet for q in qs), "worksheet numbers unchanged")
    check(all(q["chapter"] == "ch2" for q in qs), "questions carry their chapter")

    var = session(mode="variations", parts=[5], count=5, shuffle=True).get_json()["questions"]
    check(len(var) == 5 and all(q["part"] == 5 for q in var), "variations part filter")
    weak = session(mode="weak", parts=[1, 2, 3, 4, 5], count=10).get_json()["questions"]
    check(len({q["template_id"] for q in weak}) == 10, "weak spots gives 10 distinct templates")
    ids = session(mode="variations", template_ids=[13, 27], count="all").get_json()["questions"]
    check(sorted(q["template_id"] for q in ids) == [13, 27], "template_ids session (retry missed)")
    check(session(mode="worksheet", parts=[]).status_code == 400, "no parts -> 400")
    check(c.post("/api/session", json={"chapter": "nope", "parts": [1]}).status_code == 400, "bad chapter -> 400")

    q13 = qs[12]
    body = {"chapter": "ch2", "template_id": 13, "params": q13["params"]}
    check(c.post("/api/check", json={**body, "answer": "9 J"}).get_json()["status"] == "correct", "check correct")
    check(c.post("/api/check", json={**body, "answer": "90"}).get_json()["status"] == "incorrect", "check wrong")
    check(c.post("/api/reveal", json=body).get_json()["status"] == "revealed", "reveal")
    check(c.post("/api/check", json={**body, "params": {"V": 0, "N": 1}, "answer": "1"}).status_code == 400,
          "bad params -> 400")
    check(c.post("/api/check", json={**body, "chapter": "nope", "answer": "9"}).status_code == 400,
          "check with bad chapter -> 400")

    # Weak spots should favour #13 inside Part 2 when the browser reports it as missed.
    stats = {"13": {"attempts": 7, "correct": 1, "last_correct": False}}
    hits = sum(13 in [q["template_id"] for q in
                      session(mode="weak", parts=[2], count=3, stats=stats).get_json()["questions"]]
               for _ in range(60))
    check(hits >= 40, f"weak spots favours missed template (#13 picked in {hits}/60 sessions)")
    check(session(mode="weak", parts=[2], count=3, stats={"x": "junk", "5": None}).status_code == 200,
          "junk stats ignored")
    formula_api_tests(c, check)


def formula_api_tests(c, check):
    """The Ohm's Law Wheel endpoints, and that the two module types don't cross."""
    d = c.get("/api/chapters/ohms-wheel")
    check(d.status_code == 200 and len(d.get_json()["levels"]) == 5 and len(d.get_json()["quadrants"]) == 4,
          "wheel detail: 5 levels, 4 quadrants")
    check("√" not in d.get_data(as_text=True) and "V / R" not in d.get_data(as_text=True),
          "wheel detail does not leak the formulas")
    sizes = []
    for lv in range(1, 6):
        qs = c.post("/api/formula/session", json={"module": "ohms-wheel", "level": lv}).get_json()["questions"]
        sizes.append(len(qs))
    check(sizes == [3, 2, 6, 12, 12], f"questions per level (got {sizes})")

    def fcheck(key, answer, level=4, **extra):
        return c.post("/api/formula/check", json={"module": "ohms-wheel", "level": level, "key": key,
                                                  "answer": answer, **extra}).get_json()

    check(fcheck("R:PI", "P/I^2")["status"] == "correct", "formula check correct")
    check("only allows" in fcheck("I:VR", "P/V")["message"], "formula check wrong variable")
    check(fcheck("I:VR", "V//R")["status"] == "unparsed", "formula check unreadable")
    q5 = c.post("/api/formula/question", json={"module": "ohms-wheel", "level": 5, "key": "I:VR"}).get_json()["question"]
    check(set(q5["params"]) == {"V", "R"} and q5["unit"] == "A", "numeric question")
    value = q5["params"]["V"] / q5["params"]["R"]
    check(fcheck("I:VR", repr(value), level=5, params=q5["params"])["status"] == "correct", "numeric check correct")
    check(c.post("/api/formula/check", json={"module": "ohms-wheel", "level": 5, "key": "I:VR", "answer": "1",
                                             "params": {"V": -1, "R": 2}}).status_code == 400, "numeric bad params -> 400")
    check(c.post("/api/formula/check", json={"module": "ohms-wheel", "level": 1, "key": "P:IR",
                                             "answer": "I^2R"}).status_code == 400, "key outside the level -> 400")
    r = c.post("/api/formula/reveal", json={"module": "ohms-wheel", "level": 3, "key": "P:IR"}).get_json()
    check(r["status"] == "revealed" and r["steps"], "reveal shows the derivation")
    b = c.post("/api/formula/blank", json={"module": "ohms-wheel", "answers": {"P": ["VI", "I²R", "V²/R"]}}).get_json()
    check(b["score"] == 3 and b["total"] == 12 and len(b["wheel"]["quadrants"]) == 4, "blank wheel grading")
    w = c.get("/api/formula/ohms-wheel/wheel").get_json()
    check(sum(len(q["formulas"]) for q in w["quadrants"]) == 12, "wheel review")
    check(c.post("/api/session", json={"chapter": "ohms-wheel", "parts": [1]}).status_code == 400,
          "worksheet session rejects the formula module")
    check(c.post("/api/formula/session", json={"module": "ch2", "level": 1}).status_code == 400,
          "formula session rejects a worksheet chapter")


def main():
    grader_tests()
    api_tests()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print("  - " + f.translate(str.maketrans({"Ω": "ohm", "µ": "u", "×": "x"})).encode("ascii", "replace").decode())
        sys.exit(1)
    print("All grader and API tests passed.")


if __name__ == "__main__":
    main()
