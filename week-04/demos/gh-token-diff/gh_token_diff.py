# © 2026 Marc Alier i Forment (Universitat Politècnica de Catalunya) · https://wasabi.essi.upc.edu/ludo · https://lamb-project.org
# BSC Agents Course — Transformers, LLMs, RAG and Agents: From Theory to Production
# Licensed under Creative Commons BY-NC-SA 4.0 — reuse must credit the author, no commercial use, derivatives under the same license.

# =============================================================================================================== #
# Universitat Politècnica de Catalunya (UPC)                                                                      #
# =============================================================================================================== #

"""
🧾 CLI vs MCP — count the tokens.

You built an MCP server and it worked. Now the question you could not ask before:
was that the cheapest way to give the model that capability? This script makes the
bill visible for one GitHub task, two ways.

  CLI path  — the model already knows `gh` from its training. It needs no schema.
              It emits one command; you run it; the result comes back. Cost = the
              command + the output. The catalogue overhead is ZERO.

  MCP path  — before any work happens, the GitHub MCP server injects its tool
              CATALOGUE into the context: dozens of JSON schemas, at the head of
              every session. The model pays for that registry whether or not it
              uses a single tool.

We tokenise a real `gh` interaction here, and set it against the published
catalogue figures. The number is the point, not the plumbing.

Published receipts (cited in the chapter):
  - ~35× more tokens via MCP than CLI on matched tasks, reliability 100%->72%   [MindStudio 2026]
  - one GitHub language-check: ~1,365 tokens via gh  vs  ~44,026 via the MCP server [Vensas 2026]
  - a 93-tool GitHub MCP server: ~55,000 tokens of schema at session start vs ~200 via gh [Reinhard 2026]
"""
import json
import subprocess

import tiktoken

enc = tiktoken.get_encoding("cl100k_base")
def toks(s):
    return len(enc.encode(s))


# --- THE TASK: "what are the open issue titles on a repo?" ---

# CLI path: the one line the model emits. It already knows gh; no schema is loaded.
gh_command = "gh issue list --repo cli/cli --state open --limit 5 --json number,title"

# Run it for real if we can; otherwise use a representative captured result.
try:
    out = subprocess.run(gh_command, shell=True, capture_output=True, text=True, timeout=20)
    gh_output = out.stdout.strip() or out.stderr.strip()
    if not gh_output or out.returncode != 0:
        raise RuntimeError
    source = "live `gh` call"
except Exception:
    gh_output = json.dumps([
        {"number": 11823, "title": "Allow `gh pr create` to target a fork"},
        {"number": 11790, "title": "`gh repo clone` should respect submodule config"},
        {"number": 11777, "title": "Add `--json` support to `gh release view`"},
    ], indent=2)
    source = "representative captured output (no gh auth/network)"

cli_tokens = toks(gh_command) + toks(gh_output)

# MCP path: ONE real-shaped tool schema, of the dozens the server injects up front.
one_mcp_schema = {
    "name": "list_issues",
    "description": "List issues in a GitHub repository with optional filtering by state, "
                   "labels, assignee, milestone, and sort order. Returns issue number, "
                   "title, body, state, author, labels, assignees, and timestamps.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "owner": {"type": "string", "description": "Repository owner (user or org)."},
            "repo": {"type": "string", "description": "Repository name."},
            "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Issue state filter."},
            "labels": {"type": "array", "items": {"type": "string"}, "description": "Filter by label names."},
            "assignee": {"type": "string", "description": "Filter by assignee login."},
            "milestone": {"type": "string", "description": "Filter by milestone."},
            "sort": {"type": "string", "enum": ["created", "updated", "comments"]},
            "direction": {"type": "string", "enum": ["asc", "desc"]},
            "per_page": {"type": "integer", "description": "Results per page (max 100)."},
            "page": {"type": "integer", "description": "Page number of the results."},
        },
        "required": ["owner", "repo"],
    },
}
one_schema_tokens = toks(json.dumps(one_mcp_schema))
GITHUB_MCP_TOOL_COUNT = 93                       # [Reinhard 2026]
mcp_catalogue_tokens = one_schema_tokens * GITHUB_MCP_TOOL_COUNT

print(f"TASK: list open issue titles on a repo\n")
print(f"CLI path  ({source}):")
print(f"  command     : {gh_command}")
print(f"  command toks: {toks(gh_command)}")
print(f"  output toks : {toks(gh_output)}")
print(f"  ── CLI total: {cli_tokens} tokens   (catalogue overhead: 0)\n")

print(f"MCP path:")
print(f"  one tool schema             : {one_schema_tokens} tokens")
print(f"  catalogue at session start  : {one_schema_tokens} x {GITHUB_MCP_TOOL_COUNT} tools "
      f"≈ {mcp_catalogue_tokens:,} tokens  (BEFORE any work)\n")

print(f"  ratio (this measurement)    : ~{mcp_catalogue_tokens // max(cli_tokens,1)}x just for the catalogue")
print(f"  published, matched tasks    : ~35x more tokens via MCP [MindStudio 2026]")
print(f"  published, GitHub MCP       : ~55,000 vs ~200 tokens at session start [Reinhard 2026]")
print(f"\nMCP is not wrong. It is expensive by default — and the default is what bites a cohort.")
