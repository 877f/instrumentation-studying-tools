"""All study modules, in the order they appear on the home screen.

Each module is one file in this folder plus one entry in CHAPTERS below.
Two kinds exist:
  * worksheet chapters (core/template.py Chapter), e.g. ch02.py: numeric
    worksheet questions with variations, a formula sheet and saved progress.
  * formula drills (core/formula.py FormulaModule), e.g. ohms_wheel.py: type
    formulas from memory, checked with sympy; levels plus a blank-wheel mode.
To add one, copy the closest example file, replace its content, and add it here.
"""
from chapters import ch02, ohms_wheel

CHAPTERS = [ch02.CHAPTER, ohms_wheel.MODULE]
BY_ID = {c.id: c for c in CHAPTERS}
assert len(BY_ID) == len(CHAPTERS), "duplicate module ids"
