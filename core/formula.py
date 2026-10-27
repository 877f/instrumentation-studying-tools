"""Formula drills (module type "formula"), e.g. the Ohm's Law Wheel.

Students type formulas such as "I = V/R", "sqrt(P/R)" or "V²/R". The small
parser below turns them into sympy expressions without ever calling eval
(sympy's own parser does), and the checker tests algebraic equivalence with
the correct formula while allowing only the variables the question names.

A module itself is pure data (see chapters/ohms_wheel.py): variables, base
equations, formulas with derivations, levels, and a value generator for the
numeric level.
"""
import cmath
import random

import sympy

from core import grader
from core.fmt import fmt_eng, fmt_num
from core.template import Kind, Template
from core.units import QUANTITIES

MAX_LEN = 120          # longest accepted answer, in characters
MAX_DEPTH = 10         # bracket nesting
MAX_EXPONENT = 6
_screen = random.Random(2026)


class ParseError(Exception):
    pass


# ------------------------------------------------------------------ parser

DIGITS = set("0123456789")      # not str.isdigit(): that also accepts "²"
MUL_CHARS = set("*×·⋅•∙")
DIV_CHARS = set("/÷")
MINUS_CHARS = set("-−–")
OPEN, CLOSE = set("([{"), set(")]}")
SUPERSCRIPT = {"²": 2, "³": 3}
ATOM, POW, UNARY, MUL, ADD = 5, 4, 3, 2, 1      # display precedence
_symbols = {}


def symbol(name):
    if name not in _symbols:
        _symbols[name] = sympy.Symbol(name, positive=True)
    return _symbols[name]


class Tok:
    __slots__ = ("kind", "value", "text")

    def __init__(self, kind, value, text):
        self.kind, self.value, self.text = kind, value, text


def tokenize(s, letters):
    """letters: upper-case letter -> canonical variable (aliases included, e.g. U -> V)."""
    toks, i, n = [], 0, len(s)
    simple = {"^": ("op", "^"), "+": ("op", "+"), "√": ("sqrt", None)}
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
        elif ch in DIGITS or (ch == "." and i + 1 < n and s[i + 1] in DIGITS):
            j = i
            while j < n and (s[j] in DIGITS or s[j] == "."):
                j += 1
            text = s[i:j]
            if text.count(".") > 1 or len(text) > 8:
                raise ParseError(f'Couldn\'t read the number "{text}".')
            if toks and toks[-1].kind == "var" and not s[i - 1].isspace():
                v = toks[-1].value
                raise ParseError(f'"{toks[-1].text}{text}" is ambiguous. For squared, write {v}^2 or {v}².')
            toks.append(Tok("num", sympy.Rational(text), text))
            i = j
        elif s.startswith("**", i):
            toks.append(Tok("op", "^", "**"))
            i += 2
        elif ch in simple:
            toks.append(Tok(*simple[ch], ch))
            i += 1
        elif ch in MUL_CHARS:
            toks.append(Tok("op", "*", ch))
            i += 1
        elif ch in DIV_CHARS:
            toks.append(Tok("op", "/", ch))
            i += 1
        elif ch in MINUS_CHARS:
            toks.append(Tok("op", "-", ch))
            i += 1
        elif ch in OPEN or ch in CLOSE:
            toks.append(Tok("lp" if ch in OPEN else "rp", None, ch))
            i += 1
        elif ch in SUPERSCRIPT:
            toks.append(Tok("sup", SUPERSCRIPT[ch], ch))
            i += 1
        elif ch.isalpha():
            if s[i:i + 4].lower() == "sqrt":
                toks.append(Tok("sqrt", None, s[i:i + 4]))
                i += 4
                continue
            up = ch.upper()
            if up in letters:
                toks.append(Tok("var", letters[up], ch))
            elif up == "X":
                toks.append(Tok("op", "*", ch))
            else:
                names = ", ".join(sorted(set(letters.values())))
                raise ParseError(f'Couldn\'t read "{ch}". Use only the letters {names}, like V/R.')
            i += 1
        else:
            raise ParseError(f'Couldn\'t read "{ch}".')
    return toks


class Node:
    __slots__ = ("expr", "text", "prec")

    def __init__(self, expr, text, prec):
        self.expr, self.text, self.prec = expr, text, prec


def _wrap(node, prec):
    return node.text if node.prec >= prec else f"({node.text})"


def _mul(a, b):
    return Node(a.expr * b.expr, f"{_wrap(a, MUL)} × {_wrap(b, MUL)}", MUL)


def _pow(node, e):
    shown = {2: "²", 3: "³"}.get(e, f"^{e}")
    return Node(node.expr ** e, _wrap(node, ATOM) + shown, POW)


class _Parser:
    """Recursive descent: sum > product (incl. implicit IR) > unary minus > power > atom."""

    def __init__(self, toks):
        self.toks, self.i, self.depth = toks, 0, 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def at(self, kind, value=None):
        t = self.peek()
        return t is not None and t.kind == kind and (value is None or t.value == value)

    def take(self):
        t = self.peek()
        self.i += 1
        return t

    def parse(self):
        if not self.toks:
            raise ParseError("Type a formula, for example V/R.")
        node = self.sum()
        if self.i < len(self.toks):
            t = self.peek()
            if t.kind == "rp":
                raise ParseError(f'There\'s a "{t.text}" without a matching "(".')
            raise ParseError(f'Couldn\'t read the part starting at "{t.text}".')
        return node

    def sum(self):
        node = self.product()
        while self.at("op", "+") or self.at("op", "-"):
            op = self.take().value
            right = self.product()
            expr = node.expr + right.expr if op == "+" else node.expr - right.expr
            node = Node(expr, f"{node.text} {op} {_wrap(right, ADD + (op == '-'))}", ADD)
        return node

    def starts_atom(self):
        t = self.peek()
        return t is not None and t.kind in ("num", "var", "lp", "sqrt")

    def product(self):
        node = self.unary()
        while True:
            if self.at("op", "*"):
                self.take()
                node = _mul(node, self.unary())
            elif self.at("op", "/"):
                self.take()
                right = self.unary()
                node = Node(node.expr / right.expr, f"{_wrap(node, MUL)} / {_wrap(right, MUL + 1)}", MUL)
            elif self.starts_atom():                      # implicit: IR, 2R, I(R), √P√R
                node = _mul(node, self.unary())
            else:
                return node

    def unary(self):
        if self.at("op", "-"):
            self.take()
            n = self.unary()
            return Node(-n.expr, f"-{_wrap(n, UNARY)}", UNARY)
        if self.at("op", "+"):
            self.take()
            return self.unary()
        return self.power()

    def power(self):
        node = self.atom()
        while self.at("sup"):
            node = _pow(node, self.take().value)
        if self.at("op", "^"):
            self.take()
            node = _pow(node, self.exponent())
        return node

    def exponent(self):
        sign = 1
        while self.at("op", "-") or self.at("op", "+"):
            sign *= -1 if self.take().value == "-" else 1
        if self.at("num"):
            e = self.take().value
        elif self.at("lp"):
            e = self.atom().expr
        else:
            raise ParseError("Put a number after ^, like ^2.")
        e = sympy.nsimplify(e) * sign if getattr(e, "is_number", False) else None
        if e is None or not e.is_Rational or abs(e) > MAX_EXPONENT or e.q > 4:
            raise ParseError("Exponents must be small numbers, like ^2 or ^0.5.")
        return e

    def atom(self):
        t = self.peek()
        if t is None:
            raise ParseError("The formula ends too early. Is something missing after the last sign?")
        if t.kind == "num":
            self.take()
            return Node(t.value, t.text, ATOM)
        if t.kind == "var":
            self.take()
            return Node(symbol(t.value), t.value, ATOM)
        if t.kind == "lp":
            self.take()
            self.depth += 1
            if self.depth > MAX_DEPTH:
                raise ParseError("Too many brackets.")
            inner = self.sum()
            if not self.at("rp"):
                raise ParseError('A bracket is missing its ")".')
            self.take()
            self.depth -= 1
            return inner
        if t.kind == "sqrt":
            self.take()
            if self.at("lp"):
                inner = self.atom()
            else:                                         # √PR means √(PR); √P/R means √(P) / R
                inner = self.power()
                while self.at("var") or self.at("num"):
                    inner = _mul(inner, self.power())
            return Node(sympy.sqrt(inner.expr), f"√({inner.text})", ATOM)
        if t.kind == "rp":
            raise ParseError(f'There\'s a "{t.text}" without a matching "(".')
        if t.kind == "sup":
            raise ParseError(f'"{t.text}" needs a variable in front of it.')
        raise ParseError(f'Something is missing before "{t.text}".')


class Parsed:
    def __init__(self, node, used, lhs, aliases):
        self.node = node          # Node: .expr (sympy) and .text (tidy display)
        self.used = used          # canonical variables typed on the right-hand side
        self.lhs = lhs            # canonical variable on the left of "=", or None
        self.aliases = aliases    # alias letters typed, e.g. {"U"}


def parse_answer(raw, letters):
    s = raw.strip()
    if len(s) > MAX_LEN:
        raise ParseError("That's longer than any formula on the wheel.")
    lhs = None
    alias_toks = []
    if "=" in s:
        parts = s.split("=")
        if len(parts) > 2:
            raise ParseError("Use at most one = sign, like I = V/R.")
        left, s = parts[0].strip(), parts[1]
        if left:
            lt = tokenize(left, letters)
            if len(lt) != 1 or lt[0].kind != "var":
                raise ParseError("Put just one variable on the left, like I = V/R, or leave the left side off.")
            lhs = lt[0].value
            alias_toks = lt
    toks = tokenize(s, letters)
    node = _Parser(toks).parse()
    used = {t.value for t in toks if t.kind == "var"}
    aliases = {t.text.upper() for t in toks + alias_toks if t.kind == "var" and t.text.upper() != t.value}
    return Parsed(node, used, lhs, aliases)


def equivalent(a, b):
    """Algebraic equivalence. A quick numeric screen first, then sympy proves it."""
    syms = sorted(a.free_symbols | b.free_symbols, key=str)
    for _ in range(4):
        point = {s: sympy.Rational(_screen.randint(3, 97), _screen.randint(2, 11)) for s in syms}
        try:
            va, vb = complex(a.evalf(subs=point)), complex(b.evalf(subs=point))
        except Exception:
            return False
        if not (cmath.isfinite(va) and cmath.isfinite(vb)) or abs(va - vb) > 1e-9 * max(1.0, abs(vb)):
            return False
    try:
        return sympy.simplify(a - b) == 0 or sympy.simplify(a / b) == 1
    except Exception:
        return False


def _and(names):
    names = list(names)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


# ------------------------------------------------------------- module data

class Variable:
    def __init__(self, label, quantity):
        self.label = label            # "current"
        self.quantity = quantity      # key in core.units.QUANTITIES (gives the unit, e.g. A)


class Formula:
    """One wheel formula: target in terms of two knowns, with its derivation."""

    def __init__(self, target, knowns, expr, short, base, steps):
        self.target = target          # "I"
        self.knowns = tuple(knowns)   # ("V", "R"): the only variables an answer may use
        self.key = f"{target}:{''.join(knowns)}"
        self.expr_text = expr         # "V/R", parsed by the parser above
        self.short = short            # "V / R", shown on the wheel
        self.display = f"{target} = {short}"
        self.base = base              # base equation(s) to start from (used for the hint)
        self.steps = steps            # derivation from the base equations
        self.expr = None              # set by FormulaModule


class Level:
    def __init__(self, id, title, desc, keys, prompt="Write {target} in terms of {knowns}.", numeric=False):
        self.id = id
        self.title = title
        self.desc = desc
        self.keys = keys              # formula keys asked in this level, e.g. ["I:VR", "R:VI"]
        self.prompt = prompt          # {target}, {knowns}
        self.numeric = numeric        # plug in numbers instead of writing the formula


class FormulaModule:
    type = "formula"

    def __init__(self, id, title, badge, intro, variables, base, formulas, levels, quadrants,
                 numeric_values, aliases=None):
        self.id = id
        self.title = title
        self.badge = badge            # short text on the home-screen tile, e.g. "Ω"
        self.intro = intro
        self.variables = variables    # letter -> Variable
        self.base = base              # ["V = I × R", "P = V × I"]
        self.formulas = formulas
        self.levels = levels
        self.quadrants = quadrants    # wheel order, e.g. ["P", "I", "V", "R"]
        self.numeric_values = numeric_values   # fn(rng) -> consistent values for every variable
        self.aliases = aliases or {}  # letter -> (canonical, reminder), e.g. {"U": ("V", "...")}
        self.letters = {v: v for v in variables}
        self.letters.update({a: canon for a, (canon, _) in self.aliases.items()})
        self.by_key = {f.key: f for f in formulas}
        self.levels_by_id = {lv.id: lv for lv in levels}
        self._numeric = {}
        assert len(self.by_key) == len(formulas), f"{id}: duplicate formula keys"
        for f in formulas:
            f.expr = parse_answer(f.expr_text, self.letters).node.expr
            assert {str(s) for s in f.expr.free_symbols} <= set(f.knowns), f"{f.key}: uses other variables"
        for lv in levels:
            assert all(k in self.by_key for k in lv.keys), f"{id} level {lv.id}: unknown formula key"
        self._self_check()

    def _self_check(self):
        """Every formula must agree with the value generator (catches typos in the data file)."""
        rng = random.Random(1)
        for _ in range(20):
            vals = self.numeric_values(rng)
            for f in self.formulas:
                got = float(f.expr.subs({symbol(k): sympy.nsimplify(vals[k]) for k in f.knowns}))
                assert abs(got - vals[f.target]) <= 1e-9 * abs(vals[f.target]), f"{f.key} disagrees with the values"

    # -- API shapes ---------------------------------------------------------

    def summary(self):
        return {"id": self.id, "type": self.type, "title": self.title, "badge": self.badge,
                "question_count": len(self.formulas),
                "subtitle": f"{len(self.formulas)} formulas · {len(self.levels)} levels + blank wheel",
                # wheel layout only (no formulas), so the home screen can draw the ring
                "quadrants": [{"var": q, "slots": sum(f.target == q for f in self.formulas)} for q in self.quadrants]}

    def detail(self):
        return {**self.summary(), "intro": self.intro,
                "levels": [{"id": lv.id, "title": lv.title, "desc": lv.desc, "keys": lv.keys,
                            "numeric": lv.numeric} for lv in self.levels],
                "quadrants": [{"var": q, "label": self.variables[q].label,
                               "slots": sum(f.target == q for f in self.formulas)} for q in self.quadrants]}

    def wheel(self):
        """The filled-in wheel. Only shown on review screens."""
        return {"base": self.base,
                "quadrants": [{"var": q, "label": self.variables[q].label,
                               "unit": QUANTITIES[self.variables[q].quantity].unit,
                               "formulas": [{"key": f.key, "short": f.short, "display": f.display}
                                            for f in self.formulas if f.target == q]} for q in self.quadrants]}

    def hint(self, f):
        if len(f.base) == 1:
            return f"Start from {f.base[0]} and get {f.target} by itself."
        gone = [v for v in self.variables if v != f.target and v not in f.knowns]
        return f"Start from {f.base[0]} and {f.base[1]}. Substitute one into the other to get rid of {_and(gone)}."

    def question(self, level, f, rng):
        q = {"module": self.id, "level": level.id, "key": f.key, "target": f.target, "knowns": list(f.knowns),
             "numeric": level.numeric, "hint": self.hint(f),
             "prompt": level.prompt.format(target=f.target, knowns=_and(f.knowns))}
        if level.numeric:
            t = self.numeric_template(f)
            params = t.generate(rng)
            quantity = QUANTITIES[self.variables[f.target].quantity]
            q.update(params=params, prompt=t.render(params), unit=quantity.unit, quantity_label=quantity.label)
        return q

    def session(self, level, rng):
        keys = list(level.keys)
        rng.shuffle(keys)
        return [self.question(level, self.by_key[k], rng) for k in keys]

    # -- checking -----------------------------------------------------------

    def _result(self, f):
        return {"status": None, "message": None, "reminder": None, "read_as": None, "alternate": False,
                "correct_answer": f.display, "correct_formula": f.display, "steps": list(f.steps), "notes": []}

    def _reminder(self, parsed):
        return " ".join(self.aliases[a][1] for a in sorted(parsed.aliases)) or None

    def check_symbolic(self, f, raw):
        res = self._result(f)
        try:
            p = parse_answer(raw, self.letters)
        except ParseError as e:
            res.update(status="unparsed", message=str(e))
            return res
        res["read_as"] = f"{f.target} = {p.node.text}"
        res["reminder"] = self._reminder(p)
        if p.lhs is not None and p.lhs != f.target:
            res.update(status="incorrect", message=f"You solved for {p.lhs}, but this asks for {f.target}.")
            return res
        extra = sorted(p.used - set(f.knowns))
        if extra:
            res.update(status="incorrect",
                       message=f"This question only allows {_and(f.knowns)}, but your answer uses {_and(extra)}.")
            return res
        if equivalent(p.node.expr, f.expr):
            res["status"] = "correct"
            return res
        res["status"] = "incorrect"
        if equivalent(p.node.expr, 1 / f.expr):
            res["message"] = "That's upside down: it's the reciprocal of the right answer."
        elif equivalent(p.node.expr, f.expr ** 2):
            res["message"] = "That's the square of the answer. Take the square root."
        elif equivalent(p.node.expr ** 2, f.expr):
            res["message"] = "That's the square root of the answer. Square it instead."
        return res

    def numeric_template(self, f):
        """Level-5 problem for formula f, built on the worksheet engine so numbers grade the same way."""
        if f.key in self._numeric:
            return self._numeric[f.key]

        def given(var, v):
            unit = QUANTITIES[self.variables[var].quantity].unit
            return f"{fmt_num(v, 6)} {unit}" if 0.1 <= v < 1000 else fmt_eng(v, unit, sig=6)

        def gen(rng, cfg):
            vals = self.numeric_values(rng)
            return {k: float(f"{vals[k]:.10g}") for k in f.knowns}

        def solve(p, cfg):
            value = float(f.expr.subs({symbol(k): sympy.nsimplify(p[k]) for k in f.knowns}))
            unit = QUANTITIES[self.variables[f.target].quantity].unit
            plug = " and ".join(f"{k} = {given(k, p[k])}" for k in f.knowns)
            return value, list(f.steps) + [f"Plug in {plug}: {f.display} = {fmt_num(value, 5)} {unit}"]

        fields = {k: (lambda v, cfg, k=k: given(k, v)) for k in f.knowns}
        kind = Kind(self.variables[f.target].quantity, fields, self.hint(f), gen, solve)
        text = " and ".join(f"{k} = {{{k}}}" for k in f.knowns) + f". Find {f.target}."
        t = self._numeric[f.key] = Template(f.key, 5, text, kind, worksheet={})
        return t

    def check_numeric(self, f, params, raw):
        res = grader.check(self.numeric_template(f), params, raw)
        res.update(correct_formula=f.display, reminder=None)
        return res

    def reveal(self, f, params=None, numeric=False):
        if numeric:
            res = grader.reveal(self.numeric_template(f), params)
            res.update(correct_formula=f.display, reminder=None)
            return res
        res = self._result(f)
        res["status"] = "revealed"
        return res

    def grade_blank(self, answers):
        """Blank wheel: any order inside a quadrant; each formula counts once."""
        quadrants, score = {}, 0
        for qv in self.quadrants:
            formulas = [f for f in self.formulas if f.target == qv]
            allowed = [v for v in self.variables if v != qv]
            raw_slots = list((answers or {}).get(qv) or [])[:len(formulas)]
            raw_slots += [""] * (len(formulas) - len(raw_slots))
            matched, slots = set(), []
            for raw in raw_slots:
                raw = str(raw)[:200]
                if not raw.strip():
                    slots.append({"status": "blank", "message": "Left blank."})
                    continue
                try:
                    p = parse_answer(raw, self.letters)
                except ParseError as e:
                    slots.append({"status": "unparsed", "message": str(e)})
                    continue
                if p.lhs is not None and p.lhs != qv:
                    slots.append({"status": "incorrect", "message": f"This box is for {qv}, not {p.lhs}."})
                    continue
                if p.used - set(allowed):
                    slots.append({"status": "incorrect", "message": f"Uses {qv} on both sides."})
                    continue
                hit = next((f for f in formulas if equivalent(p.node.expr, f.expr)), None)
                if hit is None:
                    slots.append({"status": "incorrect", "message": f"Not one of the {qv} formulas."})
                elif hit.key in matched:
                    slots.append({"status": "duplicate", "message": f"You already have {hit.display}."})
                else:
                    matched.add(hit.key)
                    score += 1
                    slots.append({"status": "correct", "message": hit.display,
                                  "reminder": self._reminder(p)})
            quadrants[qv] = {"slots": slots, "missing": [f.display for f in formulas if f.key not in matched]}
        return {"score": score, "total": len(self.formulas), "quadrants": quadrants, "wheel": self.wheel()}
