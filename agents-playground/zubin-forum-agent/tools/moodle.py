"""Access Moodle through the local moodle-cli project.

Tools are kept separate from agents so subprocess details live in one place.
The agent receives Python objects and remains independent of CLI rendering.
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from config import moodle_subprocess_env


# The Moodle Tool owns the configuration needed to run moodle-cli.
MOODLE_CLI_PATH = r"C:\Users\USER\Documents\GitHub\moodle-cli"
PROFILE = "artemis"


@dataclass
class ForumPost:
    """One forum post returned by Moodle."""

    id: int
    author: str
    subject: str
    message: str
    timestamp: str


def run_moodle(args: list[str]) -> str:
    """Run moodle-cli in JSON mode and return its output."""

    env = moodle_subprocess_env()

    try:
        # Run from the moodle-cli project so uv uses that environment.
        result = subprocess.run(
            ["uv", "run", "moodle", "-p", PROFILE, "--json", *args],
            cwd=MOODLE_CLI_PATH,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as error:
        # Captured output would otherwise be hidden by the exception.
        print("moodle-cli command failed.", file=sys.stderr)
        if error.stderr:
            print("stderr:", file=sys.stderr)
            print(error.stderr, file=sys.stderr)
        if error.stdout:
            print("stdout:")
            print(error.stdout)
        raise

    return result.stdout


def _author_name(author: dict[str, Any]) -> str:
    """Choose the same author label previously shown in the CLI table."""

    return str(
        author.get("fullname")
        or author.get("name")
        or author.get("id")
        or "?"
    )


def _plain_message(message: str) -> str:
    """Convert Moodle HTML to the plain text used by the old table output."""

    without_tags = re.sub(r"<[^>]+>", " ", message or "")
    return re.sub(r"\s+", " ", without_tags).strip()


def _format_timestamp(timestamp: int) -> str:
    """Format a Moodle timestamp like the old table output."""

    if not timestamp:
        return "-"
    try:
        return datetime.fromtimestamp(int(timestamp)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError, OverflowError):
        return str(timestamp)


def read_discussion(discussion_id: int) -> list[ForumPost]:
    """Read one discussion and convert its JSON posts to Python objects."""

    items = json.loads(
        run_moodle(["forum", "posts", str(discussion_id)])
    )
    return [
        ForumPost(
            id=int(item["id"]),
            author=_author_name(item.get("author") or {}),
            subject=str(item.get("subject") or ""),
            message=_plain_message(str(item.get("message") or "")),
            timestamp=_format_timestamp(int(item.get("timecreated") or 0)),
        )
        for item in items
    ]


def read_forum(forum_id: int) -> list[dict[str, Any]]:
    """Read a forum and return its decoded discussion records."""

    return json.loads(
        run_moodle(["forum", "discussions", str(forum_id)])
    )


def reply_to_post(post_id: int, subject: str, message: str) -> str:
    """Post a reply through moodle-cli after the caller obtains approval."""

    # This tool performs the external write, but it does not decide whether
    # posting is allowed. The agent's human-approval workflow owns that choice.
    return run_moodle(
        [
            "forum",
            "reply",
            "--post-id",
            str(post_id),
            "--subject",
            subject,
            "--message",
            message,
        ]
    )
