"""Human approval for actions proposed by The Agentic Orchestra.

Approval is deliberately separate from recommendation logic. Musicians can
suggest an action, but only a human can authorize a later external action.
This milestone records that decision and does not post anything.
"""

from dataclasses import dataclass

from orchestra.musician import Recommendation


@dataclass
class ApprovalRequest:
    """A recommendation together with its human approval status."""

    recommendation: Recommendation
    approved: bool | None


def request_human_approval(
    recommendation: Recommendation,
) -> ApprovalRequest:
    """Show a recommendation and ask a human to approve or reject it."""

    # Present every part of the recommendation before asking for a decision.
    print("==================================")
    print("ZUBIN'S RECOMMENDATION")
    print("==================================")
    print()
    print(f"Should reply: {recommendation.should_reply}")
    print(f"Confidence: {recommendation.confidence:.0%}")
    print(f"Reason: {recommendation.reason}")
    print()
    print(f"Draft subject: {recommendation.draft_subject}")
    print()
    print("Draft message:")
    print(recommendation.draft_message)
    print()

    # Only an explicit lowercase or uppercase "y" grants approval.
    answer = input("Approve this action? [y/N] ")
    approved = answer.strip().casefold() == "y"

    return ApprovalRequest(
        recommendation=recommendation,
        approved=approved,
    )

