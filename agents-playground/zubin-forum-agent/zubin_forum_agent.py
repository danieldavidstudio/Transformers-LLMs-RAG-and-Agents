import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from approval import request_human_approval
from evaluation import save_evaluation
from orchestra.zubin import Zubin
from tools.moodle import (
    ForumPost,
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for Zubin."""

    parser = argparse.ArgumentParser(
        description="Review Grumpy's Moodle discussion with Zubin.",
    )
    parser.add_argument(
        "--draft-now",
        action="store_true",
        help="draft a reply to Grumpy's original post without requiring it "
        "to be new",
    )
    return parser.parse_args(argv)


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


def main(argv: list[str] | None = None):
    """Introduce Zubin and summarize Grumpy's discussion."""

    args = parse_args(argv)

    print("=================================")
    print("ZUBIN")
    print("The Agentic Orchestra")
    print("=================================")
    print()
    print("Reading Grumpy's discussion...")
    print()

    # The Moodle Tool returns structured posts, not rendered table text.
    posts = read_discussion(GRUMPY_DISCUSSION_ID)

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

    recommendation_posts = new_posts
    if args.draft_now:
        # Explicit draft mode treats Grumpy's original post as eligible even
        # when memory has already recorded it. All other recommendation and
        # approval rules remain in force.
        recommendation_posts = [
            post for post in posts if post.id == GRUMPY_ORIGINAL_POST_ID
        ]

    # Zubin delegates analysis of eligible posts to Turing.
    conductor = Zubin(own_author=PROFILE)
    recommendation = conductor.recommend(
        new_posts=recommendation_posts,
        reply_count=max(len(posts) - 1, 0),
        thread_posts=posts,
    )

    # A human must review the recommendation before the write tool is called.
    print()
    approval_request = request_human_approval(recommendation)

    posted = False
    try:
        if recommendation.should_reply and approval_request.approved:
            print("Action approved.")

            # Approval is the only path to the Moodle write tool.
            print("Posting reply...")
            reply_to_post(
                post_id=GRUMPY_ORIGINAL_POST_ID,
                subject=recommendation.draft_subject,
                message=recommendation.draft_message,
            )
            posted = True
            print("Reply successfully posted.")
        elif recommendation.should_reply:
            print("Action cancelled by user.")
            print("Reply not posted.")
        else:
            print("No reply was recommended.")
            print("Reply not posted.")
    finally:
        save_evaluation(
            discussion_posts=posts,
            analysis=conductor.last_analysis,
            first_draft=conductor.last_first_draft,
            critic_report=conductor.last_critic_report,
            recommendation=recommendation,
            approved=bool(approval_request.approved),
            posted=posted,
        )

    print()
    print("Ready for reasoning.")


if __name__ == "__main__":
    main()
