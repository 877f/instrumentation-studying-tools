"""Ohm's Law Wheel: the 12 wheel formulas, derived from V = I × R and P = V × I.

Content only. The engine (parsing, sympy checking, levels, blank wheel) is
core/formula.py. Scope is strict: these 12 formulas and the 2 base equations.
"""
from core.formula import Formula, FormulaModule, Level, Variable

VARIABLES = {
    "V": Variable("voltage", "voltage"),
    "I": Variable("current", "current"),
    "R": Variable("resistance", "resistance"),
    "P": Variable("power", "power"),
}
# Accepted, with a reminder: some textbooks use U for voltage.
ALIASES = {"U": ("V", "Accepted U, but our class uses V for voltage.")}

VIR = "V = I × R"
PVI = "P = V × I"

FORMULAS = [
    # P quadrant
    Formula("P", "VI", "V*I", "V × I", [PVI], [
        "P = V × I is a base equation."]),
    Formula("P", "IR", "I^2*R", "I² × R", [PVI, VIR], [
        "Start with P = V × I.",
        "Replace V using V = I × R: P = (I × R) × I.",
        "Collect the I's: P = I² × R."]),
    Formula("P", "VR", "V^2/R", "V² / R", [PVI, VIR], [
        "Start with P = V × I.",
        "From V = I × R, divide both sides by R: I = V / R.",
        "Replace I: P = V × V / R.",
        "So P = V² / R."]),
    # I quadrant
    Formula("I", "VR", "V/R", "V / R", [VIR], [
        "Start with V = I × R.",
        "Divide both sides by R: I = V / R."]),
    Formula("I", "PV", "P/V", "P / V", [PVI], [
        "Start with P = V × I.",
        "Divide both sides by V: I = P / V."]),
    Formula("I", "PR", "sqrt(P/R)", "√(P / R)", [PVI, VIR], [
        "Start with P = V × I.",
        "Replace V using V = I × R: P = I × R × I = I² × R.",
        "Divide both sides by R: I² = P / R.",
        "Take the square root: I = √(P / R)."]),
    # V quadrant
    Formula("V", "IR", "I*R", "I × R", [VIR], [
        "V = I × R is a base equation."]),
    Formula("V", "PI", "P/I", "P / I", [PVI], [
        "Start with P = V × I.",
        "Divide both sides by I: V = P / I."]),
    Formula("V", "PR", "sqrt(P*R)", "√(P × R)", [PVI, VIR], [
        "Start with P = V × I.",
        "From V = I × R, divide both sides by R: I = V / R.",
        "Replace I: P = V × V / R = V² / R.",
        "Multiply both sides by R: V² = P × R.",
        "Take the square root: V = √(P × R)."]),
    # R quadrant
    Formula("R", "VI", "V/I", "V / I", [VIR], [
        "Start with V = I × R.",
        "Divide both sides by I: R = V / I."]),
    Formula("R", "VP", "V^2/P", "V² / P", [PVI, VIR], [
        "Start with P = V × I.",
        "From V = I × R, divide both sides by R: I = V / R.",
        "Replace I: P = V × V / R = V² / R.",
        "Multiply both sides by R, then divide both sides by P: R = V² / P."]),
    Formula("R", "PI", "P/I^2", "P / I²", [PVI, VIR], [
        "Start with P = V × I.",
        "Replace V using V = I × R: P = I × (I × R) = I² × R.",
        "Divide both sides by I²: R = P / I²."]),
]

ALL = [f.key for f in FORMULAS]

LEVELS = [
    Level(1, "Transpose V = IR", "Given V = IR, solve for I, for R and for V.",
          ["I:VR", "R:VI", "V:IR"], prompt="Given V = I × R, solve for {target}."),
    Level(2, "Transpose P = VI", "Given P = VI, solve for V and for I.",
          ["V:PI", "I:PV"], prompt="Given P = V × I, solve for {target}."),
    Level(3, "Substitute", "Combine both base equations to get the squared and square-root forms.",
          ["P:IR", "P:VR", "I:PR", "V:PR", "R:VP", "R:PI"],
          prompt="Using V = I × R and P = V × I, write {target} in terms of {knowns}."),
    Level(4, "Full wheel", "Random questions from all 12 formulas.", ALL),
    Level(5, "Numeric", "Plug in values and solve, with units.", ALL, numeric=True),
]

# Level 5 numbers: pick a current and a resistance, derive V and P, so every
# answer (including the square-root forms) comes out clean.
CURRENT_RESISTANCE = [
    (2, 6), (3, 4), (0.5, 24), (1.5, 8), (4, 3), (5, 10), (2, 50), (10, 12), (0.25, 48), (6, 2),
    (2, 12), (3, 40), (0.5, 240), (0.1, 120),
    (0.002, 4700), (0.01, 1000), (0.005, 2000), (0.02, 500), (0.003, 3000),
]


def numeric_values(rng):
    I, R = rng.choice(CURRENT_RESISTANCE)
    return {"I": I, "R": R, "V": I * R, "P": I * I * R}


MODULE = FormulaModule(
    id="ohms-wheel",
    title="Ohm's Law Wheel",
    badge="Ω",
    intro="Learn all 12 wheel formulas by deriving them from V = I × R and P = V × I. "
          "Nothing is saved: your stats reset when you close the page.",
    variables=VARIABLES,
    aliases=ALIASES,
    base=[VIR, PVI],
    formulas=FORMULAS,
    levels=LEVELS,
    quadrants=["P", "I", "V", "R"],
    numeric_values=numeric_values,
)
