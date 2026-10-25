"""Number formatting: significant figures, scientific notation, engineering prefixes.

Text uses "10^n"; the front end turns that into a superscript.
"""
from decimal import Decimal, ROUND_HALF_UP

from core.units import ENG_PREFIX, QUANTITIES


def round_sig(x, sig=3):
    """Round to `sig` significant figures, half-up (2.275 -> 2.28), as a Decimal."""
    d = Decimal(repr(float(x)))
    if d == 0:
        return d
    return d.quantize(Decimal(1).scaleb(d.adjusted() - sig + 1), rounding=ROUND_HALF_UP)


def _plain(d):
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def fmt_num(x, sig=3):
    """`sig` significant figures; scientific (a × 10^n) when very large or small."""
    if x == 0:
        return "0"
    d = round_sig(x, sig)
    exp = d.adjusted()
    if -3 <= exp < 6:
        return _plain(d)
    return f"{_plain(d.scaleb(-exp))} × 10^{exp}"


def fmt_sci(x, sig=6):
    d = round_sig(x, sig)
    exp = d.adjusted()
    return f"{_plain(d.scaleb(-exp))} × 10^{exp}"


def fmt_eng(x, unit, sig=3):
    d = round_sig(x, sig)
    exp3 = max(-12, min(9, (d.adjusted() // 3) * 3))
    return f"{_plain(d.scaleb(-exp3))} {ENG_PREFIX[exp3]}{unit}"


def fmt_answer(x, quantity):
    """Final answer to 3 sig figs, plus a prefixed form where the quantity uses one."""
    q = QUANTITIES[quantity]
    text = f"{fmt_num(x)} {q.unit}"
    if q.eng == "all" or (q.eng == "large" and abs(x) >= 1000):
        eng = fmt_eng(x, q.unit)
        if eng != text:
            text += f" (= {eng})"
    return text


def g(x):
    """Intermediate values in worked solutions: 5 sig figs."""
    return fmt_num(x, 5)


def plural(value, singular, plural_):
    return f"{fmt_num(value, 6)} {singular if value == 1 else plural_}"
