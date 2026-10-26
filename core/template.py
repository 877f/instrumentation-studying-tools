"""Building blocks for a chapter: Kind (a problem type), Template (one worksheet
question), Part, and Chapter.
"""
from core.fmt import fmt_num, fmt_sci, plural
from core.units import QUANTITIES

TIME_WORDS = {"s": ("second", "seconds"), "min": ("minute", "minutes"), "hr": ("hour", "hours")}

# How a given number is written into question text. A Kind may also pass its own fn(value, cfg).
FIELD_FORMATS = {
    "num": lambda v, cfg: fmt_num(v, 6),
    "sci": lambda v, cfg: fmt_sci(v),
    "ohms": lambda v, cfg: plural(v, "ohm", "ohms"),
    "time": lambda v, cfg: plural(v, *TIME_WORDS[cfg["tunit"]]),
}


class Kind:
    """A problem type: what it asks for, how to solve it, how to make new numbers."""

    def __init__(self, quantity, fields, hint, gen, solve, slips=None, reciprocal=False):
        self.quantity = quantity      # key in core.units.QUANTITIES
        self.fields = fields          # given -> display format (FIELD_FORMATS key or fn)
        self.hint = hint              # str, or fn(cfg) -> str. Formula only, never the answer
        self.gen = gen                # fn(rng, cfg) -> givens for a variation
        self.solve = solve            # fn(givens, cfg) -> (answer, [worked-solution steps])
        self.slips = slips            # fn(cfg) -> [(factor, message)] for common dropped conversions
        self.reciprocal = reciprocal  # answer is 1/x of a given (catches "forgot the reciprocal")


class Template:
    """One worksheet question: fixed wording, worksheet numbers, and a Kind to solve it."""

    def __init__(self, id, part, text, kind, worksheet, cfg=None, note=None, alternates=None):
        self.id = id
        self.part = part
        self.text = text              # "... {N} electrons ...", placeholders = Kind.fields
        self.kind = kind
        self.worksheet = worksheet    # the sheet's own numbers
        self.cfg = cfg or {}          # per-template settings, e.g. {"tunit": "min"}
        self.note = note              # str list, or fn(givens) -> list: interpretation notes
        self.alternates = alternates  # fn(givens) -> [{"value", "quantity", "label"}] other accepted readings

    @property
    def quantity(self):
        return self.kind.quantity

    def render(self, p):
        vals = {}
        for name, f in self.kind.fields.items():
            vals[name] = (FIELD_FORMATS[f] if isinstance(f, str) else f)(p[name], self.cfg)
        return self.text.format(**vals)

    def generate(self, rng):
        for _ in range(10):
            p = self.kind.gen(rng, self.cfg)
            if p != self.worksheet:
                break
        return p

    def solve(self, p):
        return self.kind.solve(p, self.cfg)

    def hint(self):
        h = self.kind.hint
        return h(self.cfg) if callable(h) else h

    def notes(self, p):
        if self.note is None:
            return []
        return list(self.note(p)) if callable(self.note) else list(self.note)

    def alternates_for(self, p):
        return self.alternates(p) if self.alternates else []

    def slips(self):
        return self.kind.slips(self.cfg) if self.kind.slips else []

    def question(self, chapter, params, varied):
        q = QUANTITIES[self.quantity]
        return {
            "chapter": chapter.id,
            "template_id": self.id,
            "part": self.part,
            "part_title": chapter.parts[self.part].title,
            "text": self.render(params),
            "params": params,
            "hint": self.hint(),
            "quantity": self.quantity,
            "quantity_label": q.label,
            "unit": q.unit,
            "varied": varied,
        }


class Part:
    def __init__(self, title, short):
        self.title = title    # "Coulombs and Electrons"
        self.short = short    # "Charge", used on the small part toggles


class Chapter:
    """Everything one chapter offers: practice templates and a formula sheet."""

    type = "worksheet"

    def __init__(self, id, number, title, parts, templates, formulas=()):
        self.id = id                  # URL-safe, e.g. "ch2"
        self.number = number
        self.title = title
        self.parts = parts            # {1: Part, 2: Part, ...}
        self.templates = templates
        self.formulas = formulas      # [{"title", "items": [{"name", "formula", "note"}]}]
        self.by_id = {t.id: t for t in templates}
        assert len(self.by_id) == len(templates), f"{id}: duplicate template ids"
        assert all(t.part in parts for t in templates), f"{id}: template in an unknown part"

    def summary(self):
        return {"id": self.id, "type": self.type, "number": self.number, "title": self.title,
                "question_count": len(self.templates), "part_count": len(self.parts)}

    def detail(self):
        return {
            **self.summary(),
            "parts": {str(n): {"title": p.title, "short": p.short,
                               "count": sum(t.part == n for t in self.templates)} for n, p in self.parts.items()},
            "templates": [{"id": t.id, "part": t.part, "text": t.render(t.worksheet)} for t in self.templates],
            "formulas": list(self.formulas),
        }
