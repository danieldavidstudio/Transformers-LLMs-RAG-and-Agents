"""Structured discussion analysis produced before reply writing."""

from dataclasses import dataclass


@dataclass
class DiscussionAnalysis:
    """Turing's analysis of whether and how to join a discussion."""

    summary: str
    central_question: str
    should_participate: bool
    confidence: float
    why: str
    best_speaker: str
    contributors: list[str]
    key_points: list[str]
    desired_effect: str
