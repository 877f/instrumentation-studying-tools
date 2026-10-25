"""Answer parsing and grading.

Accepts plain decimals, scientific notation (2.5e3, 2.5 x 10^3, 2.5×10³),
unit prefixes (2.5k, 5 mA, 25 µS, 40 kohm) and unit names in any case.
Prefix case still matters where it changes the meaning: m = milli, M = mega.
"""
import math
import re

from questions import QUANTITIES, ENG_PREFIX, fmt_answer, fmt_num

TOLERANCE = 0.01

PREFIX_WORDS = [("pico", 1e-12), ("nano", 1e-9), ("micro", 1e-6), ("milli", 1e-3),
                ("kilo", 1e3), ("mega", 1e6), ("meg", 1e6), ("giga", 1e9)]
PREFIX_CHARS = {"p": 1e-12, "n": 1e-9, "N": 1e-9, "u": 1e-6, "U": 1e-6, "m": 1e-3, "M": 1e6,
                "k": 1e3, "K": 1e3, "g": 1e9, "G": 1e9}

# Lower-case unit names -> factor to the quantity's base unit.
UNIT_ALIASES = {
    "charge": {"c": 1, "coulomb": 1, "coulombs": 1, "coul": 1},
    "electrons": {"electron": 1, "electrons": 1, "e-": 1, "e": 1, "el": 1, "elec": 1},
    "voltage": {"v": 1, "volt": 1, "volts": 1},
    "energy": {"j": 1, "joule": 1, "joules": 1},
    "current": {"a": 1, "amp": 1, "amps": 1, "ampere": 1, "amperes": 1},
    "time": {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1, "min": 60, "mins": 60,
             "minute": 60, "minutes": 60, "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600},
    "conductance": {"s": 1, "siemens": 1, "siemen": 1, "mho": 1, "mhos": 1},
    "resistance": {"ohm": 1, "ohms": 1, "kilohm": 1e3, "kilohms": 1e3},
    "length": {"ft": 1, "foot": 1, "feet": 1, "'": 1, "yd": 3, "yds": 3, "yard": 3, "yards": 3,
               "in": 1 / 12, "inch": 1 / 12, "inches": 1 / 12, '"': 1 / 12},
    "area": {"cm": 1, "cmil": 1, "cmils": 1, "mil": 1, "mils": 1, "circular mil": 1, "circular mils": 1,
             "circ mil": 1, "circ mils": 1, "mcm": 1000},
}
UNIT_NAMES = {"charge": "coulombs (C)", "voltage": "volts (V)", "energy": "joules (J)",
              "current": "amperes (A)", "time": "seconds (s)", "conductance": "siemens (S)",
              "resistance": "ohms (Ω)", "length": "feet (ft)", "area": "circular mils (CM)"}
# Quantities where "did you mean 556 µA?" style prefix suggestions make sense.
PREFIXABLE = {"charge", "voltage", "energy", "current", "time", "conductance", "resistance"}
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
    others = [q for q in UNIT_ALIASES if q != quantity]

    def match(q):
        for mult, rest, ch in cands:
            if rest in UNIT_ALIASES[q]:
                return mult * UNIT_ALIASES[q][rest], q, ch
        return None

    hit = match(quantity)
    if hit:
        return hit
    for mult, rest, ch in cands:           # bare prefix: "2.5k", "5 m"
        if rest == "" and mult != 1:
            return mult, None, ch
    for q in others:
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
        return Parsed(error=f"Couldn't read the unit \"{unit}\". Leave it off, or use something like "
                            f"{QUANTITIES[quantity][1]}, m{QUANTITIES[quantity][1]}, k{QUANTITIES[quantity][1]}.")
    factor, unit_q, prefix = res
    if not math.isfinite(value * factor):
        return Parsed(error="That number is out of range.")
    return Parsed(value * factor, unit_q, prefix)


def close(a, b, tol=TOLERANCE):
    return b != 0 and abs(a - b) <= tol * abs(b)


def _times(k):
    return f"{10 ** abs(k):,}×"


def diagnose(t, value, correct, parsed, raw):
    """Explain a wrong answer as specifically as possible."""
    q = t.quantity
    unit = QUANTITIES[q][1]
    if value == 0:
        return "Your answer is zero."
    if value < 0:
        if close(-value, correct):
            return "Right size, wrong sign: this answer should be positive."
        return "This answer should be positive."
    r = value / correct

    if parsed.prefix in ("m", "M"):
        other = "M" if parsed.prefix == "m" else "m"
        swapped = value / PREFIX_CHARS[parsed.prefix] * PREFIX_CHARS[other]
        if close(swapped, correct):
            return (f"Prefix case slip: \"m\" means milli (10^-3) and \"M\" means mega (10^6). "
                    f"Your digits are right, but \"{parsed.prefix}\" makes it off by 10^9. You wanted \"{other}\".")

    k = round(math.log10(r))
    if k != 0 and close(r, 10.0 ** k):
        size = "too big" if k > 0 else "too small"
        msg = (f"Magnitude is off by a power of 10: your answer is 10^{abs(k)} ({_times(k)}) {size}. "
               "The digits are right, so check a unit prefix or a conversion step.")
        if parsed.unit_q is None and parsed.prefix is None and q in PREFIXABLE and -k in ENG_PREFIX:
            pre = ENG_PREFIX[-k]
            msg += (f" If you meant {fmt_num(value, 4)} {pre}{unit}, type the prefix too, "
                    f"e.g. \"{raw.strip()} {ASCII_PREFIX.get(pre, pre)}{'ohm' if unit == 'Ω' else unit}\".")
        return msg

    for factor, message in t.slips():
        if close(r, factor) or close(r * factor, 1):
            return message

    if t.kind.reciprocal and (close(value * correct, 1) or
                              any(close(value * correct, 10.0 ** j) for j in range(-12, 13))):
        return "That looks like the value you started with. Take the reciprocal: " + t.hint()

    if abs(r - 1) <= 0.05:
        return ("Close, but outside the 1% tolerance. Avoid rounding the in-between steps; "
                "keep full digits until the end.")
    return "Not within 1% of the correct answer. Compare your steps with the worked solution."


def check(t, params, raw):
    """Grade `raw` for template `t` with `params`. Returns a JSON-ready dict."""
    correct, steps = t.solve(params)
    q = t.quantity
    result = {
        "correct_answer": fmt_answer(correct, q),
        "steps": steps,
        "notes": t.notes(params),
        "read_as": None,
        "message": None,
        "alternate": False,
    }
    parsed = parse(raw, q)
    if parsed.error:
        result.update(status="unparsed", message=parsed.error)
        return result

    shown_q = parsed.unit_q or q
    result["read_as"] = f"{fmt_num(parsed.value, 4)} {QUANTITIES[shown_q][1]}"

    for alt_value, alt_q, label in t.alternates(params):
        if (parsed.unit_q in (None, alt_q)) and close(parsed.value, alt_value):
            result.update(status="correct", alternate=True,
                          message=f"Accepted under the other reading: you gave {label}. "
                                  f"This app's main reading is the number of electrons ({fmt_answer(correct, q)}). "
                                  "Check which one your teacher wants.")
            return result

    if parsed.unit_q is not None and parsed.unit_q != q:
        wanted = "the number of electrons" if q == "electrons" else f"{QUANTITIES[q][0]} in {UNIT_NAMES[q]}"
        given = "an electron count" if parsed.unit_q == "electrons" else f"a {QUANTITIES[parsed.unit_q][0]} unit"
        result.update(status="incorrect",
                      message=f"Wrong kind of unit: that's {given}, but this asks for {wanted}.")
        return result

    if close(parsed.value, correct):
        result["status"] = "correct"
        return result

    result.update(status="incorrect", message=diagnose(t, parsed.value, correct, parsed, raw))
    return result


def reveal(t, params):
    """Solution without grading (the "Show answer" button)."""
    correct, steps = t.solve(params)
    return {"status": "revealed", "correct_answer": fmt_answer(correct, t.quantity), "steps": steps,
            "notes": t.notes(params), "read_as": None, "message": None, "alternate": False}
