"""Write Markdown evaluation records for every completed agent execution."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from orchestra.analysis import DiscussionAnalysis
from orchestra.critic import CriticReport
from orchestra.musician import Recommendation


EVALUATIONS_PATH = Path(__file__).with_name("evaluations")


def _list(items: list[str]) -> str:
    """Format a Markdown list, including a clear empty value."""

    return "\n".join(f"- {item}" for item in items) or "- None"


def _discussion(posts: list[Any]) -> str:
    """Format the complete discussion for the evaluation record."""

    if not posts:
        return "No posts were available."
    return "\n\n".join(
        (
            f"### {post.subject}\n\n"
            f"- Author: {post.author}\n"
            f"- Post ID: {post.id}\n\n"
            f"{post.message}"
        )
        for post in posts
    )


def _next_path() -> Path:
    """Choose a timestamped path without overwriting an existing execution."""

    moment = datetime.now().replace(microsecond=0)
    while True:
        path = EVALUATIONS_PATH / f"{moment:%Y-%m-%d_%H-%M-%S}.md"
        if not path.exists():
            return path
        moment += timedelta(seconds=1)


def save_evaluation(
    discussion_posts: list[Any],
    analysis: DiscussionAnalysis | None,
    first_draft: str,
    critic_report: CriticReport | None,
    recommendation: Recommendation,
    approved: bool,
    posted: bool,
) -> Path | None:
    """Save one complete reasoning history without disrupting the agent."""

    if not isinstance(analysis, DiscussionAnalysis):
        analysis_text = "Unavailable"
        plan_text = "Unavailable"
    else:
        analysis_text = (
            f"- Summary: {analysis.summary or 'Not provided'}\n"
            f"- Central question: {analysis.central_question or 'Not provided'}\n"
            f"- Should participate: "
            f"{'Yes' if analysis.should_participate else 'No'}\n"
            f"- Confidence: {analysis.confidence:.0%}\n"
            f"- Why: {analysis.why}"
        )
        plan_text = (
            f"- Speaker: {analysis.best_speaker or 'Not provided'}\n"
            f"- Contributors:\n{_list(analysis.contributors)}\n"
            f"- Desired effect: {analysis.desired_effect or 'Not provided'}\n"
            f"- Key points:\n{_list(analysis.key_points)}"
        )

    if not isinstance(critic_report, CriticReport):
        critic_text = "Not run."
    else:
        critic_text = (
            f"- Approved: {'Yes' if critic_report.approved else 'No'}\n"
            f"- Score: {critic_report.score:g}/10\n"
            f"- Strengths:\n{_list(critic_report.strengths)}\n"
            f"- Weaknesses:\n{_list(critic_report.weaknesses)}\n"
            f"- Suggestions:\n{_list(critic_report.suggestions)}"
        )

    document = f"""# Orchestra Evaluation

## Discussion

{_discussion(discussion_posts)}

## Analysis

{analysis_text}

## Communication Plan

{plan_text}

## First Draft

{first_draft or "Not generated."}

## Critic Report

{critic_text}

## Final Draft

### Subject

{recommendation.draft_subject or "Not generated."}

### Message

{recommendation.draft_message or "Not generated."}

## Human Decision

{"Approved" if approved else "Rejected"}

## Posted?

{"Yes" if posted else "No"}
"""

    try:
        EVALUATIONS_PATH.mkdir(parents=True, exist_ok=True)
        path = _next_path()
        path.write_text(document, encoding="utf-8")
    except OSError:
        return None
    return path
