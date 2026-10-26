"""Quantities the grader understands: answer unit, accepted spellings, prefixes.

A new chapter that needs a new quantity (say, power in watts) adds one entry
to QUANTITIES; nothing else in the engine changes.
"""


class Quantity:
    def __init__(self, label, unit, unit_name, aliases, eng=None, prefixable=True):
        self.label = label            # "current"
        self.unit = unit              # "A", shown in answers
        self.unit_name = unit_name    # "amperes (A)", shown in messages
        self.aliases = aliases        # lower-case spelling -> factor to the base unit
        self.eng = eng                # None, "all" (556 µA) or "large" (40 kΩ but not 936 mΩ)
        self.prefixable = prefixable  # whether "did you mean 556 µA?" hints make sense


QUANTITIES = {
    "charge": Quantity("charge", "C", "coulombs (C)", {"c": 1, "coulomb": 1, "coulombs": 1, "coul": 1}),
    "electrons": Quantity("number of electrons", "electrons", "electrons",
                          {"electron": 1, "electrons": 1, "e-": 1, "e": 1, "el": 1, "elec": 1}, prefixable=False),
    "voltage": Quantity("voltage", "V", "volts (V)", {"v": 1, "volt": 1, "volts": 1}),
    "energy": Quantity("energy", "J", "joules (J)", {"j": 1, "joule": 1, "joules": 1}),
    "current": Quantity("current", "A", "amperes (A)",
                        {"a": 1, "amp": 1, "amps": 1, "ampere": 1, "amperes": 1}, eng="all"),
    "time": Quantity("time", "s", "seconds (s)",
                     {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1, "min": 60, "mins": 60, "minute": 60,
                      "minutes": 60, "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600}),
    "conductance": Quantity("conductance", "S", "siemens (S)",
                            {"s": 1, "siemens": 1, "siemen": 1, "mho": 1, "mhos": 1}, eng="all"),
    "resistance": Quantity("resistance", "Ω", "ohms (Ω)",
                           {"ohm": 1, "ohms": 1, "kilohm": 1e3, "kilohms": 1e3}, eng="large"),
    "length": Quantity("length", "ft", "feet (ft)",
                       {"ft": 1, "foot": 1, "feet": 1, "'": 1, "yd": 3, "yds": 3, "yard": 3, "yards": 3,
                        "in": 1 / 12, "inch": 1 / 12, "inches": 1 / 12, '"': 1 / 12}, prefixable=False),
    "power": Quantity("power", "W", "watts (W)", {"w": 1, "watt": 1, "watts": 1}, eng="all"),
    "area": Quantity("cross-section area", "CM", "circular mils (CM)",
                     {"cm": 1, "cmil": 1, "cmils": 1, "mil": 1, "mils": 1, "circular mil": 1, "circular mils": 1,
                      "circ mil": 1, "circ mils": 1, "mcm": 1000}, prefixable=False),
}

ENG_PREFIX = {-12: "p", -9: "n", -6: "µ", -3: "m", 0: "", 3: "k", 6: "M", 9: "G"}
PREFIX_WORDS = [("pico", 1e-12), ("nano", 1e-9), ("micro", 1e-6), ("milli", 1e-3),
                ("kilo", 1e3), ("mega", 1e6), ("meg", 1e6), ("giga", 1e9)]
# Case matters only where it changes the meaning: m = milli, M = mega.
PREFIX_CHARS = {"p": 1e-12, "n": 1e-9, "N": 1e-9, "u": 1e-6, "U": 1e-6, "m": 1e-3, "M": 1e6,
                "k": 1e3, "K": 1e3, "g": 1e9, "G": 1e9}
