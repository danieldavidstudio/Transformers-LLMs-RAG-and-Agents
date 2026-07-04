# The Agentic Orchestra — Zubin Forum Agent

Zubin is a small local agent for the Moodle Agents playground forum. He conducts
specialist musicians, remembers which posts have been seen, prepares a reply,
and waits for a human decision before writing anything to Moodle.

## Concept

The Agentic Orchestra separates coordination, specialist reasoning, external
tools, memory, and human authority. Zubin is the conductor. Turing is the first
specialist and currently uses simple, transparent heuristics to decide whether
a forum reply is appropriate.

## Safety model

- **Autonomous read:** Zubin may read the configured Moodle discussion, parse
  its posts, and update local memory.
- **Human-approved write:** Zubin displays the complete recommendation and
  draft. A reply is posted only when the user explicitly enters `y`.
- Any other response, including pressing Enter, cancels the action.

## Architecture

```text
Moodle forum
    |
    v
Moodle Tool (read_discussion)
    |
    v
Zubin Agent (parse + remember)
    |
    v
Zubin Conductor ----delegates----> Turing Specialist
    |                                    |
    +<----------- Recommendation --------+
    |
    v
Human Approval [y/N]
    |
    +-- no --> No external action
    |
    +-- yes -> Moodle Tool (reply_to_post) -> Moodle forum
```

Project structure:

```text
zubin-forum-agent/
├── approval.py                 # Human approval boundary
├── orchestra/
│   ├── musician.py            # Shared musician and recommendation types
│   ├── zubin.py               # Conductor and delegation
│   ├── turing.py              # Forum-reply heuristic
│   ├── mies.py                # Future musician
│   ├── rice.py                # Future musician
│   └── rams.py                # Future musician
├── tools/
│   └── moodle.py              # All moodle-cli subprocess access
├── zubin_forum_agent.py       # Application entry point and local memory
└── zubin_state.example.json   # Example memory file
```

## Setup

1. Install Python 3.10 or newer and
   [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Place `moodle-cli` at:

   ```text
   C:\Users\USER\Documents\GitHub\moodle-cli
   ```

3. Set up `moodle-cli` and configure an authenticated profile named `artemis`.
4. Open a terminal in this project directory.

Zubin creates `zubin_state.json` automatically. To prepare it manually, copy
`zubin_state.example.json` to `zubin_state.json`. The state file is ignored by
Git because it is local runtime memory.

## How to run

```powershell
python zubin_forum_agent.py
```

Review the recommendation and draft carefully. Enter `y` only when the reply
should be posted. Press Enter or type anything else to cancel.

On the first run, existing posts initialize memory and are not treated as new.

## Current workflow

```text
Observe → Remember → Moodle Tool → Delegate to Turing
        → Recommend → Human Approval → Approved Moodle Reply
```

## Version 0.1

Version 0.1 can read the configured forum discussion, detect unseen posts,
delegate reply reasoning to Turing, ask a human for approval, and post a reply
only after explicit approval.

## Roadmap

- Watch mode
- More musicians: Mies, Rice, Rams
- LLM-based reasoning
- More tools: GitHub, Calendar, Gmail

