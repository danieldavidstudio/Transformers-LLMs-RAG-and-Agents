"""Turing's LLM-backed forum-analysis behavior."""

import json
from typing import Any

from openai import OpenAI

from config import MODEL, OPENAI_API_KEY, OPENAI_ENDPOINT
from orchestra.musician import Musician, Recommendation


class Turing(Musician):
    """Analyze forum posts and ask an LLM whether Zubin should reply."""

    def __init__(self, own_author: str) -> None:
        super().__init__(name="Turing", role="AI and knowledge systems")
        self.own_author = own_author.casefold()

    @staticmethod
    def _safe_recommendation(reason: str) -> Recommendation:
        """Return a recommendation that can never reach the write tool."""

        return Recommendation(
            should_reply=False,
            confidence=0.0,
            reason=reason,
            draft_subject="",
            draft_message="",
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

    def _parse_recommendation(self, content: str) -> Recommendation:
        """Validate model JSON and convert it to a Recommendation."""

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError) as error:
            raise ValueError(f"the model returned invalid JSON: {error}") from error

        if not isinstance(data, dict):
            raise ValueError("the model JSON response is not an object")

        required = {
            "should_reply",
            "confidence",
            "reason",
            "draft_subject",
            "draft_message",
        }
        missing = required.difference(data)
        if missing:
            raise ValueError(
                "the model JSON response is missing: "
                + ", ".join(sorted(missing))
            )

        if not isinstance(data["should_reply"], bool):
            raise ValueError("should_reply must be a boolean")
        if (
            isinstance(data["confidence"], bool)
            or not isinstance(data["confidence"], (int, float))
            or not 0 <= data["confidence"] <= 1
        ):
            raise ValueError("confidence must be a number from 0 to 1")
        for field in ("reason", "draft_subject", "draft_message"):
            if not isinstance(data[field], str):
                raise ValueError(f"{field} must be a string")
        if not data["reason"].strip():
            raise ValueError("reason must not be empty")
        if data["should_reply"] and (
            not data["draft_subject"].strip()
            or not data["draft_message"].strip()
        ):
            raise ValueError(
                "a recommended reply must include a subject and message"
            )

        return Recommendation(
            should_reply=data["should_reply"],
            confidence=float(data["confidence"]),
            reason=data["reason"],
            draft_subject=data["draft_subject"],
            draft_message=data["draft_message"],
        )

    def recommend(
        self,
        new_posts: list[Any],
        reply_count: int,
        thread_posts: list[Any],
        persona: str,
        orchestra_concept: str,
    ) -> Recommendation:
        """Use an LLM to decide and draft, while retaining local guardrails."""

        if not new_posts:
            return self._safe_recommendation(
                "There are no new forum posts to reply to."
            )

        if reply_count >= 20:
            return self._safe_recommendation(
                "The discussion already has 20 or more replies."
            )

        posts_from_others = [
            post
            for post in new_posts
            if post.author.casefold() != self.own_author
        ]
        if not posts_from_others:
            return self._safe_recommendation(
                "The eligible posts were written by ourselves."
            )

        system_prompt = f"""
You are Turing, the AI and knowledge-systems specialist in The Agentic
Orchestra. You advise Zubin, but you do not post or act autonomously.

Zubin's persona:
{persona}

The Agentic Orchestra:
{orchestra_concept}

Decide whether a thoughtful reply is appropriate for the eligible posts in
the context of the complete thread. If so, draft in Zubin's calm, thoughtful,
concise, slightly poetic voice. Answer the spirit and substance of the thread;
never produce a generic greeting. Never claim full autonomy. A human must
review and approve every post.

Return JSON only, with exactly these fields:
{{
  "should_reply": boolean,
  "confidence": number from 0 to 1,
  "reason": string,
  "draft_subject": string,
  "draft_message": string
}}
If should_reply is false, use empty strings for both draft fields.
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

        try:
            client = OpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_ENDPOINT,
            )
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(prompt_data, ensure_ascii=False),
                    },
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            return self._parse_recommendation(content)
        except ValueError as error:
            return self._safe_recommendation(f"LLM response error: {error}")
        except Exception as error:
            return self._safe_recommendation(
                f"LLM request failed; no reply will be posted: {error}"
            )
