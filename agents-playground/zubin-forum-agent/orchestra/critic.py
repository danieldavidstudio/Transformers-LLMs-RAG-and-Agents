"""Structured review of Zubin's first draft."""

import json
from dataclasses import asdict, dataclass
from typing import Any

from orchestra.analysis import DiscussionAnalysis
from orchestra.musician import Musician
from orchestra.prompt_loader import load_persona, load_prompt, persona_role
from providers import generate_chat


@dataclass
class CriticReport:
    """The critic's non-writing assessment of a draft."""

    approved: bool
    score: float
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]


class Critic(Musician):
    """Review a draft without rewriting it."""

    def __init__(self) -> None:
        self.persona = load_persona("critic")
        self.orchestra_charter = load_prompt("orchestra")
        super().__init__(name="Critic", role=persona_role(self.persona))

    @staticmethod
    def _post_data(post: Any) -> dict[str, Any]:
        """Convert a forum post into JSON-safe review context."""

        return {
            "id": post.id,
            "author": post.author,
            "subject": post.subject,
            "message": post.message,
            "timestamp": post.timestamp,
        }

    @staticmethod
    def _parse_report(content: str) -> CriticReport:
        """Validate the critic's JSON response."""

        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("critic response must be a JSON object")

        required = {
            "approved",
            "score",
            "strengths",
            "weaknesses",
            "suggestions",
        }
        if required.difference(data):
            raise ValueError("critic response is missing required fields")
        if not isinstance(data["approved"], bool):
            raise ValueError("approved must be a boolean")
        if (
            isinstance(data["score"], bool)
            or not isinstance(data["score"], (int, float))
            or not 0 <= data["score"] <= 10
        ):
            raise ValueError("score must be a number from 0 to 10")
        for field in ("strengths", "weaknesses", "suggestions"):
            if (
                not isinstance(data[field], list)
                or not all(isinstance(item, str) for item in data[field])
            ):
                raise ValueError(f"{field} must be a list of strings")

        return CriticReport(
            approved=data["approved"],
            score=float(data["score"]),
            strengths=data["strengths"],
            weaknesses=data["weaknesses"],
            suggestions=data["suggestions"],
        )

    def recommend(
        self,
        draft_message: str,
        analysis: DiscussionAnalysis,
        thread_posts: list[Any],
    ) -> CriticReport:
        """Review one draft and return structured feedback."""

        system_prompt = f"""
{self.orchestra_charter}

---

{self.persona}

---

You are Critic.

Review the draft according to:
- Does it answer the actual thread?
- Does it add something original?
- Does it sound like Zubin?
- Is it generic?
- Is it too poetic?
- Is it likely that a human would approve it?

Your job is NOT to rewrite. Return JSON only:
{{
  "approved": boolean,
  "score": number from 0 to 10,
  "strengths": array of strings,
  "weaknesses": array of strings,
  "suggestions": array of strings
}}
""".strip()
        user_prompt = json.dumps(
            {
                "discussion_analysis": asdict(analysis),
                "complete_thread": [
                    self._post_data(post) for post in thread_posts
                ],
                "draft_message": draft_message,
            },
            ensure_ascii=False,
        )

        try:
            content = generate_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            return self._parse_report(content)
        except Exception:
            return CriticReport(
                approved=False,
                score=0.0,
                strengths=[],
                weaknesses=["The critic could not produce a valid review."],
                suggestions=[
                    "Recheck the draft against the thread and analysis."
                ],
            )
