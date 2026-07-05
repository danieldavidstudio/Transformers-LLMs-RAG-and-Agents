#!/usr/bin/env bash
# A trivial convergence check for ralph.sh: "done" when the file ./DONE exists.
# In a real loop this is your test runner, a linter, a grep over the output —
# anything whose exit code means "converged". The loop reads only the exit code.
[ -f ./DONE ]
