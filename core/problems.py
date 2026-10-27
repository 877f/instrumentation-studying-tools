"""Problem sets (module type "problems"), e.g. Household kWh and Circuit Diagrams.

A problem has one or more answer boxes: the rows and TOTAL of an appliance table, or
"find I" then "find P" for a circuit diagram. Every box is graded by the worksheet grader
(core/grader.py), so prefixes, commas, the 1% tolerance, 3-significant-figure answers and
the wrong-answer diagnosis all work as in Chapter 2. The optional "Formula used" box is
checked by the formula checker (core/formula.py) and never changes the score.

A module is content plus a few plain functions (see chapters/kwh.py and chapters/circuits.py):
  generate(level, mode, rng, settings) -> [params]   one dict of givens per question
  valid(level, params) -> bool                        params come back from the browser, so check them
  view(level, params) -> dict                         prompt, hint, short description, table or diagram
  solve(level, params) -> Solution                    answers, worked solution, notes
  custom(level, body, settings) -> params             only for a module with a Custom mode; ValueError if bad
"""
import math
import random
import re

from core import grader
from core.fmt import fmt_answer, fmt_num
from core.template import Kind, Template
from core.units import QUANTITIES


class Level:
    def __init__(self, id, title, desc):
        self.id = id                  # "K1": shown as a bubble with K above 1
        self.title = title
        self.desc = desc


class Mode:
    def __init__(self, id, label, help):
        self.id = id                  # "worksheet", "variations" or "custom"
        self.label = label
        self.help = help


class Setting:
    """A number the student can change on the module page, e.g. the electricity rate."""

    def __init__(self, key, label, unit, default, lo, hi):
        self.key = key
        self.label = label
        self.unit = unit
        self.default = default
        self.lo, self.hi = lo, hi


class Answer:
    """One answer box and its right value."""

    def __init__(self, key, label, quantity, value, miss, slips=(), shown=None, short=None, carry=None):
        self.key = key                # "r0", "total", "I"
        self.label = label            # "Television", "TOTAL kWh", "Step 1 · Current I"
        self.quantity = quantity      # key in core.units.QUANTITIES
        self.value = value
        self.miss = miss              # how a miss is listed in the session summary
        self.slips = slips            # [(ratio, message)]: your answer ÷ right answer ≈ ratio -> that message
        self.shown = shown            # fn(value) -> text, when 3 significant figures with the unit don't fit
        self.short = short            # fn(value) -> text for a narrow table cell (default: 3 significant figures)
        self.carry = carry            # (fn({key: your value}) -> value, [keys], message): it follows from
                                      # your own earlier answers, even though those are wrong


class Solution:
    def __init__(self, answers, steps, headline, notes=(), formula=None):
        self.answers = answers        # [Answer], in the order the boxes appear
        self.steps = steps            # the worked solution, shown after checking
        self.headline = headline      # the answer in one line, for the verdict
        self.notes = list(notes)      # extra lines under the worked solution
        self.formula = formula        # core.formula.Formula for the optional "Formula used" box, or None


def _template(a):
    """A one-off worksheet template, so grader.check() grades this box like any worksheet answer."""
    kind = Kind(a.quantity, {}, "", None, lambda p, cfg: (a.value, []))
    return Template(a.key, 0, "", kind, {})


def _prep(raw, quantity):
    """$12.50 -> "12.50 $": the grader reads the number first, then the unit."""
    if quantity == "cost":
        m = re.match(r"^\s*\$\s*(.*)$", raw)
        if m:
            return f"{m.group(1)} $"
    return raw


class ProblemModule:
    type = "problems"

    def __init__(self, id, title, badge, intro, levels, generate, valid, view, solve,
                 modes=(), settings=(), custom=None, reminder=None, formulas=(), checker=None, extra=None):
        self.id = id
        self.title = title
        self.badge = badge            # short text on the home-screen meter, e.g. "kWh"
        self.intro = intro
        self.reminder = reminder      # one line on the module page (never during questions), or None
        self.levels = levels
        self.modes = list(modes)      # [Mode]; empty means no mode picker
        self.settings = list(settings)
        self.formulas = list(formulas)   # formula sheet for review screens: [{"title", "items": [...]}]
        self.checker = checker        # FormulaModule whose check_symbolic() grades the "Formula used" box
        self.extra = extra or {}      # more data for the module page, e.g. the appliance list for Custom
        self.levels_by_id = {lv.id: lv for lv in levels}
        self._generate, self._valid, self._view, self._solve, self._custom = generate, valid, view, solve, custom
        assert len(self.levels_by_id) == len(levels), f"{id}: duplicate level ids"
        self._self_check()

    def _self_check(self):
        """Every generated question must pass valid() and solve to positive numbers (catches data-file typos)."""
        rng = random.Random(1)
        defaults = {s.key: s.default for s in self.settings}
        modes = [m.id for m in self.modes if m.id != "custom"] or [None]
        for lv in self.levels:
            for mode in modes:
                for p in self._generate(lv, mode, rng, defaults):
                    assert self._valid(lv, p), f"{self.id} {lv.id}: generated question fails valid(): {p}"
                    for a in self._solve(lv, p).answers:
                        assert math.isfinite(a.value) and a.value > 0, f"{self.id} {lv.id}: {a.key} = {a.value} in {p}"

    # -- API shapes ---------------------------------------------------------

    def summary(self):
        modes = " / ".join(m.label for m in self.modes if m.id != "custom")
        return {"id": self.id, "type": self.type, "title": self.title, "badge": self.badge,
                "question_count": len(self.levels),
                "subtitle": f"{len(self.levels)} levels" + (f" · {modes}" if modes else "")}

    def detail(self):
        return {**self.summary(), "intro": self.intro, "reminder": self.reminder,
                "levels": [{"id": lv.id, "title": lv.title, "desc": lv.desc} for lv in self.levels],
                "modes": [{"id": m.id, "label": m.label, "help": m.help} for m in self.modes],
                "settings": [{"key": s.key, "label": s.label, "unit": s.unit, "default": s.default,
                              "min": s.lo, "max": s.hi} for s in self.settings],
                **self.extra}

    def read_settings(self, raw):
        raw = raw if isinstance(raw, dict) else {}
        out = {}
        for s in self.settings:
            v = raw.get(s.key, s.default)
            if not (isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and s.lo <= v <= s.hi):
                raise ValueError(f"{s.label} must be a number from {s.lo:g} to {s.hi:g} {s.unit}.")
            out[s.key] = v
        return out

    def session(self, level, mode, rng, body):
        settings = self.read_settings(body.get("settings"))
        if self.modes and mode not in {m.id for m in self.modes}:
            raise ValueError("Unknown mode.")
        if mode == "custom":
            params = [self._custom(level, body, settings)]
        else:
            params = self._generate(level, mode, rng, settings)
        return [self.question(level, p) for p in params]

    def valid(self, level, params):
        try:
            return bool(self._valid(level, params))
        except (TypeError, KeyError, AttributeError):
            return False

    def question(self, level, params):
        sol = self._solve(level, params)
        f = sol.formula
        return {"module": self.id, "level": level.id, "params": params, **self._view(level, params),
                "fields": [{"key": a.key, "label": a.label, "unit": QUANTITIES[a.quantity].unit} for a in sol.answers],
                "formula": {"target": f.target, "knowns": list(f.knowns)} if f else None}

    # -- checking -----------------------------------------------------------

    @staticmethod
    def _shown(a, value):
        return a.shown(value) if a.shown else fmt_answer(value, a.quantity)

    @staticmethod
    def _short(a, value):
        return a.short(value) if a.short else fmt_num(value)

    def _field(self, a, status):
        return {"key": a.key, "label": a.label, "miss": a.miss, "status": status, "message": None, "read_as": None,
                "correct_answer": self._shown(a, a.value), "short": self._short(a, a.value)}

    def _grade(self, a, raw):
        """-> (field result, your value in a's unit or None)."""
        raw = _prep(raw, a.quantity)
        g = grader.check(_template(a), {}, raw)
        out = self._field(a, g["status"])
        out.update(message=g["message"], read_as=g["read_as"])
        if g["status"] == "unparsed":
            return out, None
        parsed = grader.parse(raw, a.quantity)
        if parsed.unit_q not in (None, a.quantity):
            return out, None
        if a.shown:
            out["read_as"] = a.shown(parsed.value)
        if g["status"] == "incorrect" and parsed.value > 0:
            hit = next((msg for ratio, msg in a.slips if grader.close(parsed.value / a.value, ratio)), None)
            if hit:
                out["message"] = hit
        return out, parsed.value

    @staticmethod
    def _result(sol, status):
        return {"status": status, "headline": sol.headline, "steps": list(sol.steps), "notes": list(sol.notes),
                "fields": [], "formula": None}

    def check(self, level, params, answers, formula_raw=""):
        sol = self._solve(level, params)
        res = self._result(sol, None)
        fields, values = {}, {}
        for a in sol.answers:
            fields[a.key], v = self._grade(a, str(answers.get(a.key, ""))[:200])
            if v is not None:
                values[a.key] = v
        for a in sol.answers:
            f = fields[a.key]
            if a.carry and f["status"] == "incorrect" and a.key in values:
                fn, deps, msg = a.carry
                if (all(d in values for d in deps) and any(fields[d]["status"] == "incorrect" for d in deps)
                        and grader.close(values[a.key], fn(values))):
                    f["message"] = msg
        res["fields"] = [fields[a.key] for a in sol.answers]
        statuses = {f["status"] for f in res["fields"]}
        res["status"] = "unparsed" if "unparsed" in statuses else "correct" if statuses == {"correct"} else "incorrect"
        if res["status"] != "unparsed":
            res["formula"] = self._formula(sol, formula_raw)
        return res

    def _formula(self, sol, raw):
        """The optional "Formula used" box. Reported, never scored."""
        f = sol.formula
        if f is None:
            return None
        if not raw.strip():
            return {"status": "blank", "message": None, "read_as": None, "reminder": None, "correct_formula": f.display}
        r = self.checker.check_symbolic(f, raw)
        return {"status": r["status"], "message": r["message"], "read_as": r["read_as"], "reminder": r["reminder"],
                "correct_formula": f.display}

    def reveal(self, level, params):
        sol = self._solve(level, params)
        res = self._result(sol, "revealed")
        res["fields"] = [self._field(a, "revealed") for a in sol.answers]
        if sol.formula is not None:
            res["formula"] = {"status": "revealed", "message": None, "read_as": None, "reminder": None,
                              "correct_formula": sol.formula.display}
        return res
