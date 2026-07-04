import subprocess
from dataclasses import dataclass


# Location of the local moodle-cli project.
MOODLE_CLI_PATH = r"C:\Users\USER\Documents\GitHub\moodle-cli"

# Moodle profile and forum identifiers used by Zubin.
PROFILE = "artemis"
FORUM_ID = 416
GRUMPY_DISCUSSION_ID = 1446
GRUMPY_ORIGINAL_POST_ID = 2662


@dataclass
class ForumPost:
    """One forum post read from the moodle-cli table."""

    id: int
    author: str
    subject: str
    message: str
    timestamp: str


def run_moodle(args: list[str]) -> str:
    """Run a moodle-cli command and return its text output."""

    # Run the command from the moodle-cli project so uv uses that project.
    result = subprocess.run(
        ["uv", "run", "moodle", *args],
        cwd=MOODLE_CLI_PATH,
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout


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


def read_grumpy_thread() -> str:
    """Read every post in Grumpy's configured discussion."""

    # The profile option belongs before the forum command.
    return run_moodle(
        [
            "--profile",
            PROFILE,
            "forum",
            "posts",
            str(GRUMPY_DISCUSSION_ID),
        ]
    )


def main():
    """Introduce Zubin and summarize Grumpy's discussion."""

    print("=================================")
    print("ZUBIN")
    print("The Agentic Orchestra")
    print("=================================")
    print()
    print("Reading Grumpy's discussion...")
    print()

    # Read the table text, then turn each row into a ForumPost.
    raw_output = read_grumpy_thread()
    posts = parse_forum_posts(raw_output)

    # Show only the small summary requested for this milestone.
    print("--------------------------------")
    print(f"Found {len(posts)} forum posts")
    print("--------------------------------")

    # Do not show the message body yet.
    for post in posts:
        print()
        print(f"ID: {post.id}")
        print(f"Author: {post.author}")
        print(f"Subject: {post.subject}")

    print()
    print("Ready for reasoning.")


if __name__ == "__main__":
    main()
