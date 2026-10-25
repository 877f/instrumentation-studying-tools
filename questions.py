"""The 54 Chapter 2 worksheet templates: wording, worksheet numbers, solvers,
hints, and random-variation generators.

Every template keeps its worksheet wording; only the numbers change in
Variations / Weak spots mode.
"""
import math
from decimal import Decimal, ROUND_HALF_UP

E_PER_C = 6.25e18   # electrons per coulomb
RHO_CU = 10.4       # copper, ohm-circular-mils per foot
EC = "6.25 × 10^18"

PARTS = {
    1: "Coulombs and Electrons",
    2: "Voltage from Coulombs and Joules",
    3: "Electrical Current from Coulombs and Time",
    4: "Conductance and Resistance",
    5: "Copper Wire Problems",
}

# quantity key -> (label shown to the user, base unit symbol)
QUANTITIES = {
    "charge": ("charge", "C"),
    "electrons": ("number of electrons", "electrons"),
    "voltage": ("voltage", "V"),
    "energy": ("energy", "J"),
    "current": ("current", "A"),
    "time": ("time", "s"),
    "conductance": ("conductance", "S"),
    "resistance": ("resistance", "Ω"),
    "length": ("length", "ft"),
    "area": ("cross-section area", "CM"),
}

# Quantities whose answers also get an engineering-prefix form, e.g. "(= 556 µA)".
ENG_QUANTITIES = {"current", "conductance", "resistance"}
ENG_PREFIX = {-12: "p", -9: "n", -6: "µ", -3: "m", 0: "", 3: "k", 6: "M", 9: "G"}


# ---------------------------------------------------------------- formatting

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
    """Final answer to 3 sig figs, plus a prefixed form for A / S / Ω."""
    unit = QUANTITIES[quantity][1]
    text = f"{fmt_num(x)} {unit}"
    if quantity in ENG_QUANTITIES and not (quantity == "resistance" and abs(x) < 1000):
        eng = fmt_eng(x, unit)
        if eng != text:
            text += f" (= {eng})"
    return text


def g(x):
    """Intermediate values in worked solutions: 5 sig figs."""
    return fmt_num(x, 5)


def _plural(value, singular, plural):
    return f"{fmt_num(value, 6)} {singular if value == 1 else plural}"


TIME_WORDS = {"s": ("second", "seconds"), "min": ("minute", "minutes"), "hr": ("hour", "hours")}

FIELD_FORMATS = {
    "num": lambda v, cfg: fmt_num(v, 6),
    "sci": lambda v, cfg: fmt_sci(v),
    "ohms": lambda v, cfg: _plural(v, "ohm", "ohms"),
    "time": lambda v, cfg: _plural(v, *TIME_WORDS[cfg["tunit"]]),
}


# ------------------------------------------------------------ shared steps

def _n_to_q(N):
    Q = N / E_PER_C
    return Q, f"Convert electrons to coulombs: Q = N ÷ ({EC} electrons/C) = {g(N)} ÷ {EC} = {g(Q)} C"


def _q_to_n_steps(Q):
    N = Q * E_PER_C
    return N, ["Convert coulombs to electrons: N = Q × 6.25 × 10^18 electrons/C",
               f"N = {g(Q)} C × {EC} = {g(N)} electrons"]


def _to_seconds(t, unit):
    if unit == "s":
        return t, []
    factor = 60 if unit == "min" else 3600
    ts = t * factor
    return ts, [f"Convert time to seconds: t = {g(t)} {unit} × {factor} s/{unit} = {g(ts)} s"]


def _to_feet(L, unit):
    if unit == "yd":
        ft = L * 3
        return ft, [f"Convert length to feet: L = {g(L)} yd × 3 ft/yd = {g(ft)} ft"]
    if unit == "in":
        ft = L / 12
        return ft, [f"Convert length to feet: L = {g(L)} in ÷ 12 in/ft = {g(ft)} ft"]
    return L, []


TIME_HINT = {"s": "", "min": " (1 min = 60 s)", "hr": " (1 hr = 3600 s)"}
LEN_HINT = {"ft": "", "yd": " (1 yd = 3 ft)", "in": " (1 ft = 12 in)"}
# prefix key -> (symbol, multiplier)
PREFIXES = {"": ("", 1.0), "k": ("k", 1e3), "M": ("M", 1e6), "m": ("m", 1e-3), "u": ("µ", 1e-6), "n": ("n", 1e-9)}


# ---------------------------------------------------------------- solvers
# Each returns (answer, [worked-solution steps]).

def solve_n_to_q(p, cfg):
    Q = p["N"] / E_PER_C
    return Q, ["Formula: Q = N ÷ (6.25 × 10^18 electrons per coulomb)",
               f"Q = {g(p['N'])} ÷ {EC} = {g(Q)} C"]


def solve_q_to_n(p, cfg):
    N = p["Q"] * E_PER_C
    return N, ["Formula: N = Q × 6.25 × 10^18 electrons per coulomb",
               f"N = {g(p['Q'])} C × {EC} = {g(N)} electrons"]


def solve_v_from_wq(p, cfg):
    V = p["W"] / p["Q"]
    return V, ["Formula: V = W ÷ Q", f"V = {g(p['W'])} J ÷ {g(p['Q'])} C = {g(V)} V"]


def solve_w_from_vq(p, cfg):
    W = p["V"] * p["Q"]
    return W, ["Formula: W = V × Q", f"W = {g(p['V'])} V × {g(p['Q'])} C = {g(W)} J"]


def solve_w_from_vn(p, cfg):
    Q, conv = _n_to_q(p["N"])
    W = p["V"] * Q
    return W, [conv, "Formula: W = V × Q", f"W = {g(p['V'])} V × {g(Q)} C = {g(W)} J"]


def solve_q_from_vw(p, cfg):
    Q = p["W"] / p["V"]
    return Q, ["Formula: V = W ÷ Q, so Q = W ÷ V", f"Q = {g(p['W'])} J ÷ {g(p['V'])} V = {g(Q)} C"]


def solve_v_from_wn(p, cfg):
    Q, conv = _n_to_q(p["N"])
    V = p["W"] / Q
    return V, [conv, "Formula: V = W ÷ Q", f"V = {g(p['W'])} J ÷ {g(Q)} C = {g(V)} V"]


def solve_n_from_vw(p, cfg):
    Q = p["W"] / p["V"]
    N, steps = _q_to_n_steps(Q)
    return N, ["Formula: V = W ÷ Q, so Q = W ÷ V",
               f"Q = {g(p['W'])} J ÷ {g(p['V'])} V = {g(Q)} C"] + steps


def solve_i_from_qt(p, cfg):
    ts, conv = _to_seconds(p["t"], cfg["tunit"])
    I = p["Q"] / ts
    return I, conv + ["Formula: I = Q ÷ t", f"I = {g(p['Q'])} C ÷ {g(ts)} s = {g(I)} A"]


def solve_q_from_it(p, cfg):
    ts, conv = _to_seconds(p["t"], cfg["tunit"])
    Q = p["I"] * ts
    return Q, conv + ["Formula: I = Q ÷ t, so Q = I × t", f"Q = {g(p['I'])} A × {g(ts)} s = {g(Q)} C"]


def solve_t_from_ni(p, cfg):
    Q, conv = _n_to_q(p["N"])
    t = Q / p["I"]
    return t, [conv, "Formula: I = Q ÷ t, so t = Q ÷ I", f"t = {g(Q)} C ÷ {g(p['I'])} A = {g(t)} s"]


def solve_i_from_nt(p, cfg):
    Q, conv = _n_to_q(p["N"])
    ts, tconv = _to_seconds(p["t"], cfg["tunit"])
    I = Q / ts
    return I, [conv] + tconv + ["Formula: I = Q ÷ t", f"I = {g(Q)} C ÷ {g(ts)} s = {g(I)} A"]


def solve_n_from_it(p, cfg):
    ts, conv = _to_seconds(p["t"], cfg["tunit"])
    Q = p["I"] * ts
    N, steps = _q_to_n_steps(Q)
    return N, conv + ["Formula: Q = I × t", f"Q = {g(p['I'])} A × {g(ts)} s = {g(Q)} C"] + steps


def solve_t_from_iq(p, cfg):
    t = p["Q"] / p["I"]
    return t, ["Formula: I = Q ÷ t, so t = Q ÷ I", f"t = {g(p['Q'])} C ÷ {g(p['I'])} A = {g(t)} s"]


def solve_g_from_r(p, cfg):
    sym, mult = PREFIXES[cfg["prefix"]]
    R = p["R"] * mult
    steps = []
    if mult != 1:
        steps.append(f"Convert to ohms: R = {g(p['R'])} {sym}Ω = {g(p['R'])} × 10^{round(math.log10(mult))} Ω = {g(R)} Ω")
    G = 1 / R
    return G, steps + ["Formula: G = 1 ÷ R", f"G = 1 ÷ {g(R)} Ω = {g(G)} S"]


def solve_r_from_g(p, cfg):
    sym, mult = PREFIXES[cfg["prefix"]]
    G = p["G"] * mult
    R = 1 / G
    return R, [f"Convert to siemens: G = {g(p['G'])} {sym}S = {g(p['G'])} × 10^{round(math.log10(mult))} S = {g(G)} S",
               "Formula: R = 1 ÷ G", f"R = 1 ÷ {g(G)} S = {g(R)} Ω"]


def solve_wire_length(p, cfg):
    L = p["R"] * p["A"] / RHO_CU
    return L, ["Formula: R = ρL ÷ A, so L = R × A ÷ ρ",
               "ρ for copper = 10.4 Ω·CM per foot, so L comes out in feet",
               f"L = {g(p['R'])} Ω × {g(p['A'])} CM ÷ 10.4 = {g(L)} ft"]


def solve_wire_area(p, cfg):
    ft, conv = _to_feet(p["L"], cfg["lunit"])
    A = RHO_CU * ft / p["R"]
    return A, conv + ["Formula: R = ρL ÷ A, so A = ρL ÷ R (ρ for copper = 10.4 Ω·CM per foot)",
                      f"A = 10.4 × {g(ft)} ft ÷ {g(p['R'])} Ω = {g(A)} CM"]


def solve_wire_resistance(p, cfg):
    ft, conv = _to_feet(p["L"], cfg["lunit"])
    R = RHO_CU * ft / p["A"]
    return R, conv + ["Formula: R = ρL ÷ A (ρ for copper = 10.4 Ω·CM per foot)",
                      f"R = 10.4 × {g(ft)} ft ÷ {g(p['A'])} CM = {g(R)} Ω"]


# ------------------------------------------------------- variation generators
# Inputs come from short lists of hand/calculator-friendly numbers.

Q_FOR_N = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 20, 24, 25, 30, 40, 50, 64, 75, 80, 100, 120, 150, 200]
Q_GIVEN = [0.5, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 20, 24, 25, 30, 40, 50]
Q_P2 = [2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 20, 25]
V_SET = [1.5, 3, 5, 6, 9, 10, 12, 15, 18, 20, 24, 30, 48, 120]
I_SET = [0.5, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
T_SETS = {"s": [2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 20, 30],
          "min": [1, 2, 3, 4, 5, 10, 15, 20, 30, 45],
          "hr": [0.5, 1, 1.5, 2, 2.5, 3, 4, 8]}
R_SETS = {"": [10, 20, 25, 40, 50, 75, 100, 150, 200, 250, 400, 470, 500, 800, 1000],
          "k": [1, 2, 2.2, 2.5, 4, 4.7, 5, 8, 10, 20, 25, 40, 50, 100],
          "M": [1, 1.5, 2, 2.5, 4, 5, 10]}
G_SETS = {"u": [1, 2, 4, 5, 8, 10, 20, 25, 40, 50, 80, 100, 125, 200, 250, 500],
          "n": [100, 200, 250, 400, 500, 800, 1000],
          "m": [0.5, 1, 2, 2.5, 4, 5, 8, 10, 20, 25, 50]}
R5 = [0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5]
A5 = [400, 500, 625, 800, 1000, 1250, 1600, 2000, 2500, 3000, 4000, 5000]
L_SETS = {"yd": [20, 25, 50, 60, 75, 100, 120, 133, 150, 200, 250],
          "ft": [50, 100, 150, 200, 250, 300, 400, 500, 750, 1000],
          "in": [600, 900, 1200, 1500, 1800, 2100, 2400, 3000, 3600]}


def rand_electrons(rng):
    """Mostly whole/round coulomb amounts; sometimes a 9.36 × 10^20-style count."""
    if rng.random() < 0.2:
        return float(f"{rng.randint(101, 999) / 100}e{rng.choice((18, 19, 20))}")
    return rng.choice(Q_FOR_N) * E_PER_C


def _vq(rng):
    V, Q = rng.choice(V_SET), rng.choice(Q_P2)
    return V, Q, round(V * Q, 6)


def gen_v_from_wn(rng, cfg):
    if rng.random() < 0.2:
        return {"W": rng.choice([12, 24, 36, 45, 60, 75, 90, 100, 120, 150]), "N": rand_electrons(rng)}
    V, Qc = rng.choice(V_SET), rng.choice(Q_FOR_N[:15])
    return {"W": round(V * Qc, 6), "N": Qc * E_PER_C}


def gen_i_from_qt(rng, cfg):
    I, t = rng.choice(I_SET), rng.choice(T_SETS[cfg["tunit"]])
    ts, _ = _to_seconds(t, cfg["tunit"])
    return {"Q": round(I * ts, 6), "t": t}


class Kind:
    def __init__(self, quantity, fields, hint, gen, solve, electrons=False, reciprocal=False):
        self.quantity = quantity
        self.fields = fields          # param -> display format
        self.hint = hint              # str or fn(cfg) -> str
        self.gen = gen                # fn(rng, cfg) -> params
        self.solve = solve            # fn(params, cfg) -> (answer, steps)
        self.electrons = electrons    # electrons <-> coulombs conversion involved
        self.reciprocal = reciprocal  # answer is 1/x of a given


KINDS = {
    "n_to_q": Kind("charge", {"N": "sci"}, "Q = N ÷ (6.25 × 10^18 electrons per coulomb)",
                   lambda r, c: {"N": rand_electrons(r)}, solve_n_to_q, electrons=True),
    "q_to_n": Kind("electrons", {"Q": "num"}, "N = Q × 6.25 × 10^18 electrons per coulomb",
                   lambda r, c: {"Q": r.choice(Q_GIVEN)}, solve_q_to_n, electrons=True),
    "v_from_wq": Kind("voltage", {"W": "num", "Q": "num"}, "V = W ÷ Q",
                      lambda r, c: (lambda v, q, w: {"W": w, "Q": q})(*_vq(r)), solve_v_from_wq),
    "w_from_vq": Kind("energy", {"V": "num", "Q": "num"}, "W = V × Q",
                      lambda r, c: {"V": r.choice(V_SET), "Q": r.choice(Q_P2)}, solve_w_from_vq),
    "w_from_vn": Kind("energy", {"V": "num", "N": "sci"},
                      "First convert electrons to coulombs: Q = N ÷ 6.25 × 10^18. Then W = V × Q",
                      lambda r, c: {"V": r.choice(V_SET), "N": rand_electrons(r)}, solve_w_from_vn, electrons=True),
    "q_from_vw": Kind("charge", {"V": "num", "W": "num"}, "V = W ÷ Q, so Q = W ÷ V",
                      lambda r, c: (lambda v, q, w: {"V": v, "W": w})(*_vq(r)), solve_q_from_vw),
    "v_from_wn": Kind("voltage", {"W": "num", "N": "sci"},
                      "First convert electrons to coulombs: Q = N ÷ 6.25 × 10^18. Then V = W ÷ Q",
                      gen_v_from_wn, solve_v_from_wn, electrons=True),
    "n_from_vw": Kind("electrons", {"V": "num", "W": "num"}, "Q = W ÷ V, then N = Q × 6.25 × 10^18",
                      lambda r, c: (lambda v, q, w: {"V": v, "W": w})(*_vq(r)), solve_n_from_vw, electrons=True),
    "i_from_qt": Kind("current", {"Q": "num", "t": "time"},
                      lambda c: f"I = Q ÷ t, with t in seconds{TIME_HINT[c['tunit']]}",
                      gen_i_from_qt, solve_i_from_qt),
    "q_from_it": Kind("charge", {"I": "num", "t": "time"},
                      lambda c: f"Q = I × t, with t in seconds{TIME_HINT[c['tunit']]}",
                      lambda r, c: {"I": r.choice(I_SET), "t": r.choice(T_SETS[c["tunit"]])}, solve_q_from_it),
    "t_from_ni": Kind("time", {"N": "sci", "I": "num"}, "Q = N ÷ 6.25 × 10^18, then t = Q ÷ I",
                      lambda r, c: {"N": rand_electrons(r), "I": r.choice(I_SET)}, solve_t_from_ni, electrons=True),
    "i_from_nt": Kind("current", {"N": "sci", "t": "time"},
                      lambda c: f"Q = N ÷ 6.25 × 10^18, t in seconds{TIME_HINT[c['tunit']]}, then I = Q ÷ t",
                      lambda r, c: {"N": rand_electrons(r), "t": r.choice(T_SETS[c["tunit"]])},
                      solve_i_from_nt, electrons=True),
    "n_from_it": Kind("electrons", {"I": "num", "t": "time"},
                      lambda c: f"Q = I × t (t in seconds{TIME_HINT[c['tunit']]}), then N = Q × 6.25 × 10^18",
                      lambda r, c: {"I": r.choice(I_SET), "t": r.choice(T_SETS[c["tunit"]])},
                      solve_n_from_it, electrons=True),
    "t_from_iq": Kind("time", {"I": "num", "Q": "num"}, "I = Q ÷ t, so t = Q ÷ I",
                      lambda r, c: {"I": r.choice(I_SET), "Q": r.choice([5, 10, 12, 15, 20, 25, 30, 40, 50, 60, 100])},
                      solve_t_from_iq),
    "g_from_r": Kind("conductance", {"R": "num"},
                     lambda c: "G = 1 ÷ R, with R in ohms" + {"": "", "k": " (1 kΩ = 10^3 Ω)", "M": " (1 MΩ = 10^6 Ω)"}[c["prefix"]],
                     lambda r, c: {"R": r.choice(R_SETS[c["prefix"]])}, solve_g_from_r, reciprocal=True),
    "r_from_g": Kind("resistance", {"G": "num"},
                     lambda c: "R = 1 ÷ G, with G in siemens" + {"u": " (1 µS = 10^-6 S)", "n": " (1 nS = 10^-9 S)", "m": " (1 mS = 10^-3 S)"}[c["prefix"]],
                     lambda r, c: {"G": r.choice(G_SETS[c["prefix"]])}, solve_r_from_g, reciprocal=True),
    "wire_length": Kind("length", {"R": "ohms", "A": "num"}, "R = ρL ÷ A, so L = R × A ÷ ρ (ρ = 10.4 Ω·CM per foot)",
                        lambda r, c: {"R": r.choice(R5), "A": r.choice(A5)}, solve_wire_length),
    "wire_area": Kind("area", {"L": "num", "R": "ohms"},
                      lambda c: f"R = ρL ÷ A, so A = ρL ÷ R (ρ = 10.4 Ω·CM per foot, L in feet{LEN_HINT[c['lunit']]})",
                      lambda r, c: {"L": r.choice(L_SETS[c["lunit"]]), "R": r.choice(R5)}, solve_wire_area),
    "wire_resistance": Kind("resistance", {"L": "num", "A": "num"},
                            lambda c: f"R = ρL ÷ A (ρ = 10.4 Ω·CM per foot, L in feet{LEN_HINT[c['lunit']]})",
                            lambda r, c: {"L": r.choice(L_SETS[c["lunit"]]), "A": r.choice(A5)}, solve_wire_resistance),
}


# ------------------------------------------------------------------- notes
# Interpretation notes for wording that could be read more than one way.

def _note_936(p):
    if abs(p["N"] - 9.36e20) < 1e15:
        return ["Heads-up: 9.36 × 10^20 isn't an exact multiple of 6.25 × 10^18 (it gives 149.76 C). "
                "If the sheet meant 9.375 × 10^20 it would be exactly 150 C. Both versions fall inside the 1% tolerance."]
    return []


def _note_electron_time(p):
    return ["Interpretation: the electron count is converted to coulombs first (Q = N ÷ 6.25 × 10^18), "
            "then t = Q ÷ I. Dividing the electron count straight by the current doesn't give seconds."] + _note_936(p)


def _note_32(p):
    Q = p["I"] * _to_seconds(p["t"], "hr")[0]
    return ["Interpretation: \"charge in electrons\" is read as the NUMBER of electrons (N = Q × 6.25 × 10^18). "
            f"If your teacher wants coulombs instead, the charge is {fmt_answer(Q, 'charge')}. "
            "This app accepts that answer too and tells you which reading it matched."]


def _note_50(p):
    notes = [f"\"Limit resistance to {_plural(p['R'], 'ohm', 'ohms')}\" makes this the minimum wire size: "
             "more circular mils means less resistance."]
    if p["L"] == 133:
        notes.append("133 yd = 399 ft. If the sheet meant 133⅓ yd (= 400 ft), the answer is 2080 CM. "
                     "Both are inside the 1% tolerance.")
    return notes


NOTE_52 = ["\"Maximum resistance\" makes this the longest wire allowed: any shorter wire has less resistance."]


# --------------------------------------------------------------- templates

class Template:
    def __init__(self, id, part, text, kind, tunit=None, lunit=None, prefix=None, note=None,
                 alt_coulombs=False, **worksheet):
        self.id = id
        self.part = part
        self.text = text
        self.kind_name = kind
        self.kind = KINDS[kind]
        self.cfg = {"tunit": tunit, "lunit": lunit, "prefix": prefix}
        self.note = note
        self.alt_coulombs = alt_coulombs
        self.worksheet = worksheet

    @property
    def quantity(self):
        return self.kind.quantity

    def render(self, p):
        vals = {k: FIELD_FORMATS[f](p[k], self.cfg) for k, f in self.kind.fields.items()}
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

    def alternates(self, p):
        """Other accepted readings: list of (value, quantity, label)."""
        if self.alt_coulombs:
            return [(p["I"] * _to_seconds(p["t"], self.cfg["tunit"])[0], "charge", "the charge in coulombs")]
        return []

    def slips(self):
        """Conversion factors a student commonly drops: list of (factor, message)."""
        out = []
        if self.kind.electrons:
            out.append((E_PER_C, "Off by a factor of 6.25 × 10^18: electrons and coulombs got mixed up. "
                                 "Electrons → coulombs is ÷ 6.25 × 10^18; coulombs → electrons is ×."))
        if self.cfg["tunit"] == "min":
            out.append((60, "Off by a factor of 60: check the minutes → seconds conversion (1 min = 60 s)."))
        if self.cfg["tunit"] == "hr":
            out.append((3600, "Off by a factor of 3600: check the hours → seconds conversion (1 hr = 3600 s)."))
            out.append((60, "Off by a factor of 60: 1 hr is 3600 s, not 60 s."))
        if self.cfg["lunit"] == "yd":
            out.append((3, "Off by a factor of 3: convert yards to feet first (1 yd = 3 ft)."))
        if self.cfg["lunit"] == "in":
            out.append((12, "Off by a factor of 12: convert inches to feet first (1 ft = 12 in)."))
        return out

    def question(self, params, varied):
        label, unit = QUANTITIES[self.quantity]
        return {
            "template_id": self.id,
            "part": self.part,
            "part_title": PARTS[self.part],
            "text": self.render(params),
            "params": params,
            "hint": self.hint(),
            "quantity": self.quantity,
            "quantity_label": label,
            "unit": unit,
            "varied": varied,
        }


T = Template
TEMPLATES = [
    # Part 1: Coulombs and Electrons
    T(1, 1, "Calculate the charge in coulombs for {N} electrons", "n_to_q", N=6.25e18),
    T(2, 1, "How many coulombs are in {N} electrons?", "n_to_q", N=3.125e19),
    T(3, 1, "If a circuit contains {N} electrons, what is the charge in coulombs?", "n_to_q", note=_note_936, N=9.36e20),
    T(4, 1, "How many electrons are present when the charge is {Q} coulombs?", "q_to_n", Q=8),
    T(5, 1, "Calculate the number of electrons in a circuit with a charge of {Q} coulombs", "q_to_n", Q=3.5),
    T(6, 1, "Find the charge in coulombs for {N} electrons", "n_to_q", N=4.375e19),
    T(7, 1, "How many electrons create a charge of {Q} coulombs?", "q_to_n", Q=12),
    T(8, 1, "If a conductor has {N} electrons, what is Q?", "n_to_q", N=7.5e19),
    # Part 2: Voltage from Coulombs and Joules
    T(9, 2, "Calculate the voltage if energy is {W} joules and charge is {Q} coulombs", "v_from_wq", W=24, Q=4),
    T(10, 2, "Find the voltage when energy is {W} joules and charge is {Q} coulombs", "v_from_wq", W=150, Q=15),
    T(11, 2, "What is the voltage if {W} joules of energy moves {Q} coulombs of charge?", "v_from_wq", W=45, Q=9),
    T(12, 2, "Calculate the energy in joules when voltage is {V} volts and charge is {Q} coulombs", "w_from_vq", V=12, Q=3),
    T(13, 2, "Find the energy when voltage is {V} volts and the charge is {N} electrons", "w_from_vn", V=9, N=6.25e18),
    T(14, 2, "How many coulombs of charge when voltage is {V} volts and energy is {W} joules?", "q_from_vw", V=15, W=90),
    T(15, 2, "Calculate voltage if energy is {W} joules and charge is {N} electrons", "v_from_wn", W=75, N=3.125e19),
    T(16, 2, "Find the energy when voltage is {V} volts and charge is {Q} coulombs", "w_from_vq", V=24, Q=8),
    T(17, 2, "How many electrons create the charge if voltage is {V} volts and energy is {W} joules", "n_from_vw", V=6, W=48),
    T(18, 2, "Calculate the voltage when energy is {W} joules and electrons equal {N}", "v_from_wn", W=120, N=4.375e19),
    T(19, 2, "What is the energy when voltage is {V} volts and charge is {N} electrons", "w_from_vn", V=18, N=7.5e19),
    T(20, 2, "Find the charge in coulombs if voltage is {V} volts and energy is {W} joules", "q_from_vw", V=20, W=160),
    T(21, 2, "Calculate energy if voltage is {V} volts and charge is {N} electrons", "w_from_vn", note=_note_936, V=5, N=9.36e20),
    # Part 3: Electrical Current from Coulombs and Time
    T(22, 3, "Calculate the current if {Q} coulombs flow in {t}", "i_from_qt", tunit="s", Q=15, t=3),
    T(23, 3, "Find the current when {Q} coulombs pass through a wire in {t}", "i_from_qt", tunit="s", Q=45, t=9),
    T(24, 3, "What is the current if {Q} coulombs flow in {t}?", "i_from_qt", tunit="min", Q=120, t=1),
    T(25, 3, "Calculate the charge in coulombs when current is {I} amperes for {t}", "q_from_it", tunit="min", I=2, t=3),
    T(26, 3, "Find the time in seconds when {N} electrons flow with {I} amperes of current", "t_from_ni",
      note=_note_electron_time, N=6.25e18, I=4),
    T(27, 3, "What is the current if {N} electrons pass through a circuit in {t}?", "i_from_nt", tunit="hr", N=3.125e19, t=2.5),
    T(28, 3, "Calculate the number of electrons when current is {I} amperes for {t}", "n_from_it", tunit="min", I=0.5, t=45),
    T(29, 3, "Find the charge in coulombs if current is {I} amperes for {t}", "q_from_it", tunit="hr", I=1.5, t=2),
    T(30, 3, "What time in seconds is needed for {N} electrons to flow at {I} amperes?", "t_from_ni",
      note=_note_electron_time, N=9.36e20, I=3),
    T(31, 3, "Calculate the current when {N} electrons pass through in {t}", "i_from_nt", tunit="min", N=7.5e19, t=30),
    T(32, 3, "Find the charge in electrons if {I} amperes flow for {t}", "n_from_it", tunit="hr",
      note=_note_32, alt_coulombs=True, I=6, t=1.5),
    T(33, 3, "What is the current if {N} electrons flow in {t}?", "i_from_nt", tunit="min", N=4.375e19, t=20),
    T(34, 3, "Calculate the time in seconds when {I} amperes moves {Q} coulombs", "t_from_iq", I=2, Q=25),
    # Part 4: Conductance and Resistance
    T(35, 4, "Calculate the conductance of a {R} ohm resistor", "g_from_r", prefix="", R=200),
    T(36, 4, "Find the conductance when resistance is {R} ohms", "g_from_r", prefix="", R=500),
    T(37, 4, "What is the conductance of a {R} kilohm resistor?", "g_from_r", prefix="k", R=1),
    T(38, 4, "Calculate the conductance of a {R} megohm resistor", "g_from_r", prefix="M", R=2.5),
    T(39, 4, "Find the conductance when resistance is {R} ohms", "g_from_r", prefix="", R=100),
    T(40, 4, "What is the conductance of a {R} kilohm resistor?", "g_from_r", prefix="k", R=50),
    T(41, 4, "Calculate the resistance when conductance is {G} microsiemens", "r_from_g", prefix="u", G=25),
    T(42, 4, "Find the resistance if conductance equals {G} nanosiemens", "r_from_g", prefix="n", G=500),
    T(43, 4, "What is the resistance when conductance is {G} millisiemens?", "r_from_g", prefix="m", G=2),
    T(44, 4, "Calculate the resistance if conductance is {G} microsiemens", "r_from_g", prefix="u", G=100),
    # Part 5: Copper Wire Problems
    T(45, 5, "Calculate the length of a copper wire if its resistance is {R} and has {A} circular mils", "wire_length", R=2, A=1250),
    T(46, 5, "Find the circular mils needed for a {L}-yard copper wire to have a resistance of {R}", "wire_area", lunit="yd", L=100, R=1.5),
    T(47, 5, "What is the resistance of a copper wire that is {L} inches long with {A} circular mils?", "wire_resistance", lunit="in", L=2100, A=800),
    T(48, 5, "Calculate the circular mils needed for a {L}-foot copper wire to have a resistance of {R}", "wire_area", lunit="ft", L=250, R=0.75),
    T(49, 5, "Find the length of copper wire needed if you want {R} resistance with {A} circular mils", "wire_length", R=1.25, A=1600),
    T(50, 5, "What circular mils are needed to limit resistance to {R} in a {L}-yard copper wire?", "wire_area", lunit="yd", note=_note_50, L=133, R=2),
    T(51, 5, "Calculate the resistance of a copper wire that is {L} yards long with {A} circular mils", "wire_resistance", lunit="yd", L=75, A=2500),
    T(52, 5, "Find the length possible for a copper wire with {A} circular mils if maximum resistance is {R}", "wire_length", note=NOTE_52, A=900, R=3),
    T(53, 5, "What is the resistance of a copper wire that is {L} inches long with {A} circular mils", "wire_resistance", lunit="in", L=1800, A=3000),
    T(54, 5, "Calculate the circular mils needed for a {L}-yard copper wire to have a resistance of {R}", "wire_area", lunit="yd", L=60, R=1),
]

BY_ID = {t.id: t for t in TEMPLATES}
assert sorted(BY_ID) == list(range(1, 55))
