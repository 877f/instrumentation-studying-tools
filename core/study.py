"""Study-guide chapters (module type "study"), e.g. Geometry, Chapter 2.

A chapter is a folder in content/study/, found at startup: adding one needs no code changes.
  chapter.json   title, sections, formula cards and flashcards
  problems.py    TYPES: one Type per kind of problem, a generator for fresh givens plus a solver,
                 so every answer key is code (content/study/geometry-ch2/problems.py is the example)

The textbook's own exercises never go in the repo, which is public. chapter.json may name a file
in content/private/ (gitignored, so the hosted site never has it). When that file is there, the
"Textbook set" mode reads it; when it isn't, the mode doesn't appear. Its items run through the
same solvers, so the answer key is still code.
"""
import importlib.util
import json
import math
import os
import random
import re
import sys
from decimal import Decimal

from core import answers
from core.answers import Ident, Num, Sym

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(BASE, "content", "study")
PRIVATE = os.path.join(BASE, "content", "private")
MAX_GIVEN = 16          # longest given, in characters
QUIZ_MAX = 40


class Solution:
    def __init__(self, answer, steps, notes=()):
        self.answer = answer          # core.answers Num, Ident or Sym
        self.steps = list(steps)      # the worked steps, shown when asked for
        self.notes = list(notes)


class Type:
    """One kind of problem.
      generate(rng) -> params          fresh givens, as JSON-safe values
      valid(params) -> bool            params come back from the browser, so check all solve() relies on
      view(params) -> {"text", "hint", "figure"}
      solve(params) -> Solution
    Measured givens are strings ("16.0") because their trailing zeros set the significant figures."""

    def __init__(self, id, section, title, generate, valid, view, solve, quiz=True):
        self.id = id
        self.section = section
        self.title = title
        self.generate = generate
        self._valid = valid
        self.view = view
        self.solve = solve
        self.quiz = quiz              # False keeps it out of Quiz mode

    def valid(self, params):
        if not isinstance(params, dict) or len(params) > 20:
            return False
        try:
            return bool(self._valid(params))
        except (TypeError, KeyError, ValueError, AttributeError, ArithmeticError):
            return False


# -------------------------------------------- helpers for problems.py files

def given(params, key, lo="0", hi="1e7"):
    """A measured given as a Decimal: a plain positive decimal string in (lo, hi]. ValueError otherwise."""
    s = params[key]
    if not (isinstance(s, str) and len(s) <= MAX_GIVEN and re.fullmatch(r"\d+(?:\.\d+)?|\.\d+", s)):
        raise ValueError(key)
    d = Decimal(s)
    if not (Decimal(lo) < d <= Decimal(hi)):
        raise ValueError(key)
    return d


def whole(params, key, lo, hi):
    v = params[key]
    if not (isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi):
        raise ValueError(key)
    return v


def choice(params, key, options):
    v = params[key]
    if v not in options:
        raise ValueError(key)
    return v


def keys(params, *names):
    if set(params) != set(names):
        raise ValueError("keys")
    return True


def sig(*givens):
    """Significant figures for the answer: the fewest among the measured givens."""
    return min(answers.sig_figs(g) for g in givens)


def meas(rng, lo, hi, figures):
    """A measured value between lo and hi (spread evenly on a log scale), written to `figures`
    significant figures with trailing zeros kept: 16.0, 9.200, 0.0952. Never fewer than 2 figures."""
    for _ in range(50):
        x = math.exp(rng.uniform(math.log(lo), math.log(hi)))
        r = answers.round_sig(Decimal(repr(x)), figures)
        e = r.adjusted()
        s = f"{r:.{max(0, figures - 1 - e)}f}"
        if answers.sig_figs(s) >= 2 and Decimal(s) > 0:
            return s
    raise RuntimeError("meas: no value found")


def approx(x, figures):
    """x written to `figures` significant figures, like meas(), or None when that leaves fewer than 2
    (4000 can't show 3 figures). Generators retry with new numbers on None."""
    r = answers.round_sig(Decimal(repr(float(x))), figures)
    s = f"{r:.{max(0, figures - 1 - r.adjusted())}f}"
    return s if answers.sig_figs(s) >= 2 and Decimal(s) > 0 else None


def pick_letters(rng, n, pool="ABCDEFGHJKLMNPRSTUVWXYZ"):
    return "".join(rng.sample(pool, n))


# ----------------------------------------------------------------- chapters

def _shape(a):
    """What the answer box needs to know: never the answer itself."""
    if isinstance(a, Num):
        if a.dim == "radian":
            return {"kind": "number", "placeholder": "Radians: 0.393 or pi/8", "unit": "rad",
                    "keys": [["π", "π"], ["/", "/"]], "formats": "A decimal or a π form: 0.393, pi/8, π/8, 313pi/450"}
        if a.dim == "angle":
            return {"kind": "number", "placeholder": "Angle in degrees", "unit": "°",
                    "keys": [["°", "°"]], "formats": "Degrees: 25, 25° or 25 deg"}
        what = "Area" if a.dim == "area" else "Length"
        return {"kind": "number", "placeholder": f"{what} in {a.unit_label}", "unit": a.unit_label,
                "keys": [["×10^", "x10^"], [a.unit_label, a.unit_label]],
                "formats": "Unit optional · 1.73e3 = 1.73 x 10^3 · within 0.5 % or rounded right"}
    if isinstance(a, Ident):
        sym = "∠" if a.name_kind == "angle" else "Δ" if a.prefix == "Δ" else None
        k = ([[sym, sym]] if sym else []) + [["and", " and "]]
        n = "two names" if a.pick == 2 else "a name"
        example = {"angle": "∠ABC", "set3": f"{a.prefix}ABC", "pair": "AB", "point": "A"}[a.name_kind]
        return {"kind": "names", "placeholder": f"Type {n}, like {example}", "unit": None, "keys": k,
                "formats": "Order of the end letters and case don't matter: ∠ABD = ∠DBA, CB = BC"}
    letters = ", ".join(a.letter_list)
    return {"kind": "formula", "placeholder": f"{a.target} = ...", "unit": None,
            "keys": [["²", "²"], ["(", "("], [")", ")"]],
            "formats": f"Use the letters {letters}. Leave out the dashed lines."}


class StudyChapter:
    type = "study"

    def __init__(self, folder, private_dir=PRIVATE):
        with open(os.path.join(folder, "chapter.json"), encoding="utf-8") as f:
            meta = json.load(f)
        self.folder = folder
        self.id = meta["id"]
        self.number = meta.get("number")
        self.title = meta["title"]
        self.name = meta.get("name", self.title)
        self.kicker = meta.get("kicker", "")
        self.tag = meta.get("tag", "")
        self.intro = meta.get("intro", "")
        self.sections = meta["sections"]
        self.section_ids = [s["id"] for s in self.sections]
        mod_name = "study_" + re.sub(r"\W", "_", self.id)
        spec = importlib.util.spec_from_file_location(mod_name, os.path.join(folder, "problems.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod   # so the --dev reloader notices edits to it
        spec.loader.exec_module(mod)
        self.types = list(mod.TYPES)
        self.by_type = {t.id: t for t in self.types}
        assert len(self.by_type) == len(self.types), f"{self.id}: duplicate type ids"
        assert all(t.section in self.section_ids for t in self.types), f"{self.id}: type in an unknown section"
        self.textbook_path = os.path.join(private_dir, meta["textbook"]) if meta.get("textbook") else None
        self._tb = (None, None)
        self._self_check()

    def _self_check(self):
        """Every generated problem must pass valid(), and its own answer must grade as right (catches typos)."""
        rng = random.Random(1)
        for t in self.types:
            for _ in range(12):
                p = t.generate(rng)
                assert t.valid(json.loads(json.dumps(p))), f"{self.id} {t.id}: generated params fail valid(): {p}"
                a = t.solve(p).answer
                if isinstance(a, Num):
                    assert a.value.is_finite() and a.value > 0, f"{self.id} {t.id}: answer {a.value} for {p}"
                    assert a.check(a.number())["status"] == "correct", f"{self.id} {t.id}: {a.shown()} fails itself"

    # -- the private textbook set --------------------------------------------

    def textbook(self):
        """The private exercises as a dict, or None when the file isn't there (always, on the hosted site)."""
        path = self.textbook_path
        if not path or not os.path.isfile(path):
            return None
        mtime = os.stat(path).st_mtime
        if self._tb[0] != mtime:
            with open(path, encoding="utf-8") as f:
                self._tb = (mtime, json.load(f))
        return self._tb[1]

    def textbook_items(self, section):
        data = self.textbook()
        if data is None:
            return None
        out = []
        for item in data.get("items", []):
            if item.get("section") != section:
                continue
            label = f"#{item['number']}"
            t = self.by_type.get(item.get("type"))
            if item.get("pending") or t is None or not t.valid(item.get("params")):
                out.append({"label": label, "pending": True, "text": item.get("text", ""),
                            "figure_name": item.get("figure_name")})
                continue
            q = self.question(t, item["params"], text=item.get("text"), label=label)
            out.append({"label": label, "pending": False, "question": q, "figure_name": item.get("figure_name")})
        return out

    # -- API shapes ------------------------------------------------------------

    def summary(self):
        return {"id": self.id, "type": self.type, "title": self.title, "name": self.name, "number": self.number,
                "kicker": self.kicker, "tag": self.tag, "section_count": len(self.sections),
                "type_ids": [t.id for t in self.types],
                "subtitle": f"{len(self.sections)} sections · {len(self.types)} kinds of problem"}

    def detail(self):
        tb = self.textbook()
        counts = {}
        for item in (tb or {}).get("items", []):
            counts[item.get("section")] = counts.get(item.get("section"), 0) + 1
        return {**self.summary(), "intro": self.intro, "textbook": tb is not None,
                "sections": [{**{k: s.get(k) for k in ("id", "title", "topics", "formulas", "flashcards")},
                              "types": [{"id": t.id, "title": t.title} for t in self.types if t.section == s["id"]],
                              "textbook": counts.get(s["id"], 0)} for s in self.sections]}

    def question(self, t, params, text=None, label=None):
        v = t.view(params)
        text = re.sub(r"\.\.(?=\s|$)", ".", text or v["text"])     # "sides of 2.46 in.." -> "in."
        return {"chapter": self.id, "section": t.section, "type": t.id, "type_title": t.title, "params": params,
                "text": text, "hint": v.get("hint"), "figure": v.get("figure"), "label": label,
                "answer": _shape(t.solve(params).answer)}

    # -- sessions ------------------------------------------------------------

    def problem(self, section, type_id, rng, avoid=None):
        if type_id is not None:
            t = self.by_type.get(type_id)
            if t is None or t.section != section:
                raise ValueError("No such problem type in this section.")
        else:
            pool = [t for t in self.types if t.section == section]
            if not pool:
                raise ValueError("No such section.")
            t = rng.choice([x for x in pool if x.id != avoid] or pool)
        return self.question(t, t.generate(rng))

    def quiz(self, sections, count, rng):
        """`count` problems, round-robin over the chosen sections so each gets its share, types shuffled."""
        decks = {s: [t for t in self.types if t.section == s and t.quiz] for s in sections}
        decks = {s: d for s, d in decks.items() if d}
        if not decks:
            raise ValueError("Pick at least one section.")
        order = list(decks)
        rng.shuffle(order)
        queues = {s: [] for s in order}
        out = []
        while len(out) < count:
            s = order[len(out) % len(order)]
            if not queues[s]:
                queues[s] = rng.sample(decks[s], len(decks[s]))
            t = queues[s].pop()
            out.append(self.question(t, t.generate(rng)))
        return out

    # -- grading ---------------------------------------------------------------

    def _result(self, sol, status):
        a = sol.answer
        steps = list(sol.steps)
        if isinstance(a, Num) and a.sig is not None and a.unrounded():
            steps.append(f"Round to {a.sig} significant figures, the fewest in the measured givens: {a.shown()}")
        return {"status": status, "message": None, "read_as": None, "answer": a.shown(),
                "unrounded": a.unrounded(), "steps": steps, "notes": sol.notes}

    def check(self, t, params, raw):
        sol = t.solve(params)
        res = self._result(sol, None)
        res.update(sol.answer.check(str(raw)[:200]))
        return res

    def reveal(self, t, params):
        return self._result(t.solve(params), "revealed")


def load_all(root=CONTENT):
    """Every chapter folder under content/study/, in folder-name order."""
    if not os.path.isdir(root):
        return []
    folders = sorted(d for d in os.listdir(root) if os.path.isfile(os.path.join(root, d, "chapter.json")))
    return [StudyChapter(os.path.join(root, d)) for d in folders]
