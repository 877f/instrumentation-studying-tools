"""Study guide answers: reading what was typed, grading it, and showing the right answer.

Numbers   1,234 · 1234 · 4.43e6 · 4.43x10^6 · 4.43 x 10^6 · 4.43×10⁶
Units     optional. When one is typed it must match: ft², ft^2, ft2 and sq ft all mean ft²,
          and ft for an area is wrong (the message says why). No conversions.
Accepted  within 0.5 % of the exact value, or equal to the exact value rounded half-up
          (Decimal, never float) to the significant figures typed, at least 2.
          On an exact tie (9.25 to 2 figures) either neighbour counts: 9.3 or 9.2.
Shown     textbook style: the fewest significant figures among the measured givens.
          Exact givens never limit it. Trailing zeros in a whole number (3200) don't count.
Angles    degrees: 25, 25°, 25 deg
Radians   a decimal, or a multiple of π: pi/8, π/8, 313pi/450, 2π/3
Names     for "name the angle" questions: ∠ABD = ∠DBA, CB = BC, ΔOEC = ΔCOE. Case,
          spaces and the ∠ / Δ signs don't matter. Several right answers can exist.
Formulas  p = 4a + 2b, checked for algebraic equivalence by core/formula.py
"""
import re
from decimal import ROUND_DOWN, ROUND_HALF_DOWN, ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

from core import formula as fm

TOL = Decimal("0.005")
MIN_SIG = 2
PI = Decimal("3.14159265358979323846264338327950288419716939937510")
SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")


# ----------------------------------------------------------------- numbers

def dsqrt(x):
    with localcontext() as ctx:
        ctx.prec = 50
        return Decimal(x).sqrt()


def sig_figs(text):
    """Significant figures in a typed or given number: "16.0" -> 3, "3200" -> 2, "0.0952" -> 3."""
    s = text.strip().lstrip("+-")
    s = re.split(r"[eE]", s)[0]
    if "." in s:
        digits = s.replace(".", "").lstrip("0")
    else:
        digits = s.lstrip("0").rstrip("0")
    return max(len(digits), 1)


def round_sig(d, n, rounding=ROUND_HALF_UP):
    d = Decimal(d)
    if d == 0:
        return d
    with localcontext() as ctx:
        ctx.prec = 60
        return d.quantize(Decimal(1).scaleb(d.adjusted() - n + 1), rounding=rounding)


def is_tie(d, n):
    """True when d sits exactly halfway between two n-figure values, like 9.25 at 2 figures."""
    d = abs(Decimal(d))
    if d == 0:
        return False
    with localcontext() as ctx:
        ctx.prec = 60
        q = d.adjusted() - n + 1
        rest = d - d.quantize(Decimal(1).scaleb(q), rounding=ROUND_DOWN)
        return rest == Decimal(5).scaleb(q - 1)


def accepted(typed, sig, exact):
    """The tolerance rule: 0.5 %, or a correct rounding to the figures typed (minimum 2)."""
    exact = Decimal(exact)
    if exact == 0:
        return typed == 0
    if abs(typed - exact) <= TOL * abs(exact):
        return True
    n = max(MIN_SIG, sig)
    if typed == round_sig(exact, n):
        return True
    return is_tie(exact, n) and typed == round_sig(exact, n, ROUND_HALF_DOWN)


def plain(d):
    """Decimal without exponent or trailing zeros: 56, 22.5, 0.0285."""
    s = format(Decimal(d).normalize(), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def fmt_sig(d, n):
    """Textbook-style n significant figures. Scientific notation only when plain digits would need
    zeros that aren't significant: 1727.876 -> 1.73 × 10^3, but 340 (exact, 2 figures) stays 340."""
    d = Decimal(d)
    if d == 0:
        return "0"
    r = round_sig(d, n)
    e = r.adjusted()
    if e >= n and r != d:
        m = r.scaleb(-e)
        return f"{m:.{n - 1}f} × 10^{e}"
    if e < -4:
        m = r.scaleb(-e)
        return f"{m:.{n - 1}f} × 10^{e}"
    return f"{r:.{max(0, n - 1 - e)}f}"


def fmt_mid(d, n=6):
    """In-between values in worked steps: 6 significant figures, trailing zeros dropped."""
    d = Decimal(d)
    if d == 0:
        return "0"
    r = round_sig(d, n)
    e = r.adjusted()
    if e >= 8 or e < -4:
        return f"{plain(r.scaleb(-e))} × 10^{e}"
    return plain(r)


def fmt_read(d):
    """How a typed value is echoed back: 4.43 × 10^6 rather than 4430000."""
    d = Decimal(d)
    e = d.adjusted() if d else 0
    return f"{plain(d.scaleb(-e))} × 10^{e}" if (e >= 6 or e < -4) else plain(d)


def _normalize(raw):
    s = raw.strip()
    for a, b in (("−", "-"), ("–", "-"), ("—", "-"), ("×", "x"), ("✕", "x"), ("⋅", "x"), ("·", "x"),
                 (" ", " "), (" ", " ")):
        s = s.replace(a, b)
    s = re.sub(r"10([⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)", lambda m: "10^" + m.group(1).translate(SUPERSCRIPTS), s)
    s = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", s)        # thousands separators: 1,234 but not 9,25
    if re.match(r"^\s*10\s*(\^|\*\*)", s):                 # "10^6" with no number in front
        s = "1x" + s
    return s


NUM_RE = re.compile(r"""^(?P<mant>[+-]?(?:\d+(?:\.\d*)?|\.\d+))
    (?:[eE](?P<e>[+-]?\d{1,3}))?
    (?:\s*[xX*]\s*10\s*(?:\^|\*\*)\s*\(?\s*(?P<p>[+-]?\d{1,3})\s*\)?)?
    \s*(?P<unit>.*)$""", re.X)


def parse_number(raw):
    """-> (Decimal value, significant figures typed, unit text) or an error message."""
    if not raw or not raw.strip():
        return "Type an answer first."
    m = NUM_RE.match(_normalize(raw))
    if not m:
        if re.match(r"^\s*\d+,\d{1,2}\b", raw):
            return "Use a decimal point, not a comma: 9.25, not 9,25."
        return "Couldn't read a number. Try 1234, 1.23e3 or 1.23 x 10^3."
    exp = int(m.group("e") or 0) + int(m.group("p") or 0)
    value = Decimal(m.group("mant")).scaleb(exp)
    return value, sig_figs(m.group("mant")), m.group("unit").strip()


# ------------------------------------------------------------------- units

LENGTH_ALIASES = {
    "mm": ("mm", "millimeter", "millimeters", "millimetre", "millimetres"),
    "cm": ("cm", "centimeter", "centimeters", "centimetre", "centimetres"),
    "m": ("m", "meter", "meters", "metre", "metres"),
    "km": ("km", "kilometer", "kilometers", "kilometre", "kilometres"),
    "in": ("in", "inch", "inches", '"', "″", "''"),
    "ft": ("ft", "foot", "feet", "'", "′"),
    "yd": ("yd", "yard", "yards"),
    "mi": ("mi", "mile", "miles"),
}
LENGTH_WORDS = {a: u for u, names in LENGTH_ALIASES.items() for a in names}
SHOW_UNIT = {"mm": "mm", "cm": "cm", "m": "m", "km": "km", "in": "in.", "ft": "ft", "yd": "yd", "mi": "mi"}
DEGREE_WORDS = {"°", "º", "˚", "deg", "degs", "degree", "degrees"}
RADIAN_WORDS = {"rad", "rads", "radian", "radians"}


def unit_text(dim, unit=None):
    if dim == "length":
        return SHOW_UNIT[unit]
    if dim == "area":
        return SHOW_UNIT[unit] + "²"
    return "°" if dim == "angle" else "rad"


def read_unit(text):
    """-> None (no unit), (dimension, base unit), or False if it can't be read."""
    u = re.sub(r"\s+", " ", text.lower().replace(".", " ")).strip()
    if not u:
        return None
    if u in DEGREE_WORDS:
        return "angle", None
    if u in RADIAN_WORDS:
        return "radian", None
    if u in LENGTH_WORDS:
        return "length", LENGTH_WORDS[u]
    m = re.fullmatch(r"(?:square|sq)\s*(.+)", u)
    if m and m.group(1).strip() in LENGTH_WORDS:
        return "area", LENGTH_WORDS[m.group(1).strip()]
    m = re.fullmatch(r"(.+?)\s*(?:\^\s*2|\*\*\s*2|2|²|squared|sq)", u)
    if m and m.group(1).strip() in LENGTH_WORDS:
        return "area", LENGTH_WORDS[m.group(1).strip()]
    return False


DIM_WORDS = {"length": "a length", "area": "an area", "angle": "an angle in degrees", "radian": "an angle in radians"}


def _unit_message(want, got_dim, got_unit):
    given = unit_text(got_dim, got_unit)
    if want.dim == "area" and got_dim == "length":
        return (f"{given} is a length unit, but this asks for an area. Area units are squared: "
                f"{want.unit_label} (or {SHOW_UNIT[want.unit].rstrip('.')}^2, sq {SHOW_UNIT[want.unit].rstrip('.')}).")
    if want.dim == "length" and got_dim == "area":
        return f"{given} is an area unit, but this asks for a length, in {want.unit_label}."
    if want.dim == "radian" and got_dim == "angle":
        return "That's in degrees. This asks for radians: multiply the degrees by π/180."
    if want.dim == "angle" and got_dim == "radian":
        return "This asks for the angle in degrees, not radians."
    if got_dim == want.dim:
        return f"This answer is in {want.unit_label}, but you typed {given}. Give it in {want.unit_label}."
    return f"{given} doesn't fit here: this asks for {DIM_WORDS[want.dim]}."


# ------------------------------------------------------------- answer kinds

class Num:
    """A number with a unit. `sig` is the textbook-style answer's significant figures (None: exact)."""

    kind = "number"

    def __init__(self, value, dim, unit=None, sig=None, pi=None, slips=()):
        self.value = Decimal(value)
        self.dim = dim                # "length", "area", "angle" or "radian"
        self.unit = unit              # "ft" for a length or an area; None for angles
        self.sig = sig
        self.pi = pi                  # radians only: the exact multiple of π, as a Fraction
        self.slips = list(slips)      # [(wrong value, message)]: a known mistake gets its own message
        self.unit_label = unit_text(dim, unit)

    def _joined(self, num):
        return f"{num}°" if self.dim == "angle" else f"{num} {self.unit_label}"

    def number(self):
        if self.sig is None:
            v = self.value
            return plain(v) if v == round_sig(v, 12) else fmt_sig(v, 3)
        return fmt_sig(self.value, self.sig)

    def shown(self):
        if self.dim == "radian" and self.pi is not None and self.pi.denominator <= 12:
            return f"{fmt_pi(self.pi)} ≈ {self.number()} rad"
        return self._joined(self.number())

    def unrounded(self):
        """The full value, when the textbook-style answer rounds it."""
        full = fmt_mid(self.value, 7)
        if self.dim == "radian" and self.pi is not None and self.pi.denominator > 12:
            return f"{full} rad = {fmt_pi(self.pi)} exactly"
        if Decimal(full.replace(" × 10^", "E")) == Decimal(self.number().replace(" × 10^", "E")):
            return None
        return self._joined(full)

    def check(self, raw):
        if self.dim == "radian":
            coef = parse_pi(raw)
            if isinstance(coef, str):
                return _res("unparsed", coef)
            if coef is not None:
                value = Decimal(coef.numerator) * PI / Decimal(coef.denominator)
                read = f"{fmt_pi(coef)} rad = {fmt_mid(value, 4)} rad"
                if (self.pi is not None and coef == self.pi) or abs(value - self.value) <= TOL * self.value:
                    return _res("correct", None, read)
                return _res("incorrect", _diagnose(value, self.value), read)
        p = parse_number(raw)
        if isinstance(p, str):
            return _res("unparsed", p)
        value, sig, utext = p
        u = read_unit(utext)
        if u is False:
            return _res("unparsed", f'Couldn\'t read the unit "{utext}". Leave it off, or use {self.unit_label}.')
        if u is not None and (u[0] != self.dim or (self.unit and u[1] != self.unit)):
            return _res("incorrect", _unit_message(self, *u), f"{fmt_read(value)} {unit_text(*u)}")
        read = self._joined(fmt_read(value))
        if accepted(value, sig, self.value):
            return _res("correct", None, read)
        for wrong, msg in self.slips:
            if accepted(value, sig, wrong):
                return _res("incorrect", msg, read)
        return _res("incorrect", _diagnose(value, self.value), read)


def _res(status, message=None, read_as=None):
    return {"status": status, "message": message, "read_as": read_as}


def _diagnose(value, exact):
    if value == 0:
        return "Your answer is zero."
    if value < 0:
        return "This answer should be positive."
    r = value / exact
    for k in range(-6, 7):
        if k and abs(r - Decimal(10) ** k) <= TOL * Decimal(10) ** k:
            return f"The digits are right but it's off by a factor of 10^{abs(k)}. Check the decimal point."
    if abs(r - 1) <= Decimal("0.05"):
        return "Close, but outside the 0.5 % tolerance. Keep full digits until the last step, then round."
    return "Not within 0.5 % of the right answer. Compare your steps with the worked steps."


# ------------------------------------------------------------------ radians

PI_RE = re.compile(r"""^\(?\s*(?P<num>\d+(?:\.\d+)?)?\s*(?:/\s*(?P<den1>\d+(?:\.\d+)?)\s*)?\)?\s*\*?\s*
    (?:pi|π)\s*(?:/\s*(?P<den>\d+(?:\.\d+)?))?\s*(?:rad|rads|radians?)?$""", re.X | re.I)


def parse_pi(raw):
    """A multiple of π as a Fraction, None if no π was typed, or an error message."""
    s = raw.strip()
    if not re.search(r"pi|π", s, re.I):
        return None
    m = PI_RE.match(s.replace("Π", "π"))
    if not m:
        return "Couldn't read that π form. Write it like pi/8, π/8 or 313pi/450."
    f = Fraction(m.group("num") or "1")
    for key in ("den1", "den"):
        if m.group(key):
            d = Fraction(m.group(key))
            if d == 0:
                return "Can't divide by zero."
            f /= d
    return f


def fmt_pi(f):
    n, d = f.numerator, f.denominator
    top = "π" if n == 1 else f"{n}π"
    return top if d == 1 else f"{top}/{d}"


# -------------------------------------------------------------------- names

NAME_LENGTH = {"angle": 3, "set3": 3, "pair": 2, "point": 1}
HOW = {"angle": "Name an angle with three letters, vertex in the middle, like ∠ABC.",
       "set3": "Use three letters, like ΔABC.",
       "pair": "Use two letters, like AB.",
       "point": "Use one letter."}
LONG_WORDS = re.compile(r"\b(?:angles?|lines?|segments?|chords?|rays?|sides?|triangles?|sectors?|arcs?|tangents?|"
                        r"secants?|radius|radii|diameters?|points?|region|between|bounded|perpendicular|isosceles|"
                        r"inscribed|acute|obtuse|right|straight)\b", re.I)
SHORT_WORDS = re.compile(r"\b(?:and|or|of|by|an|the|is|are|to|with)\b")     # lower case only: "OR" could be a name


def canon(name, kind):
    s = name.upper()
    if kind == "angle":
        return min(s, s[::-1])
    if kind in ("pair", "set3"):
        return "".join(sorted(s))
    return s


def show_name(name, kind):
    return {"angle": "∠", "set3": ""}.get(kind, "") + name


class Ident:
    """Name the parts of a figure. `items` lists the right answers, each with all its equivalent names;
    `pick` of them must be given, all different. ["DBC"] already covers ∠CBD."""

    kind = "names"

    def __init__(self, items, pick, kind, letters, shown, prefix=""):
        self.items = [{canon(n, kind) for n in names} for names in items]
        self.pick = pick
        self.name_kind = kind         # "angle", "pair" (segment, line, ray), "set3" (triangle, sector), "point"
        self.letters = set(letters)
        self.shown_text = shown       # "∠DBC and ∠EBD"
        self.prefix = prefix          # "Δ" or "sector " when showing a typed name back

    def shown(self):
        return self.shown_text

    def unrounded(self):
        return None

    def check(self, raw):
        s = raw
        for sym in "∠Δ△∡⦣":
            s = s.replace(sym, ",")
        s = SHORT_WORDS.sub(",", LONG_WORDS.sub(",", s))
        chunks = [re.sub(r"[^A-Za-z]", "", c).upper() for c in re.split(r"[,;&/+|\n]", s)]
        chunks = [c for c in chunks if c]
        if not chunks:
            return _res("unparsed", "Type a name. " + HOW[self.name_kind])
        n = NAME_LENGTH[self.name_kind]
        names = []
        for c in chunks:
            if len(c) % n:
                return _res("unparsed", f'Couldn\'t read "{c}". ' + HOW[self.name_kind])
            names.extend(c[i:i + n] for i in range(0, len(c), n))
        names = list(dict.fromkeys(canon(x, self.name_kind) for x in names))
        read = " and ".join(self.prefix + show_name(x, self.name_kind) for x in names)
        missing = sorted({ch for x in names for ch in x if ch not in self.letters})
        if missing:
            return _res("incorrect", f"There's no point {missing[0]} in the figure.", read)
        if len(names) < self.pick:
            return _res("unparsed", f"This asks for {self.pick} different names. You gave {len(names)}.")
        hits = [next((i for i, item in enumerate(self.items) if x in item), None) for x in names]
        wrong = [x for x, h in zip(names, hits) if h is None]
        if wrong:
            return _res("incorrect", f"{self.prefix}{show_name(wrong[0], self.name_kind)} isn't one of them.", read)
        if len(set(hits)) < self.pick:
            return _res("unparsed", f"Two of those name the same thing. This asks for {self.pick} different ones.")
        return _res("correct", None, read)


# ----------------------------------------------------------------- formulas

class Sym:
    """A formula in the figure's letters, e.g. p = 4a + 2b. `slips`: [(formula, message)]."""

    kind = "formula"

    def __init__(self, target, expr, letters, target_word, slips=()):
        self.target = target          # "p" or "A"
        self.letters = {v.upper(): v for v in letters}
        self.letter_list = list(letters)
        self.target_word = target_word   # "perimeter" or "area"
        self.expr_text = expr
        self.expr = fm.parse_answer(expr, self.letters).node.expr
        self.slips = [(fm.parse_answer(e, self.letters).node.expr, msg) for e, msg in slips]

    def shown(self):
        return f"{self.target} = {self.expr_text}"

    def unrounded(self):
        return None

    def check(self, raw):
        s = raw.strip()
        if not s:
            return _res("unparsed", "Type a formula first.")
        if "=" in s:
            left, _, s = s.partition("=")
            if "=" in s:
                return _res("unparsed", f"Use at most one = sign, like {self.target} = ...")
            left = left.strip()
            if left and left.lower() not in (self.target.lower(), self.target_word):
                other = "area" if self.target_word == "perimeter" else "perimeter"
                if left.lower() in ("a", "p", other):
                    return _res("incorrect", f"This asks for the {self.target_word} ({self.target}), not the {other}.")
                return _res("unparsed", f"Put {self.target} on the left, like {self.target} = ..., or leave it off.")
        try:
            p = fm.parse_answer(s, self.letters)
        except fm.ParseError as e:
            msg = str(e).replace(", like V/R.", ".").replace("like I = V/R", f"like {self.target} = ...")
            return _res("unparsed", msg)
        read = f"{self.target} = {p.node.text}"
        if fm.equivalent(p.node.expr, self.expr):
            return _res("correct", None, read)
        for wrong, msg in self.slips:
            if fm.equivalent(p.node.expr, wrong):
                return _res("incorrect", msg, read)
        return _res("incorrect", "Not the same formula. Add up the outside edges (or the pieces' areas) one at a time.",
                    read)
