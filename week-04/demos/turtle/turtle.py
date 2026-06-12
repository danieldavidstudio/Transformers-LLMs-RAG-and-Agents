# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

# =============================================================================================================== #
# Universitat Politècnica de Catalunya (UPC)                                                                      #
# =============================================================================================================== #

"""
🐢 Turtle — a custom agent shipped as a CLI.

This is the defining move of the methodology, made concrete. You took the small
agent loop you built by hand, you HARVESTED what a prototype taught you (the tools,
a security scaffold), you FOLDED it into your own ~30-line loop plus two additions —
a session store and an explicit security check before each tool runs — and you SHIP
it as a command-line tool. Not a chat window in the corner of a web page. Not a
hidden endpoint. A CLI:

    turtle "list the files here and tell me which is largest"   -> answer + a session id
    turtle <session-id> "now show me the first lines of it"     -> continues that session
    turtle --list-sessions
    turtle --replay <session-id>
    turtle --help                                               -> works, for a human AND the agent

Why a CLI and not a chat box? Because the next agent has to be able to drive it.
"A chat-window-in-a-corner is not testable by another agent; a CLI is." The shape
of the loop is invariant; yours will look slightly different, but this is the shape.
"""
import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from openai import OpenAI

# --- configuration (point at any OpenAI-compatible endpoint; Ollama by default) ---
client = OpenAI(
    base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.environ.get("OPENAI_API_KEY", "ollama"),
)
MODEL = os.environ.get("MODEL", "qwen3:1.7b")
SESSIONS = Path(os.environ.get("TURTLE_SESSIONS", Path(__file__).parent / "sessions"))

SYSTEM_PROMPT = (
    "You are Turtle, a small command-line assistant. You can inspect the current "
    "directory with the run_shell tool when, and only when, the task needs it. "
    "Prefer one command at a time. Answer the user plainly once you have what you need."
)

# --- the one tool this Turtle exposes: a deliberately narrow shell ---
# A real Turtle harvests its tools from the prototype. We expose ONE here to keep
# the loop readable — and to make the security check visible.
TOOLS = [{
    "type": "function",
    "function": {
        "name": "run_shell",
        "description": "Run one read-only shell command and return its output.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "e.g. 'ls -la' or 'wc -l file.txt'"}},
            "required": ["command"],
        },
    },
}]

# --- the explicit security check: the two lines that are NOT in the prototype ---
# Critical constraints live in host code, deterministic — never in the prompt.
ALLOW = {"ls", "cat", "head", "tail", "wc", "date", "pwd", "echo", "file"}
FORBIDDEN = set(";|&><`$()")  # block shell metacharacters that escape the allow-list


def security_check(command):
    """Return (ok, reason). Runs BEFORE every tool execution. This is the gate."""
    if any(c in FORBIDDEN for c in command):
        return False, "shell metacharacters are not allowed"
    verb = command.strip().split()[0] if command.strip() else ""
    if verb not in ALLOW:
        return False, f"'{verb}' is not on the allow-list {sorted(ALLOW)}"
    return True, "on the allow-list"


def run_shell(command):
    out = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
    return (out.stdout or out.stderr).strip()[:2000]


# --- session store: the other addition over the hand-built loop ---
def load(session_id):
    f = SESSIONS / f"{session_id}.json"
    return json.loads(f.read_text()) if f.exists() else None


def save(session_id, messages):
    SESSIONS.mkdir(parents=True, exist_ok=True)
    (SESSIONS / f"{session_id}.json").write_text(json.dumps(messages, indent=2))


# --- the loop (the invariant ~30 lines) ---
def agent_turn(messages):
    """Run the model, satisfy any tool calls (gated by the security check), repeat."""
    while True:
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        msg = resp.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content or ""

        for call in msg.tool_calls:
            command = json.loads(call.function.arguments).get("command", "")
            ok, reason = security_check(command)
            print(f"  🔒 security check: run_shell({command!r}) -> {'ALLOWED' if ok else 'DENIED'} ({reason})")
            result = run_shell(command) if ok else f"BLOCKED by security check: {reason}"
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})


def converse(session_id, user_text):
    history = load(session_id)
    if history is None:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
    history.append({"role": "user", "content": user_text})
    answer = agent_turn(history)
    save(session_id, history)
    return answer


# --- the CLI surface (this is what makes it a Turtle) ---
def main():
    p = argparse.ArgumentParser(
        prog="turtle",
        description="A custom agent you can drive from the command line — by a human or by another agent.",
        epilog='examples:\n  turtle "what is the biggest file here?"\n  turtle 1a2b3c4d "show me its first 5 lines"\n'
               "  turtle --list-sessions\n  turtle --replay 1a2b3c4d",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("args", nargs="*", help='[session-id] "your message"')
    p.add_argument("--list-sessions", action="store_true", help="list saved session ids")
    p.add_argument("--replay", metavar="ID", help="print a saved session's transcript")
    a = p.parse_args()

    if a.list_sessions:
        ids = sorted(f.stem for f in SESSIONS.glob("*.json")) if SESSIONS.exists() else []
        print("\n".join(ids) if ids else "(no sessions yet)")
        return
    if a.replay:
        history = load(a.replay)
        if not history:
            sys.exit(f"no session {a.replay!r}")
        for m in history:
            if m["role"] in ("user", "assistant") and m.get("content"):
                print(f"{m['role']:>9}: {m['content']}")
        return

    # turtle "msg"  (new)  |  turtle <id> "msg"  (continue)
    if len(a.args) == 1:
        session_id, user_text = uuid.uuid4().hex[:8], a.args[0]
        print(f"🐢 new session {session_id}")
    elif len(a.args) == 2:
        session_id, user_text = a.args
    else:
        p.print_help()
        return

    answer = converse(session_id, user_text)
    print(f"\n{answer}\n\n[session {session_id}]  continue with:  turtle {session_id} \"...\"")


if __name__ == "__main__":
    main()
