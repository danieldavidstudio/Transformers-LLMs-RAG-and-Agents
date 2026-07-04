"""Read-only access to Moodle through the local moodle-cli project.

Tools are kept separate from agents so subprocess details live in one place.
The agent can focus on its own parsing, memory, and presentation behavior.
"""

import subprocess


# The Moodle Tool owns the configuration needed to run moodle-cli.
MOODLE_CLI_PATH = r"C:\Users\USER\Documents\GitHub\moodle-cli"
PROFILE = "artemis"


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


def read_discussion(discussion_id: int) -> str:
    """Read every post in one Moodle forum discussion."""

    return run_moodle(
        [
            "--profile",
            PROFILE,
            "forum",
            "posts",
            str(discussion_id),
        ]
    )


def read_forum(forum_id: int) -> str:
    """Read the discussions available in one Moodle forum."""

    return run_moodle(
        [
            "--profile",
            PROFILE,
            "forum",
            "discussions",
            str(forum_id),
        ]
    )


def reply_to_post(post_id: int, subject: str, message: str) -> str:
    """Post a reply through moodle-cli after the caller obtains approval."""

    # This tool performs the external write, but it does not decide whether
    # posting is allowed. The agent's human-approval workflow owns that choice.
    return run_moodle(
        [
            "-p",
            PROFILE,
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


def read_grumpy_thread() -> str:
    """Read Grumpy's discussion using its known discussion ID."""

    return read_discussion(1446)
