"""Turing's LLM-backed forum-analysis behavior."""

import json
from typing import Any

from orchestra.analysis import DiscussionAnalysis
from orchestra.musician import Musician
from orchestra.prompt_loader import load_persona, load_prompt, persona_role
from providers import generate_chat


class Turing(Musician):
    """Analyze forum posts and ask an LLM whether Zubin should reply."""

    def __init__(self, own_author: str) -> None:
        self.persona = load_persona("turing")
        self.zubin_persona = load_persona("zubin")
        self.orchestra_charter = load_prompt("orchestra")
        super().__init__(name="Turing", role=persona_role(self.persona))
        self.own_author = own_author.casefold()

    @staticmethod
    def _safe_analysis(reason: str) -> DiscussionAnalysis:
        """Return an analysis that recommends silence."""

        return DiscussionAnalysis(
            summary="",
            central_question="",
            should_participate=False,
            confidence=0.0,
            why=reason,
            best_speaker="",
            contributors=[],
            key_points=[],
            desired_effect="",
        )

    @staticmethod
    def _post_data(post: Any) -> dict[str, Any]:
        """Convert a forum post into JSON-safe prompt data."""

        return {
            "id": post.id,
            "author": post.author,
            "subject": post.subject,
            "message": post.message,
            "timestamp": post.timestamp,
        }

    def _parse_analysis(self, content: str) -> DiscussionAnalysis:
        """Validate model JSON and convert it to a DiscussionAnalysis."""

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError(f"the model returned invalid JSON: {error}") from error

        if not isinstance(data, dict):
            raise ValueError("the model JSON response is not an object")

        required = {
            "summary",
            "central_question",
            "should_participate",
            "confidence",
            "why",
            "best_speaker",
            "contributors",
            "key_points",
            "desired_effect",
        }
        missing = required.difference(data)
        if missing:
            raise ValueError(
                "the model JSON response is missing: "
                + ", ".join(sorted(missing))
            )

        if not isinstance(data["should_participate"], bool):
            raise ValueError("should_participate must be a boolean")
        if (
            isinstance(data["confidence"], bool)
            or not isinstance(data["confidence"], (int, float))
            or not 0 <= data["confidence"] <= 1
        ):
            raise ValueError("confidence must be a number from 0 to 1")
        for field in (
            "summary",
            "central_question",
            "why",
            "best_speaker",
            "desired_effect",
        ):
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
        for field in ("contributors", "key_points"):
            if (
                not isinstance(data[field], list)
                or not all(isinstance(item, str) for item in data[field])
            ):
                raise ValueError(f"{field} must be a list of strings")
        if not data["why"].strip():
            raise ValueError("why must not be empty")
        if data["should_participate"] and (
            not data["summary"].strip()
            or not data["central_question"].strip()
            or not data["best_speaker"].strip()
            or not data["key_points"]
            or not data["desired_effect"].strip()
        ):
            raise ValueError(
                "participation analysis must include complete discussion context"
            )

        return DiscussionAnalysis(
            summary=data["summary"],
            central_question=data["central_question"],
            should_participate=data["should_participate"],
            confidence=float(data["confidence"]),
            why=data["why"],
            best_speaker=data["best_speaker"],
            contributors=data["contributors"],
            key_points=data["key_points"],
            desired_effect=data["desired_effect"],
        )

    def recommend(
        self,
        new_posts: list[Any],
        reply_count: int,
        thread_posts: list[Any],
    ) -> DiscussionAnalysis:
        """Use an LLM to analyze the discussion without writing a reply."""

        if not new_posts:
            return self._safe_analysis(
                "There are no new forum posts to reply to."
            )

        if reply_count >= 20:
            return self._safe_analysis(
                "The discussion already has 20 or more replies."
            )

        posts_from_others = [
            post
            for post in new_posts
            if post.author.casefold() != self.own_author
        ]
        if not posts_from_others:
            return self._safe_analysis(
                "The eligible posts were written by ourselves."
            )

        system_prompt = f"""
{self.orchestra_charter}

---

{self.zubin_persona}

---

{self.persona}

---

You are an analyst.
Do NOT write a reply.

Your job is to understand:
- What is this discussion really about?
- Why are people posting?
- Is there room for a meaningful contribution?
- If not, recommend silence.
- Which musician should speak?

Return JSON only, with exactly these fields:
{{
  "summary": string,
  "central_question": string,
  "should_participate": boolean,
  "confidence": number from 0 to 1,
  "why": string,
  "best_speaker": string,
  "contributors": array of strings,
  "key_points": array of strings,
  "desired_effect": string
}}
If should_participate is false, recommend silence clearly in "why".
""".strip()

        prompt_data = {
            "complete_thread": [
                self._post_data(post) for post in thread_posts
            ],
            "eligible_posts": [
                self._post_data(post) for post in posts_from_others
            ],
            "existing_reply_count": reply_count,
        }

        user_prompt = json.dumps(prompt_data, ensure_ascii=False)

        try:
            content = generate_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception as error:
            return self._safe_analysis(
                f"LLM request failed; no reply will be posted: {error}"
            )

        try:
            return self._parse_analysis(content)
        except ValueError:
            return self._safe_analysis(
                "Invalid JSON returned by the LLM."
            )
