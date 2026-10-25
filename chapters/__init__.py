"""All chapters, in the order they appear on the home screen.

To add a chapter: copy ch02.py to a new file (e.g. ch03.py), replace its parts,
templates and formula sheet, then add it to CHAPTERS below.
"""
from chapters import ch02

CHAPTERS = [ch02.CHAPTER]
BY_ID = {c.id: c for c in CHAPTERS}
assert len(BY_ID) == len(CHAPTERS), "duplicate chapter ids"
