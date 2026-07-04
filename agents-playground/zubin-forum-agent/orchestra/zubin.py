"""Zubin's reasoning and recommendation behavior.

Zubin is the conductor. He delegates specialist analysis instead of containing
forum decision rules himself.
"""

from typing import Any

from orchestra.musician import Musician, Recommendation
from orchestra.turing import Turing


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
    ) -> Recommendation:
        """Delegate to Turing and return his recommendation unchanged."""

        print("----------------------------------")
        print("Zubin delegated to Turing")
        print("----------------------------------")

        # Zubin coordinates the work but does not duplicate Turing's reasoning.
        return self.turing.recommend(
            new_posts=new_posts,
            reply_count=reply_count,
        )
