"""Electrical Calculations: the Instrumentation, Automation & Robotics practice worksheet.

Ohm's and Watt's laws, kWh, efficiency and battery amp-hours. 45 worksheet questions;
1-30 have parts (a) and (b), each graded on its own as #1a, #1b..., so 75 in all.
43-45 are bonus questions written to fit answers that were on the key with no question.

Same engine as Chapter 2, with two settings of its own (see TOLERANCE and shown()):
answers within 0.5% count, and answers are shown to 3 significant figures in
engineering notation (500 mA, 3.60 kW, 24.0 V).
"""
import math
import re

from chapters.circuits import PAIRS
from core.fmt import fmt_num, fmt_sf, g, plural
from core.template import Chapter, Kind, Part, Template
from core.units import QUANTITIES

TOLERANCE = 0.005
ENGINEERING = {"voltage", "current", "resistance", "power"}      # shown with prefixes: 500 mA, 3.60 kW

PARTS = {
    1: Part("Ohm's Law and Watt's Law", "Ohm & Watt"),
    2: Part("Energy in kWh", "kWh"),
    3: Part("Efficiency", "Efficiency"),
    4: Part("Battery Life from Amp-Hours", "Amp-hours"),
}


def shown(x, quantity):
    """How every answer is displayed: 3 significant figures, engineering notation."""
    return fmt_sf(x, QUANTITIES[quantity].unit, prefix=quantity in ENGINEERING)


def final(x, quantity):
    style = "3 significant figures, engineering notation" if quantity in ENGINEERING else "3 significant figures"
    return f"Answer ({style}): {shown(x, quantity)}"


def given(unit):
    return lambda v, cfg: f"{fmt_num(v, 6)}{'' if unit == '%' else ' '}{unit}"


def count(v, cfg):
    return fmt_num(v, 6)


def kind(quantity, fields, hint, gen, solve):
    return Kind(quantity, fields, hint, gen, solve, tolerance=TOLERANCE, shown=shown)


# ------------------------------------------------- Part 1: Ohm's and Watt's laws

SYM = {"V": ("voltage", "V"), "I": ("current", "A"), "R": ("resistance", "Ω"), "P": ("power", "W")}
# (target, givens) -> (formula, how to work it out)
LAWS = {
    ("V", "IR"): ("V = I × R", lambda p: p["I"] * p["R"]),
    ("V", "IP"): ("V = P ÷ I", lambda p: p["P"] / p["I"]),
    ("V", "PR"): ("V = √(P × R)", lambda p: math.sqrt(p["P"] * p["R"])),
    ("I", "RV"): ("I = V ÷ R", lambda p: p["V"] / p["R"]),
    ("I", "PV"): ("I = P ÷ V", lambda p: p["P"] / p["V"]),
    ("I", "PR"): ("I = √(P ÷ R)", lambda p: math.sqrt(p["P"] / p["R"])),
    ("R", "IV"): ("R = V ÷ I", lambda p: p["V"] / p["I"]),
    ("R", "PV"): ("R = V² ÷ P", lambda p: p["V"] ** 2 / p["P"]),
    ("R", "IP"): ("R = P ÷ I²", lambda p: p["P"] / p["I"] ** 2),
    ("P", "IV"): ("P = V × I", lambda p: p["V"] * p["I"]),
    ("P", "IR"): ("P = I² × R", lambda p: p["I"] ** 2 * p["R"]),
    ("P", "RV"): ("P = V² ÷ R", lambda p: p["V"] ** 2 / p["R"]),
}


def law_hint(target, givens):
    """Which law to use, in words. Hints never write the formula out."""
    name = SYM[target][0]
    used = set(givens) | {target}
    if used <= set("VIR"):
        return f"Ohm's law, solved for the {name}."
    if used == set("PVI"):
        return "Watt's law, with the voltage and current." if target == "P" else f"Watt's law, solved for the {name}."
    which = "current and resistance" if used == set("PIR") else "voltage and resistance"
    if target == "P":
        return f"The power formula that uses {which}."
    root = " It needs a square root." if target in "IV" else ""
    return f"The power formula that uses {which}, solved for the {name}.{root}"


def substitute(rhs, p):
    """'V² ÷ P' -> '(120 V)² ÷ 60 W'."""
    def val(m):
        v = f"{g(p[m.group(1)])} {SYM[m.group(1)][1]}"
        return f"({v})²" if m.group(2) else v
    return re.sub(r"([VIRP])(²?)", val, rhs)


def law_solver(target, givens):
    formula, fn = LAWS[(target, givens)]
    rhs = formula.split(" = ", 1)[1]

    def solve(p, cfg):
        x = fn(p)
        q, unit = SYM[target]
        work = f"{target} = {substitute(rhs, p)}"
        if "√" in rhs:
            work += f" = √{g(x * x)}"
        return x, [f"Formula: {formula}", f"{work} = {g(x)} {unit}", final(x, q)]
    return solve


_pools = {}


def gen_law(rng, cfg):
    """New numbers near the worksheet's own (an LED stays LED-sized), from clean V/R pairs."""
    givens, ws = cfg["givens"], cfg["near"]
    key = (givens, tuple(sorted(ws.items())))
    if key not in _pools:
        for factor in (4, 10, math.inf):
            pool = []
            for V, R in PAIRS:
                every = {"V": V, "R": R, "I": V / R, "P": V * V / R}
                if all(ws[k] / factor <= every[k] <= ws[k] * factor for k in givens):
                    pool.append({k: float(every[k]) for k in givens})
            if len(pool) >= 6:
                break
        _pools[key] = pool
    return dict(rng.choice(_pools[key]))


KINDS = {}
for (target, givens) in LAWS:
    KINDS[target + givens] = kind(SYM[target][0], {k: given(SYM[k][1]) for k in givens}, law_hint(target, givens),
                                  gen_law, law_solver(target, givens))


# ------------------------------------------------------------- Part 2: kWh

def solve_kwh(p, cfg):
    wh = p["P"] * p["h"]
    e = wh / 1000
    return e, ["Formula: kWh = (W × h) ÷ 1000",
               f"kWh = ({g(p['P'])} W × {g(p['h'])} h) ÷ 1000 = {g(wh)} Wh ÷ 1000 = {g(e)} kWh", final(e, "kwh")]


def solve_kwh_iv(p, cfg):
    P = p["V"] * p["I"]
    wh = P * p["h"]
    e = wh / 1000
    return e, [f"Power first: P = V × I = {g(p['V'])} V × {g(p['I'])} A = {g(P)} W",
               "Formula: kWh = (W × h) ÷ 1000",
               f"kWh = ({g(P)} W × {g(p['h'])} h) ÷ 1000 = {g(wh)} Wh ÷ 1000 = {g(e)} kWh", final(e, "kwh")]


def solve_kwh_house(p, cfg):
    bulbs = p["n"] * p["Wb"] * p["hb"]
    tv = p["Wt"] * p["ht"]
    laptop = p["Wl"] * p["hl"]
    wh = bulbs + tv + laptop
    e = wh / 1000
    return e, [f"Bulbs: {g(p['n'])} × {g(p['Wb'])} W × {g(p['hb'])} h = {g(bulbs)} Wh",
               f"TV: {g(p['Wt'])} W × {g(p['ht'])} h = {g(tv)} Wh",
               f"Laptop: {g(p['Wl'])} W × {g(p['hl'])} h = {g(laptop)} Wh",
               f"Total: {g(bulbs)} Wh + {g(tv)} Wh + {g(laptop)} Wh = {g(wh)} Wh",
               f"kWh = {g(wh)} Wh ÷ 1000 = {g(e)} kWh", final(e, "kwh")]


def solve_kwh_motors(p, cfg):
    kw = p["n"] * p["kW"]
    e = kw * p["h"]
    return e, [f"Total power first: {g(p['n'])} motors × {g(p['kW'])} kW = {g(kw)} kW = {g(kw * 1000)} W",
               "Formula: kWh = (W × h) ÷ 1000",
               f"kWh = ({g(kw * 1000)} W × {g(p['h'])} h) ÷ 1000 = {g(e)} kWh per day",
               f"The {plural(p['d'], 'day', 'days')} per week doesn't change the daily figure.", final(e, "kwh")]


def pick(**sets):
    return lambda rng, cfg: {k: rng.choice(v) for k, v in sets.items()}


def HOURS(v, cfg):
    return plural(v, "hour", "hours")


KINDS.update({
    "kwh": kind("kwh", {"P": given("W"), "h": HOURS}, "Multiply to get watt-hours first, then change them into kilowatt-hours.",
                lambda rng, cfg: {"P": rng.choice(cfg["P_set"]), "h": rng.choice(cfg["h_set"])}, solve_kwh),
    "kwh_iv": kind("kwh", {"I": given("A"), "V": given("V"), "h": HOURS},
                   "Find the power from the current and voltage first, then the energy.",
                   pick(I=[10, 12, 15, 16, 20, 24, 30], V=[120, 208, 240], h=[4, 5, 6, 8, 10, 12]), solve_kwh_iv),
    "kwh_house": kind("kwh", {"n": count, "Wb": given("W"), "hb": HOURS, "Wt": given("W"), "ht": HOURS,
                              "Wl": given("W"), "hl": HOURS},
                      "Find each item's watt-hours, add them up, then change the total into kilowatt-hours.",
                      pick(n=[2, 3, 4, 5, 6, 8], Wb=[8, 9, 10, 12, 15], hb=[3, 4, 5, 6, 8], Wt=[100, 120, 150, 200, 250],
                           ht=[2, 3, 4, 5, 6], Wl=[45, 60, 65, 90], hl=[3, 4, 6, 8, 10]), solve_kwh_house),
    "kwh_motors": kind("kwh", {"n": count, "kW": given("kW"), "h": HOURS, "d": lambda v, cfg: plural(v, "day", "days")},
                       "Find the total power of all the motors first. Only one day counts here.",
                       pick(n=[2, 3, 4, 5, 6, 8], kW=[1.5, 2, 3, 5, 7.5, 10], h=[8, 10, 12, 16, 24], d=[5, 6, 7]),
                       solve_kwh_motors),
})


# ------------------------------------------------------- Part 3: efficiency

EFF = [75, 80, 85, 88, 90, 92, 94, 95]
WATTS = [50, 100, 120, 150, 200, 240, 250, 300, 400, 500, 600, 800, 1000]


def solve_eff(p, cfg):
    e = p["Pout"] / p["Pin"] * 100
    return e, ["Formula: Efficiency = (Pout ÷ Pin) × 100%",
               f"Efficiency = ({g(p['Pout'])} W ÷ {g(p['Pin'])} W) × 100% = {g(e)}%", final(e, "percent")]


def solve_pin(p, cfg):
    pin = p["Pout"] / (p["eff"] / 100)
    return pin, ["Formula: Efficiency = (Pout ÷ Pin) × 100%, so Pin = Pout ÷ (efficiency as a decimal)",
                 f"Pin = {g(p['Pout'])} W ÷ {g(p['eff'] / 100)} = {g(pin)} W", final(pin, "power")]


def solve_pout(p, cfg):
    pout = p["Pin"] * p["eff"] / 100
    return pout, ["Formula: Efficiency = (Pout ÷ Pin) × 100%, so Pout = Pin × (efficiency as a decimal)",
                  f"Pout = {g(p['Pin'])} W × {g(p['eff'] / 100)} = {g(pout)} W", final(pout, "power")]


def gen_eff(rng, cfg):
    pin, eff = rng.choice(WATTS), rng.choice(EFF)
    return {"Pout": round(pin * eff / 100, 6), "Pin": pin}


KINDS.update({
    "eff": kind("percent", {"Pout": given("W"), "Pin": given("W")},
                "Efficiency compares what comes out to what goes in, as a percent.", gen_eff, solve_eff),
    "pin": kind("power", {"eff": given("%"), "Pout": given("W")},
                "Work backwards from the efficiency. The input is always more than the output.",
                pick(eff=EFF, Pout=WATTS), solve_pin),
    "pout": kind("power", {"eff": given("%"), "Pin": given("W")},
                 "Use the efficiency as a decimal. The output is always less than the input.",
                 pick(eff=EFF, Pin=WATTS), solve_pout),
})


# ------------------------------------------------------ Part 4: amp-hours

def solve_ah(p, cfg):
    h = p["Ah"] / p["I"]
    steps = ["Formula: hours = Ah ÷ A"]
    if "V" in p:
        steps.append(f"The {g(p['V'])} V rating doesn't change the run time; only the amp-hours and the current matter.")
    return h, steps + [f"hours = {g(p['Ah'])} Ah ÷ {g(p['I'])} A = {g(h)} h", final(h, "hours")]


def solve_ah_ma(p, cfg):
    amps = p["mA"] / 1000
    h = p["Ah"] / amps
    return h, [f"Change the current to amps: {g(p['mA'])} mA ÷ 1000 = {g(amps)} A",
               "Formula: hours = Ah ÷ A",
               f"hours = {g(p['Ah'])} Ah ÷ {g(amps)} A = {g(h)} h", final(h, "hours")]


AH_HINT = "Share the battery's amp-hours out at the device's current."
KINDS.update({
    "ah_v": kind("hours", {"V": given("V"), "Ah": given("Ah"), "I": given("A")}, AH_HINT + " The voltage doesn't matter here.",
                 pick(V=[6, 12, 24, 48], Ah=[7, 12, 20, 35, 50, 60, 100, 200], I=[0.5, 1, 1.5, 2, 2.5, 4, 5]), solve_ah),
    "ah": kind("hours", {"Ah": given("Ah"), "I": given("A")}, AH_HINT,
               pick(Ah=[5, 10, 12, 20, 35, 40, 50, 100], I=[0.5, 1, 1.5, 2, 2.5, 3, 4, 5]), solve_ah),
    "ah_ma": kind("hours", {"Ah": given("Ah"), "mA": given("mA")}, "Change the milliamps into amps first. " + AH_HINT,
                  pick(Ah=[1.2, 2, 2.4, 3, 5, 7.2, 10], mA=[100, 150, 200, 250, 400, 500, 750, 800]), solve_ah_ma),
})


# --------------------------------------------------------------- templates

AN = re.compile(r"\b([Aa]) (?=8|1[18](?!\d))")


class CalcTemplate(Template):
    """A worksheet template that writes "an 8 V battery", not "a 8 V battery", when new numbers come in."""

    def render(self, p):
        return AN.sub(lambda m: m.group(1) + "n ", super().render(p))


BONUS = ["Bonus question: the answer key had this answer with no worksheet question, so this question was written to fit it."]


def Q2(n, stem, a, b, **worksheet):
    """Worksheet question n with parts (a) and (b): two templates, #na and #nb, sharing the givens."""
    givens = "".join(sorted(worksheet))
    out = []
    for i, (target, ask) in enumerate((a, b)):
        k = KINDS[target + givens]
        out.append(CalcTemplate(2 * n - 1 + i, 1, f"{stem} ({'ab'[i]}) {ask}", k, worksheet,
                                cfg={"givens": givens, "near": worksheet}, label=f"{n}{'ab'[i]}"))
    return out


def Q(number, part, text, kind_key, note=None, cfg=None, **worksheet):
    """Worksheet question 31-45: one template. Ids carry on from Part 1's 60."""
    return CalcTemplate(30 + number, part, text, KINDS[kind_key], worksheet, cfg=cfg, note=note, label=str(number))


SECTION_1 = [
    Q2(1, "A circuit has a resistance of {R} and a current of {I}.",
       ("V", "Find the voltage."), ("P", "Find the power."), R=12, I=2),
    Q2(2, "A household circuit runs at {V} and draws {I}.",
       ("R", "Find the resistance."), ("P", "Find the power."), V=120, I=3),
    Q2(3, "A {P} light bulb operates on {V}.",
       ("I", "Determine the current draw."), ("R", "Determine the resistance of the filament."), P=60, V=120),
    Q2(4, "A heater draws {I} at {V}.",
       ("P", "Find the power."), ("R", "Find the resistance of the heater."), I=15, V=240),
    Q2(5, "A resistor of {R} dissipates {P}.",
       ("I", "Find the current through it."), ("V", "Find the voltage across it."), P=25, R=100),
    Q2(6, "An electric motor draws {I} from a {V} supply.",
       ("P", "Find the power."), ("R", "Find the resistance of the motor."), I=8, V=24),
    Q2(7, "An appliance uses {P} and draws {I}.",
       ("V", "Find the voltage."), ("R", "Find the resistance."), P=1200, I=5),
    Q2(8, "A {R} resistor is connected to {V}.",
       ("I", "Find the current."), ("P", "Find the power."), R=220, V=110),
    Q2(9, "A device uses {P} and has a resistance of {R}.",
       ("I", "Find the current."), ("V", "Find the voltage."), P=500, R=48),
    Q2(10, "A lamp on a {V} supply is rated at {P}.",
       ("I", "Find the current."), ("R", "Find the resistance."), V=12, P=36),
    Q2(11, "A computer power supply delivers {V} at {I} to a component.",
       ("P", "Find the power."), ("R", "Find the resistance of the component."), V=3.3, I=0.5),
    Q2(12, "An LED has a voltage drop of {V} and a resistance of {R}.",
       ("I", "Find the current."), ("P", "Find the power."), V=2, R=100),
    Q2(13, "A load uses {P} on a {V} supply.",
       ("I", "Find the current."), ("R", "Find the resistance."), P=75, V=15),
    Q2(14, "A resistor carries {I} and dissipates {P}.",
       ("V", "Find the voltage across it."), ("R", "Find its resistance."), I=4, P=64),
    Q2(15, "A battery of {V} is connected across a resistor of {R}.",
       ("I", "Find the current."), ("P", "Find the power."), V=9, R=3),
    Q2(16, "A heating element is rated {P} at {V}.",
       ("I", "Find the current."), ("R", "Find the resistance of the element."), P=2400, V=240),
    Q2(17, "A current of {I} flows through a {R} resistor.",
       ("V", "Find the voltage across it."), ("P", "Find the power."), I=0.1, R=470),
    Q2(18, "A speaker has an impedance of {R} and operates at {V}.",
       ("I", "Calculate the current."), ("P", "Calculate the power rating."), R=8, V=24),
    Q2(19, "A device with a resistance of {R} draws {I}.",
       ("V", "Find the voltage."), ("P", "Find the power."), I=1.5, R=40),
    Q2(20, "A load with a resistance of {R} dissipates {P}.",
       ("I", "Find the current."), ("V", "Find the voltage."), P=100, R=16),
    Q2(21, "A load of {R} is connected to a {V} supply.",
       ("I", "Find the current."), ("P", "Find the power."), V=48, R=32),
    Q2(22, "A motor draws {I} and uses {P}.",
       ("V", "Find the voltage."), ("R", "Find the resistance of the motor."), I=6, P=720),
    Q2(23, "A sensor on a {V} supply uses {P}.",
       ("I", "Find the current."), ("R", "Find the resistance."), V=5, P=0.5),
    Q2(24, "A resistor drops {V} with {I} flowing through it.",
       ("R", "Find its resistance."), ("P", "Find the power it dissipates."), I=0.25, V=6),
    Q2(25, "An appliance on a {V} circuit uses {P}.",
       ("I", "Find the current."), ("R", "Find the resistance."), V=120, P=360),
    Q2(26, "A current of {I} flows through a resistor of {R}.",
       ("V", "Find the voltage across it."), ("P", "Find the power."), R=150, I=0.4),
    Q2(27, "A supply of {V} is connected across a load of {R}.",
       ("I", "Find the current."), ("P", "Find the power."), V=18, R=9),
    Q2(28, "A load uses {P} and draws {I}.",
       ("V", "Find the voltage."), ("R", "Find the resistance."), P=40, I=2),
    Q2(29, "A load uses {P} on a {V} supply.",
       ("I", "Find the current."), ("R", "Find the resistance."), P=200, V=50),
    Q2(30, "A heater has a resistance of {R} and draws {I}.",
       ("V", "Find the voltage."), ("P", "Find the power."), R=20, I=5),
]

TEMPLATES = [t for pair in SECTION_1 for t in pair] + [
    # Part 2: kWh
    Q(31, 2, "A {P} space heater runs for {h}. How much energy does it use, in kWh?", "kwh",
      cfg={"P_set": [750, 1000, 1200, 1500, 1800, 2000], "h_set": [2, 3, 4, 5, 6, 8]}, P=1500, h=6),
    Q(32, 2, "An air conditioner draws {I} at {V} and runs {h} a day. How many kWh does it use each day?", "kwh_iv",
      I=20, V=240, h=8),
    Q(33, 2, "In one day, a household runs {n} LED bulbs at {Wb} each for {hb}, a TV at {Wt} for {ht}, and a laptop "
             "at {Wl} for {hl}. What is the total energy used, in kWh?", "kwh_house",
      n=4, Wb=15, hb=6, Wt=200, ht=4, Wl=65, hl=8),
    Q(34, 2, "An EV charger delivers {P} for {h}. How much energy does it deliver, in kWh?", "kwh",
      cfg={"P_set": [3300, 6600, 7200, 7680, 9600, 11500], "h_set": [3, 4, 5, 6, 8, 10]}, P=7200, h=6),
    Q(35, 2, "A factory runs {n} motors rated {kW} each for {h} a day, {d} a week. How many kWh do the motors "
             "use per day?", "kwh_motors", n=5, kW=5, h=12, d=5),
    # Part 3: Efficiency
    Q(36, 3, "A converter delivers {Pout} to a load while drawing {Pin}. What is its efficiency?", "eff",
      Pout=200, Pin=250),
    Q(37, 3, "A power supply is {eff} efficient and delivers {Pout}. How much input power does it draw?", "pin",
      eff=85, Pout=300),
    Q(38, 3, "A converter is {eff} efficient and draws {Pin}. What is its output power?", "pout", eff=90, Pin=400),
    Q(39, 3, "A device takes in {Pin} and puts out {Pout}. What is its efficiency?", "eff", Pin=150, Pout=135),
    Q(40, 3, "A power supply delivers {Pout} at {eff} efficiency. What is its input power?", "pin", Pout=800, eff=92),
    # Part 4: Amp-hours
    Q(41, 4, "A {V}, {Ah} battery powers a device that draws {I}. How many hours will it last?", "ah_v",
      V=12, Ah=100, I=2),
    Q(42, 4, "A device draws {mA} from a {Ah} battery. How many hours will it last?", "ah_ma", mA=500, Ah=7.2),
    Q(43, 4, "Bonus: a camping lantern draws {I} from a {Ah} battery pack. How many hours will it run?", "ah",
      note=BONUS, I=1.5, Ah=20),
    Q(44, 4, "Bonus: a work light draws {mA} from a {Ah} cordless-tool battery. How many hours will it run?", "ah_ma",
      note=BONUS, mA=750, Ah=5),
    Q(45, 4, "Bonus: a trolling motor draws {I} from a {Ah} deep-cycle battery. How many hours can it run?", "ah",
      note=BONUS, I=4, Ah=40),
]

FORMULAS = [
    {"title": "Part 1: Ohm's Law and Watt's Law", "items": [
        {"name": "Ohm's law", "formula": "V = I × R", "note": "I = V ÷ R · R = V ÷ I"},
        {"name": "Watt's law", "formula": "P = V × I", "note": "I = P ÷ V · V = P ÷ I"},
        {"name": "Power from current and resistance", "formula": "P = I² × R", "note": "R = P ÷ I² · I = √(P ÷ R)"},
        {"name": "Power from voltage and resistance", "formula": "P = V² ÷ R", "note": "R = V² ÷ P · V = √(P × R)"},
    ]},
    {"title": "Part 2: Energy in kWh", "items": [
        {"name": "Kilowatt-hours", "formula": "kWh = (W × h) ÷ 1000", "note": "W × h gives watt-hours (Wh)."},
    ]},
    {"title": "Part 3: Efficiency", "items": [
        {"name": "Efficiency", "formula": "Efficiency = (Pout ÷ Pin) × 100%",
         "note": "Pin = Pout ÷ efficiency · Pout = Pin × efficiency, with the efficiency as a decimal (85% = 0.85)"},
    ]},
    {"title": "Part 4: Battery Life from Amp-Hours", "items": [
        {"name": "Run time", "formula": "hours = Ah ÷ A", "note": "Change mA to A first: 500 mA = 0.5 A."},
    ]},
    {"title": "Answers", "items": [
        {"name": "Format", "formula": "3 significant figures, engineering notation",
         "note": "Exponents in multiples of 3: 500 mA, 3.60 kW, 40.0 mW. Answers within 0.5% count."},
    ]},
]

CHAPTER = Chapter("calc", 3, "Electrical Calculations", PARTS, TEMPLATES, FORMULAS)
