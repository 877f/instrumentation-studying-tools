"""Grader + API smoke tests. Uses a throwaway progress file, never your real one.

    py test_app.py
"""
import json
import os
import sys
import tempfile

import app as server
import grader
from questions import BY_ID

failures = []


def expect(tid, raw, status, contains=None):
    t = BY_ID[tid]
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
    expect(47, "2.28", "correct")
    expect(47, "2.27", "correct")
    expect(47, "27.3", "incorrect", "inches to feet")
    expect(46, "2080", "correct")
    expect(46, "2.08k", "correct")
    expect(46, "2.08 kcmil", "correct")
    expect(46, "693", "incorrect", "yards to feet")
    for raw in ["240", "240 ft", "80 yd", "2885 in", "240 FT"]:
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
    tmp = tempfile.mkdtemp()
    server.PROGRESS_FILE = os.path.join(tmp, "progress.json")
    c = server.app.test_client()

    def check(cond, msg):
        if not cond:
            failures.append("API: " + msg)

    r = c.get("/")
    check(r.status_code == 200 and b"Chapter 2 Study Tool" in r.data, "index page")
    st = c.get("/api/stats").get_json()
    check(len(st["templates"]) == 54, "stats lists 54 templates")

    ws = c.post("/api/session", json={"mode": "worksheet", "parts": [1, 2, 3, 4, 5], "count": "all"}).get_json()
    qs = ws["questions"]
    check([q["template_id"] for q in qs] == list(range(1, 55)), "worksheet session = 1..54 in order")
    check(all(q["params"] == BY_ID[q["template_id"]].worksheet for q in qs), "worksheet numbers unchanged")

    var = c.post("/api/session", json={"mode": "variations", "parts": [5], "count": 5, "shuffle": True}).get_json()
    check(len(var["questions"]) == 5 and all(q["part"] == 5 for q in var["questions"]), "variations part filter")

    weak = c.post("/api/session", json={"mode": "weak", "parts": [1, 2, 3, 4, 5], "count": 10}).get_json()
    check(len({q["template_id"] for q in weak["questions"]}) == 10, "weak spots gives 10 distinct templates")

    check(c.post("/api/session", json={"mode": "worksheet", "parts": []}).status_code == 400, "no parts -> 400")

    q13 = qs[12]
    body = {"template_id": 13, "params": q13["params"], "uid": "u1", "answer": "9 J"}
    check(c.post("/api/check", json=body).get_json()["status"] == "correct", "check correct")
    c.post("/api/check", json=body)  # same uid again: must not double count
    s = c.get("/api/stats").get_json()["templates"][12]
    check(s["attempts"] == 1 and s["correct"] == 1, f"dedupe by uid (got {s['attempts']}/{s['correct']})")

    c.post("/api/check", json={**body, "uid": "u2", "answer": "90"})
    c.post("/api/check", json={**body, "uid": "u3", "answer": "??"})       # unparsed: not counted
    c.post("/api/reveal", json={"template_id": 13, "params": q13["params"], "uid": "u4"})
    s = c.get("/api/stats").get_json()["templates"][12]
    check(s["attempts"] == 3 and s["correct"] == 1 and s["last_correct"] is False and s["last_seen"],
          f"miss + reveal recorded, unparsed ignored (got {s})")

    check(c.post("/api/check", json={"template_id": 13, "params": {"V": 0, "N": 1}, "answer": "1"}).status_code == 400,
          "bad params -> 400")

    # Weak spots should now favour #13 inside Part 2.
    for i in range(6):
        c.post("/api/check", json={**body, "uid": f"m{i}", "answer": "1"})
    hits = sum(13 in [q["template_id"] for q in
                      c.post("/api/session", json={"mode": "weak", "parts": [2], "count": 3}).get_json()["questions"]]
               for _ in range(60))
    check(hits >= 40, f"weak spots favours missed template (#13 picked in {hits}/60 sessions)")

    c.post("/api/session/complete", json={"mode": "worksheet", "answered": 3, "correct": 1, "missed": [13, 27]})
    with open(server.PROGRESS_FILE, encoding="utf-8") as f:
        saved = json.load(f)
    check(saved["templates"]["13"]["attempts"] == 9 and len(saved["sessions"]) == 1, "progress.json contents")

    c.post("/api/progress/reset", json={})
    check(c.get("/api/stats").get_json()["templates"][12]["attempts"] == 0, "reset clears stats")


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
