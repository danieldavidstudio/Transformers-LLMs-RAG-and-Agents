#!/usr/bin/env bash
# © 2026 Marc Alier i Forment (UPC) · CC BY-NC-SA 4.0 · BSC Agents Course (advanced / ungraded demo)
#
# ralph.sh — a convergence loop, shipped as a CLI.
#
# A Ralph loop (after Geoffrey Huntley) is a convergence loop: run the agent on a
# goal, check whether it converged, repeat until it has (or you run out of patience).
# In this methodology it needs no framework primitive — it IS bash. The agent is a
# CLI (the Turtle); the convergence check is another CLI whose EXIT CODE is the
# handoff protocol. Bash semantics carry the orchestration logic.
#
#   ./ralph.sh "fix the failing test" ./check_done.sh 10
#
# arg1 = the goal   arg2 = a check CLI (exit 0 == converged)   arg3 = max iterations
set -euo pipefail

goal="$1"; check_cli="$2"; max_iter="${3:-10}"
TURTLE="${TURTLE:-../../../week-04/demos/turtle/turtle.py}"
session=$(uuidgen)

for i in $(seq 1 "$max_iter"); do
  echo "── iteration $i ──"
  python3 "$TURTLE" "$session" "make progress on: $goal"
  if "$check_cli"; then
    echo "converged in $i iter"; exit 0
  fi
done
echo "did not converge in $max_iter iter"; exit 1
