"""Zubin's reasoning and recommendation behavior.

Zubin is the conductor. He delegates specialist analysis instead of containing
forum decision rules himself.
"""

from typing import Any

from orchestra.musician import Musician, Recommendation
from orchestra.turing import Turing


ZUBIN_PERSONA = """
Zubin is the conductor of The Agentic Orchestra. He coordinates specialists:
Mies for architecture, Rice for structural engineering, Turing for AI and
knowledge systems, and Rams for UX/UI. His voice is calm, thoughtful, concise,
slightly poetic, and never generic.
""".strip()

ORCHESTRA_CONCEPT = """
The Agentic Orchestra separates coordination from specialist reasoning.
Zubin conducts; specialists contribute their disciplines. The system may read
and draft autonomously, but a human must explicitly approve every external
forum post.
""".strip()


class Zubin(Musician):
    """Delegate forum analysis without taking action."""

    def __init__(self, own_author: str) -> None:
        super().__init__(
            name="Zubin",
            role="Conductor",
        )

        # Turing is the Orchestra's first specialist.
        self.turing = Turing(own_author=own_author)

    def recommend(
        self,
        new_posts: list[Any],
        reply_count: int,
        thread_posts: list[Any] | None = None,
    ) -> Recommendation:
        """Delegate to Turing and return his recommendation unchanged."""

        print("----------------------------------")
        print("Zubin delegated to Turing")
        print("----------------------------------")

        # Zubin coordinates the work but does not duplicate Turing's reasoning.
        return self.turing.recommend(
            new_posts=new_posts,
            reply_count=reply_count,
            thread_posts=thread_posts if thread_posts is not None else new_posts,
            persona=ZUBIN_PERSONA,
            orchestra_concept=ORCHESTRA_CONCEPT,
        )
