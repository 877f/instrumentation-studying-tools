"""All study modules, in the order they appear on the home screen.

Each module is one file in this folder plus one entry in CHAPTERS below.
Three kinds exist:
  * worksheet chapters (core/template.py Chapter), e.g. ch02.py and calc.py:
    numeric worksheet questions with variations, a formula sheet and saved progress.
  * formula drills (core/formula.py FormulaModule), e.g. ohms_wheel.py: type
    formulas from memory, checked with sympy; levels plus a blank-wheel mode.
  * problem sets (core/problems.py ProblemModule), e.g. kwh.py and circuits.py:
    levels of multi-box numeric problems drawn as a table or a circuit diagram.
To add one, copy the closest example file, replace its content, and add it here.

Study-guide chapters (core/study.py), e.g. Geometry, are the exception: each is a folder in
content/study/, picked up automatically and listed after the modules above.
"""
from chapters import calc, ch02, circuits, kwh, ohms_wheel
from core import study

CHAPTERS = [ch02.CHAPTER, ohms_wheel.MODULE, kwh.MODULE, circuits.MODULE, calc.CHAPTER] + study.load_all()
BY_ID = {c.id: c for c in CHAPTERS}
assert len(BY_ID) == len(CHAPTERS), "duplicate module ids"
