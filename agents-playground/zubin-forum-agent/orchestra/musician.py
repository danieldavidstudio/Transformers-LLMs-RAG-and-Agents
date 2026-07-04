"""Shared building blocks for every member of The Agentic Orchestra."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Recommendation:
    """A musician's non-binding recommendation."""

    should_reply: bool
    confidence: float
    reason: str
    draft_subject: str
    draft_message: str


class Musician:
    """Base class that gives every musician a name, role, and interface."""

    def __init__(self, name: str, role: str) -> None:
        self.name = name
        self.role = role

    def recommend(self, *args: Any, **kwargs: Any) -> Recommendation:
        """Return a recommendation when implemented by a concrete musician."""

        raise NotImplementedError(
            f"{self.name} does not have recommendation logic yet."
        )

