"""Zubin's reasoning and recommendation behavior.

This module contains decisions, not Moodle access or posting code. Keeping
reasoning separate makes it possible to improve how Zubin thinks without
changing the tools that read external systems.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Recommendation:
    """A complete, non-binding recommendation from Zubin."""

    should_reply: bool
    confidence: float
    reason: str
    draft_subject: str
    draft_message: str


class Zubin:
    """Review new posts and prepare a recommendation without taking action."""

    def __init__(self, own_author: str) -> None:
        # Zubin must not recommend replying to posts written by ourselves.
        self.own_author = own_author.casefold()

    def recommend(
        self,
        new_posts: list[Any],
        reply_count: int,
    ) -> Recommendation:
        """Read new posts, explain a decision, and optionally draft a reply."""

        # A future milestone can replace these simple rules with an LLM.
        # The Recommendation interface can stay the same when that happens.

        # There is nothing to answer when memory found no new posts.
        if not new_posts:
            return Recommendation(
                should_reply=False,
                confidence=1.0,
                reason="There are no new forum posts to reply to.",
                draft_subject="",
                draft_message="",
            )

        # Avoid adding to a discussion that already has many replies.
        if reply_count >= 20:
            return Recommendation(
                should_reply=False,
                confidence=0.9,
                reason="The discussion already has 20 or more replies.",
                draft_subject="",
                draft_message="",
            )

        # Ignore our own posts and keep only possible conversation partners.
        posts_from_others = [
            post
            for post in new_posts
            if post.author.casefold() != self.own_author
        ]

        if not posts_from_others:
            return Recommendation(
                should_reply=False,
                confidence=0.95,
                reason="The new posts were written by ourselves.",
                draft_subject="",
                draft_message="",
            )

        # For now, draft a friendly response to the most recent eligible post.
        target_post = posts_from_others[-1]
        subject = target_post.subject
        if not subject.casefold().startswith("re:"):
            subject = f"Re: {subject}"

        return Recommendation(
            should_reply=True,
            confidence=0.75,
            reason=(
                f"There is a new post from {target_post.author}, and the "
                "discussion has fewer than 20 replies."
            ),
            draft_subject=subject,
            draft_message=(
                f"Thanks for sharing this, {target_post.author}. "
                "Your post adds something useful to the discussion."
            ),
        )

