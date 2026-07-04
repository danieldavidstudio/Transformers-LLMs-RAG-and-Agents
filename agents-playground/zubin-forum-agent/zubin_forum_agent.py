import subprocess


# Location of the local moodle-cli project.
MOODLE_CLI_PATH = r"C:\Users\USER\Documents\GitHub\moodle-cli"

# Moodle profile and forum identifiers used by Zubin.
PROFILE = "artemis"
FORUM_ID = 416
GRUMPY_DISCUSSION_ID = 1446
GRUMPY_ORIGINAL_POST_ID = 2662


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
    """Introduce Zubin and display Grumpy's discussion."""

    print("=================================")
    print("ZUBIN")
    print("The Agentic Orchestra")
    print("=================================")
    print()
    print("Reading Grumpy's discussion...")
    print()

    # Keep the moodle-cli output unchanged: no parsing and no JSON.
    print(read_grumpy_thread())


if __name__ == "__main__":
    main()
