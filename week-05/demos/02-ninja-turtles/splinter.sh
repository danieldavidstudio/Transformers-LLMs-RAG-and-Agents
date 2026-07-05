#!/usr/bin/env bash
# © 2026 Marc Alier i Forment (UPC) · CC BY-NC-SA 4.0 · BSC Agents Course (advanced / ungraded demo)
#
# splinter.sh — multi-agent orchestration is CLI composition.
#
# Once your agent ships as a CLI (the Turtle), orchestrating several is not a new
# thing to learn: another agent's CLI is just another tool. A parent (Splinter)
# delegates to children (specialist Turtles) exactly the way it would call `gh` or
# `git`. The plan flows from one child to the next as an ORDINARY SHELL VARIABLE —
# no shared typed-state object, no framework message bus.
#
#   ./splinter.sh "write a haiku about warehouse robots and save it"
#
# This toy uses ONE turtle.py binary and gives each child a role via its prompt.
# In a real topology each role (Leonardo/Donatello/Michelangelo/Raphael) is its
# own Turtle CLI with its own scaffolding and its own allow-list.
set -euo pipefail

TURTLE="${TURTLE:-../../../week-04/demos/turtle/turtle.py}"
goal="${1:-list the files here and summarise what this project is}"

# call_cli: dispatch to a child Turtle in a given role. The parent does not know
# (or care) that the child is an LLM — it is a subprocess with an exit code and stdout.
call_cli() {  # $1 = role, $2 = task
  python3 "$TURTLE" "[role: $1] $2"
}

echo "🐢 SPLINTER orchestrating — goal: $goal"
echo

echo "── delegate to LEONARDO (planner) ──"
plan=$(call_cli leonardo "produce a short numbered plan for: $goal")
echo "$plan"
echo

echo "── delegate to RAPHAEL (executor), passing the plan as a shell variable ──"
# the plan is just a string; it flows into the next call with no framework primitive
call_cli raphael "carry out step 1 of this plan, using only read-only commands:

$plan"

echo
echo "orchestration done — each child was a CLI; the plan was a shell variable."
