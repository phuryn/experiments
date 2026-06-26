---
name: bug-finder
description: Review a Python solution against a markdown spec, run it, and report bugs.
---

# Bug Finder

When reviewing code:

1. Read the spec (a `.md` file) and the solution (a `.py` file).
2. Actually run the solution to test it against the spec.
3. Report every bug in this exact format, one per bug:
   `BUG: <what is wrong> | FIX: <the one-line fix>`
4. If correct, output `NO BUGS`.
