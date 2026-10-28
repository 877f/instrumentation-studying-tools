"""Answer parsing and grading.

Accepts plain decimals, scientific notation (2.5e3, 2.5 x 10^3, 2.5×10³),
unit prefixes (2.5k, 5 mA, 25 µS, 40 kohm) and unit names in any case.
Prefix case still matters where it changes the meaning: m = milli, M = mega.
"""
import math
import re

from core.fmt import fmt_answer, fmt_num
from core.units import ENG_PREFIX, PREFIX_CHARS, PREFIX_WORDS, QUANTITIES

TOLERANCE = 0.01
ASCII_PREFIX = {"µ": "u"}
SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")
NUM_RE = re.compile(r"""^\s*
    (?P<mant>[+-]?(?:\d+(?:\.\d*)?|\.\d+))
    (?:[eE](?P<e>[+-]?\d+))?
    (?:\s*(?:[xX*]\s*)?10\s*(?:\^|\*\*)\s*\(?\s*(?P<p>[+-]?\d+)\s*\)?)?
    \s*(?P<unit>.*?)\s*$""", re.X)


class Parsed:
    def __init__(self, value=None, unit_q=None, prefix=None, error=None):
        self.value = value      # in the base unit of unit_q (or of the expected quantity)
        self.unit_q = unit_q    # quantity of the unit typed, None if no unit typed
        self.prefix = prefix    # single-character prefix used, if any
        self.error = error


def normalize(raw):
    s = raw.strip()
    for a, b in (("−", "-"), ("–", "-"), ("—", "-"), ("×", "x"), ("✕", "x"), ("⋅", "x"),
                 ("Ω", "ohm"), ("Ω", "ohm"), ("µ", "u"), ("μ", "u"), ("℧", "mho")):
        s = s.replace(a, b)
    s = re.sub(r"10([⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)", lambda m: "10^" + m.group(1).translate(SUPERSCRIPTS), s)
    s = re.sub(r"(?<=\d),(?=\d)", "", s)          # thousands separators
    if re.match(r"^\s*10\s*(\^|\*\*)", s):          # "10^18" with no mantissa
        s = "1x" + s
    return s


def _candidates(unit):
    """(multiplier, remaining unit text, prefix char) splits of the typed unit."""
    low = re.sub(r"\s+", " ", unit.lower()).rstrip(".")
    out = [(1.0, low, None)]
    for word, mult in PREFIX_WORDS:
        if low.startswith(word):
            out.append((mult, low[len(word):].strip(), None))
            break
    if unit[0] in PREFIX_CHARS:
        out.append((PREFIX_CHARS[unit[0]], low[1:].strip(), unit[0]))
    return out


def _resolve(unit, quantity):
    """-> (factor, unit quantity or None, prefix char) or None if unrecognised."""
    if not unit:
        return 1.0, None, None
    cands = _candidates(unit)

    def match(q):
        aliases = QUANTITIES[q].aliases
        for mult, rest, ch in cands:
            if rest in aliases:
                return mult * aliases[rest], q, ch
        return None

    hit = match(quantity)
    if hit:
        return hit
    for mult, rest, ch in cands:           # bare prefix: "2.5k", "5 m"
        if rest == "" and mult != 1:
            return mult, None, ch
    for q in QUANTITIES:
        if q != quantity:
            hit = match(q)
            if hit:
                return hit
    return None


def parse(raw, quantity):
    if not raw or not raw.strip():
        return Parsed(error="Type an answer first.")
    m = NUM_RE.match(normalize(raw))
    if not m:
        return Parsed(error="Couldn't read a number. Try 2500, 2.5e3, 2.5k or 6.25 x 10^18.")
    exp = int(m.group("e") or 0) + int(m.group("p") or 0)
    try:
        value = float(f"{m.group('mant')}e{exp}")
    except (ValueError, OverflowError):
        return Parsed(error="That number is out of range.")
    unit = m.group("unit")
    res = _resolve(unit, quantity)
    if res is None:
        u = QUANTITIES[quantity].unit
        return Parsed(error=f"Couldn't read the unit \"{unit}\". Leave it off, or use something like {u}, m{u}, k{u}.")
    factor, unit_q, prefix = res
    if not math.isfinite(value * factor):
        return Parsed(error="That number is out of range.")
    return Parsed(value * factor, unit_q, prefix)


def close(a, b, tol=TOLERANCE):
    return b != 0 and abs(a - b) <= tol * abs(b)


def tolerance(t):
    """The template's own tolerance if its Kind sets one, otherwise the default 1%."""
    return t.kind.tolerance or TOLERANCE


def shown(t, x, quantity=None):
    """The answer as it's displayed: the Kind's own format if it has one, otherwise fmt_answer."""
    return (t.kind.shown or fmt_answer)(x, quantity or t.quantity)


def diagnose(t, value, correct, parsed, raw):
    """Explain a wrong answer as specifically as possible."""
    q = QUANTITIES[t.quantity]
    if value == 0:
        return "Your answer is zero."
    if value < 0:
        if close(-value, correct):
            return "Right size, wrong sign: this answer should be positive."
        return "This answer should be positive."
    r = value / correct

    if parsed.prefix in ("m", "M"):
        other = "M" if parsed.prefix == "m" else "m"
        if close(value / PREFIX_CHARS[parsed.prefix] * PREFIX_CHARS[other], correct):
            return (f"Prefix case slip: \"m\" means milli (10^-3) and \"M\" means mega (10^6). "
                    f"Your digits are right, but \"{parsed.prefix}\" makes it off by 10^9. You wanted \"{other}\".")

    k = round(math.log10(r))
    if k != 0 and close(r, 10.0 ** k):
        size = "too big" if k > 0 else "too small"
        msg = (f"Magnitude is off by a power of 10: your answer is 10^{abs(k)} ({10 ** abs(k):,}×) {size}. "
               "The digits are right, so check a unit prefix or a conversion step.")
        if parsed.unit_q is None and parsed.prefix is None and q.prefixable and -k in ENG_PREFIX:
            pre = ENG_PREFIX[-k]
            msg += (f" If you meant {fmt_num(value, 4)} {pre}{q.unit}, type the prefix too, "
                    f"e.g. \"{raw.strip()} {ASCII_PREFIX.get(pre, pre)}{'ohm' if q.unit == 'Ω' else q.unit}\".")
        return msg

    for factor, message in t.slips():
        if close(r, factor) or close(r * factor, 1):
            return message

    if t.kind.reciprocal and any(close(value * correct, 10.0 ** j) for j in range(-12, 13)):
        return "That looks like the value you started with. Take the reciprocal: " + t.hint()

    pct = f"{tolerance(t) * 100:g}%"
    if abs(r - 1) <= 0.05:
        return (f"Close, but outside the {pct} tolerance. Avoid rounding the in-between steps; "
                "keep full digits until the end.")
    return f"Not within {pct} of the correct answer. Compare your steps with the worked solution."


def _base(t, params):
    correct, steps = t.solve(params)
    return correct, {"correct_answer": shown(t, correct), "steps": steps, "notes": t.notes(params),
                     "read_as": None, "message": None, "alternate": False}


def check(t, params, raw):
    """Grade `raw` for template `t` with givens `params`. Returns a JSON-ready dict."""
    correct, result = _base(t, params)
    q = t.quantity
    parsed = parse(raw, q)
    if parsed.error:
        result.update(status="unparsed", message=parsed.error)
        return result
    result["read_as"] = f"{fmt_num(parsed.value, 4)} {QUANTITIES[parsed.unit_q or q].unit}"

    tol = tolerance(t)
    for alt in t.alternates_for(params):
        if parsed.unit_q in (None, alt["quantity"]) and close(parsed.value, alt["value"], tol):
            result.update(status="correct", alternate=True,
                          message=f"Accepted under the other reading: you gave {alt['label']}. "
                                  f"The main reading is {shown(t, correct)}. Check which one your teacher wants.")
            return result

    if parsed.unit_q is not None and parsed.unit_q != q:
        wanted = "the number of electrons" if q == "electrons" else f"{QUANTITIES[q].label} in {QUANTITIES[q].unit_name}"
        given = "an electron count" if parsed.unit_q == "electrons" else f"a {QUANTITIES[parsed.unit_q].label} unit"
        result.update(status="incorrect", message=f"Wrong kind of unit: that's {given}, but this asks for {wanted}.")
        return result

    if close(parsed.value, correct, tol):
        result["status"] = "correct"
    else:
        result.update(status="incorrect", message=diagnose(t, parsed.value, correct, parsed, raw))
    return result


def reveal(t, params):
    """Solution without grading (the "Show answer" button)."""
    _, result = _base(t, params)
    result["status"] = "revealed"
    return result
