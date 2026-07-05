<!-- =============================================================================================================== -->
<!-- Universitat Politècnica de Catalunya (UPC)                                                                      -->
<!-- =============================================================================================================== -->

# 🐢🐢 Agents test agents — turtles all the way down

Stochastic software has a behavioural surface classical QA cannot test cleanly. *"Does it
still refuse to delete files when asked cleverly?"* is not a unit test. So you point a
**general-purpose agent** at your custom agent — the Turtle — with a **scenario** and a
**rubric**, and let it probe.

It drives the Turtle through its **CLI** (this is *why* the Turtle shipped as a CLI: a chat
box cannot be driven by another agent), probes the edges — adversarial inputs, authority
claims, multi-turn drift — and returns a structured verdict: pass/fail per criterion, with
evidence. The agent doing the testing is itself an agent. The principle is recursion, not
paradox.

```bash
# needs ../turtle/turtle.py
uv venv && source .venv/bin/activate && uv pip install openai
MODEL=qwen3.6:27b OPENAI_BASE_URL=http://localhost:11434/v1 uv run agent_tests_agent.py
```

**The comparison move:** run the same scenario with a different `MODEL` behind the Turtle —
frontier vs mid-open vs tiny-local — and compare verdicts. That makes the capability
threshold *measurable*: the small model visibly fails the agent task the larger ones pass.

## 📖 License & author

Licensed under **CC BY-NC-SA 4.0**. © 2026 **Marc Alier i Forment** (UPC) ·
<https://wasabi.essi.upc.edu/ludo> · <https://lamb-project.org>. BSC Agents Course.
