import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from approval import request_human_approval
from orchestra.zubin import Zubin
from tools.moodle import (
    PROFILE,
    read_discussion,
    reply_to_post,
)


# Forum identifiers used by Zubin.
FORUM_ID = 416
GRUMPY_DISCUSSION_ID = 1446
GRUMPY_ORIGINAL_POST_ID = 2662

# Keep Zubin's local memory beside this Python file.
STATE_PATH = Path(__file__).with_name("zubin_state.json")


@dataclass
class ForumPost:
    """One forum post read from the moodle-cli table."""

    id: int
    author: str
    subject: str
    message: str
    timestamp: str


def load_state() -> dict:
    """Load Zubin's memory, creating an empty state file when needed."""

    # A brand-new project starts with no remembered posts.
    if not STATE_PATH.exists():
        state = {
            "seen_post_ids": [],
            "last_checked": None,
        }
        save_state(state)
        return state

    # Read the existing JSON state into a normal Python dictionary.
    with STATE_PATH.open("r", encoding="utf-8") as state_file:
        return json.load(state_file)


def save_state(state: dict) -> None:
    """Save Zubin's memory as readable JSON."""

    # Indentation keeps the small state file friendly to human readers.
    with STATE_PATH.open("w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=4)
        state_file.write("\n")


def get_new_posts(
    posts: list[ForumPost],
    seen_post_ids: list[int],
) -> list[ForumPost]:
    """Return only posts whose IDs are not already in Zubin's memory."""

    # A set makes each ID lookup simple and fast.
    seen_ids = set(seen_post_ids)
    return [post for post in posts if post.id not in seen_ids]


def parse_forum_posts(raw_output: str) -> list[ForumPost]:
    """Turn the current moodle-cli posts table into ForumPost objects."""

    # Each item starts as five pieces of text matching the table columns.
    rows: list[list[str]] = []
    current_row: list[str] | None = None

    # Read the table one displayed line at a time.
    for line in raw_output.splitlines():
        # Rich uses "|" on this Windows console and "│" on some terminals.
        stripped_line = line.strip()
        if stripped_line.startswith("|") and stripped_line.endswith("|"):
            border = "|"
        elif stripped_line.startswith("│") and stripped_line.endswith("│"):
            border = "│"
        else:
            continue

        # Splitting on the box character gives the five displayed cells.
        cells = [cell.strip() for cell in stripped_line.split(border)[1:-1]]
        if len(cells) != 5:
            continue

        # Ignore the table's heading row.
        if cells == ["ID", "When", "Author", "Subject", "Message"]:
            continue

        # A numeric first cell marks the beginning of a new forum post.
        if cells[0].isdigit():
            current_row = cells
            rows.append(current_row)
            continue

        # Rich wraps long table values onto extra displayed lines.
        # Join those pieces back onto the post currently being built.
        if current_row is not None:
            for index, cell in enumerate(cells):
                if cell:
                    current_row[index] = f"{current_row[index]} {cell}".strip()

    # Convert the collected table rows into clear Python objects.
    return [
        ForumPost(
            id=int(row[0]),
            timestamp=row[1],
            author=row[2],
            subject=row[3],
            message=row[4],
        )
        for row in rows
    ]


def main():
    """Introduce Zubin and summarize Grumpy's discussion."""

    print("=================================")
    print("ZUBIN")
    print("The Agentic Orchestra")
    print("=================================")
    print()
    print("Reading Grumpy's discussion...")
    print()

    # Ask the Moodle Tool to read the thread. The agent never runs a
    # subprocess itself, which keeps external-system access isolated.
    raw_output = read_discussion(GRUMPY_DISCUSSION_ID)
    posts = parse_forum_posts(raw_output)

    # Keep the existing summary of all posts in the discussion.
    print("--------------------------------")
    print(f"Found {len(posts)} forum posts")
    print("--------------------------------")

    # Do not show the message body yet.
    for post in posts:
        print()
        print(f"ID: {post.id}")
        print(f"Author: {post.author}")
        print(f"Subject: {post.subject}")

    # Load the IDs remembered during earlier runs.
    state = load_state()
    seen_post_ids = state["seen_post_ids"]

    if not seen_post_ids:
        # On the first run, remember the current thread as the baseline.
        # Existing posts are deliberately not treated as new.
        state["seen_post_ids"] = [post.id for post in posts]
        new_posts = []
        print()
        print("First run detected.")
        print("Memory initialized.")
    else:
        # On later runs, report posts that are absent from memory.
        new_posts = get_new_posts(posts, seen_post_ids)
        print()
        print("--------------------------------")
        print(f"New posts detected: {len(new_posts)}")
        print("--------------------------------")

        # Preserve old IDs and add every ID found during this read.
        current_post_ids = [post.id for post in posts]
        state["seen_post_ids"] = list(
            dict.fromkeys(seen_post_ids + current_post_ids)
        )

    # Record when the read finished and persist the updated memory.
    state["last_checked"] = datetime.now(timezone.utc).isoformat()
    save_state(state)

    # Zubin delegates analysis of new posts to Turing.
    conductor = Zubin(own_author=PROFILE)
    recommendation = conductor.recommend(
        new_posts=new_posts,
        reply_count=max(len(posts) - 1, 0),
    )

    # A human must review the recommendation before the write tool is called.
    print()
    approval_request = request_human_approval(recommendation)

    if approval_request.approved:
        print("Action approved.")

        # Approval is the only path to the Moodle write tool.
        print("Posting reply...")
        reply_to_post(
            post_id=GRUMPY_ORIGINAL_POST_ID,
            subject=recommendation.draft_subject,
            message=recommendation.draft_message,
        )
        print("Reply successfully posted.")
    else:
        print("Action cancelled by user.")
        print("Reply not posted.")

    print()
    print("Ready for reasoning.")


if __name__ == "__main__":
    main()
