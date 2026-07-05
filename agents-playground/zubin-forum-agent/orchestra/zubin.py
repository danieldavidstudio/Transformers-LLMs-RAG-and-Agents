"""Zubin's orchestration and recommendation behavior."""

import json
from dataclasses import asdict
from typing import Any

from orchestra.analysis import DiscussionAnalysis
from orchestra.critic import Critic, CriticReport
from orchestra.knowledge_loader import load_rules
from orchestra.musician import Musician, Recommendation
from orchestra.prompt_loader import load_persona, load_prompt, persona_role
from orchestra.turing import Turing
from providers import generate_chat


class Zubin(Musician):
    """Delegate forum analysis without taking action."""

    def __init__(self, own_author: str) -> None:
        self.persona = load_persona("zubin")
        self.orchestra_charter = load_prompt("orchestra")
        self.rules = load_rules()
        self.last_analysis: DiscussionAnalysis | None = None
        self.last_first_draft = ""
        self.last_critic_report: CriticReport | None = None
        self.last_final_draft = ""
        super().__init__(
            name="Zubin",
            role=persona_role(self.persona),
        )

        self.turing = Turing(own_author=own_author)
        self.critic = Critic()

    @staticmethod
    def _post_data(post: Any) -> dict[str, Any]:
        """Convert one forum post into JSON-safe drafting context."""

        return {
            "id": post.id,
            "author": post.author,
            "subject": post.subject,
            "message": post.message,
            "timestamp": post.timestamp,
        }

    @staticmethod
    def _recommend_silence(
        analysis: DiscussionAnalysis,
    ) -> Recommendation:
        """Convert a no-participation analysis into a recommendation."""

        return Recommendation(
            should_reply=False,
            confidence=analysis.confidence,
            reason=analysis.why,
            draft_subject="",
            draft_message="",
        )

    @staticmethod
    def _reply_subject(posts: list[Any]) -> str:
        """Build a reply subject from the eligible discussion post."""

        subject = posts[-1].subject if posts else "Discussion"
        return subject if subject.casefold().startswith("re:") else f"Re: {subject}"

    def recommend(
        self,
        new_posts: list[Any],
        reply_count: int,
        thread_posts: list[Any] | None = None,
    ) -> Recommendation:
        """Ask Turing for analysis, then write the final reply as Zubin."""

        self.last_analysis = None
        self.last_first_draft = ""
        self.last_critic_report = None
        self.last_final_draft = ""

        print("----------------------------------")
        print("Zubin delegated to Turing")
        print("----------------------------------")

        complete_thread = (
            thread_posts if thread_posts is not None else new_posts
        )
        analysis = self.turing.recommend(
            new_posts=new_posts,
            reply_count=reply_count,
            thread_posts=complete_thread,
        )
        self.last_analysis = analysis

        if not analysis.should_participate:
            return self._recommend_silence(analysis)

        system_prompt = f"""
{self.orchestra_charter}

---

{self.rules}

---

{self.persona}

---

You are Zubin.

You already understand the discussion.

Your job is NOT to explain AI.
Your job is to advance the conversation exactly one meaningful step.

Never write generic introductions.
Never write inspirational filler.
Never sound like ChatGPT.

Write as if you are joining an ongoing conversation among peers.

Return only the forum message.
""".strip()
        user_prompt = json.dumps(
            {
                "discussion_analysis": asdict(analysis),
                "complete_thread": [
                    self._post_data(post) for post in complete_thread
                ],
            },
            ensure_ascii=False,
        )

        try:
            content = generate_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception as error:
            return Recommendation(
                should_reply=False,
                confidence=0.0,
                reason=(
                    "LLM drafting failed; no reply will be posted: "
                    f"{error}"
                ),
                draft_subject="",
                draft_message="",
            )

        try:
            message = content.strip()
        except (AttributeError, TypeError):
            message = ""

        if not message:
            return Recommendation(
                should_reply=False,
                confidence=0.0,
                reason="Zubin's drafting LLM returned an empty message.",
                draft_subject="",
                draft_message="",
            )

        self.last_first_draft = message
        critic_report = self.critic.recommend(
            draft_message=message,
            analysis=analysis,
            thread_posts=complete_thread,
        )
        self.last_critic_report = critic_report

        final_message = message
        if critic_report.score < 7:
            rewrite_system_prompt = f"""
{self.orchestra_charter}

---

{self.rules}

---

{self.persona}

---

Rewrite the first draft exactly once using the Critic's suggestions. Preserve
what is strong, correct what is weak, and advance the ongoing conversation one
meaningful step. Do not mention the Critic or the review process.

Never write a generic introduction.
Never write inspirational filler.
Return only the rewritten forum message.
""".strip()
            rewrite_user_prompt = json.dumps(
                {
                    "discussion_analysis": asdict(analysis),
                    "complete_thread": [
                        self._post_data(post) for post in complete_thread
                    ],
                    "first_draft": message,
                    "critic_report": asdict(critic_report),
                },
                ensure_ascii=False,
            )
            try:
                rewritten = generate_chat(
                    system_prompt=rewrite_system_prompt,
                    user_prompt=rewrite_user_prompt,
                ).strip()
            except Exception:
                rewritten = ""
            if rewritten:
                final_message = rewritten

        self.last_final_draft = final_message
        return Recommendation(
            should_reply=True,
            confidence=analysis.confidence,
            reason=analysis.why,
            draft_subject=self._reply_subject(new_posts),
            draft_message=final_message,
        )
